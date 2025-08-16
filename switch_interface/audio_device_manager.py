"""Audio device management with automatic fallback capabilities."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Literal, Optional, Tuple

import sounddevice as sd

from .audio.stream import open_input, rescan_backends

logger = logging.getLogger(__name__)

__all__ = [
    "AudioDeviceManager",
    "get_available_devices",
    "check_device",
    "find_working_device",
    "AudioDeviceMode",
    "AudioDeviceError",
]


class AudioDeviceError(Exception):
    """Exception raised for audio device errors with recovery information."""

    def __init__(
        self,
        message: str,
        device_id: Optional[int | str] = None,
        error_type: str = "general",
        recovery_hint: Optional[str] = None,
    ):
        self.device_id = device_id
        self.error_type = (
            error_type  # "access", "format", "hardware", "not_found", "general"
        )
        self.recovery_hint = recovery_hint
        super().__init__(message)


# Audio device access modes
AudioDeviceMode = Literal["exclusive", "shared", "auto"]


class AudioDeviceManager:
    """Manages audio device selection and fallback mechanisms."""

    def __init__(self):
        self.last_working_device: Optional[int | str] = None
        self.last_working_mode: AudioDeviceMode = "auto"
        self.device_test_cache: Dict[str, Tuple[bool, float]] = (
            {}
        )  # device_id -> (success, timestamp)
        self.cache_timeout = 30.0  # Cache test results for 30 seconds
        self.fallback_attempts: Dict[str, int] = (
            {}
        )  # Track fallback attempts per device

    def get_available_input_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio input devices."""
        try:
            devices = []
            for i, device_info in enumerate(sd.query_devices()):
                if device_info.get("max_input_channels", 0) > 0:
                    devices.append(
                        {
                            "index": i,
                            "name": device_info["name"],
                            "hostapi": device_info.get("hostapi", 0),
                            "max_input_channels": device_info["max_input_channels"],
                            "default_samplerate": device_info.get(
                                "default_samplerate", 44100
                            ),
                        }
                    )
            return devices
        except Exception as exc:
            logger.warning(f"Failed to query audio devices: {exc}")
            return []

    def test_device(
        self,
        device: int | str | None,
        samplerate: int = 44100,
        blocksize: int = 256,
        timeout: float = 2.0,
        mode: AudioDeviceMode = "auto",
    ) -> Tuple[bool, Optional[str]]:
        """Test if an audio device can be opened successfully.

        Args:
            device: Device ID or name to test
            samplerate: Sample rate to test with
            blocksize: Block size to test with
            timeout: Maximum time to wait for device test
            mode: Audio device mode ("exclusive", "shared", or "auto")

        Returns:
            tuple: (success, error_message)
        """
        device_key = f"{str(device) if device is not None else 'default'}:{mode}"
        current_time = time.time()

        # Check cache first
        if device_key in self.device_test_cache:
            success, timestamp = self.device_test_cache[device_key]
            if current_time - timestamp < self.cache_timeout:
                return success, None if success else "Cached failure"

        try:
            # Test opening the device with a short timeout
            backend = None
            extra_kwargs = {}

            # Set mode-specific parameters
            if mode == "exclusive":
                # Force exclusive mode (Windows WASAPI)
                from .audio.backends.wasapi import get_extra_settings

                extra_settings = get_extra_settings()
                if extra_settings:
                    extra_kwargs["extra_settings"] = extra_settings
            elif mode == "shared":
                # Force shared mode by explicitly avoiding extra settings
                pass
            # For "auto" mode, let the backend decide

            with open_input(
                samplerate=samplerate,
                blocksize=blocksize,
                channels=1,
                dtype="float32",
                device=device,
                callback=lambda *args: None,
                backend=backend,
                **extra_kwargs,
            ):
                # If we get here, the device works
                self.device_test_cache[device_key] = (True, current_time)
                if device is not None:
                    self.last_working_device = device
                self.last_working_mode = mode
                return True, None

        except Exception as exc:
            error_msg = str(exc)
            error_type = self._categorize_audio_error(error_msg)
            logger.debug(
                f"Device test failed for {device} in {mode} mode: {error_msg} (type: {error_type})"
            )
            self.device_test_cache[device_key] = (False, current_time)
            return False, error_msg

    def _categorize_audio_error(self, error_msg: str) -> str:
        """Categorize audio error messages to help with recovery."""
        error_msg = error_msg.lower()

        if (
            "access denied" in error_msg
            or "permission" in error_msg
            or "being used" in error_msg
        ):
            return "access"
        elif (
            "format" in error_msg
            or "sample rate" in error_msg
            or "channels" in error_msg
        ):
            return "format"
        elif "no such device" in error_msg or "device not found" in error_msg:
            return "not_found"
        elif "hardware" in error_msg or "driver" in error_msg:
            return "hardware"
        else:
            return "general"

    def find_working_device(
        self,
        preferred_device: int | str | None = None,
        samplerate: int = 44100,
        blocksize: int = 256,
        preferred_mode: AudioDeviceMode = "auto",
    ) -> Tuple[Optional[int | str], Optional[str], Optional[AudioDeviceMode]]:
        """Find a working audio input device with fallback logic.

        This method implements a comprehensive fallback strategy:
        1. Try preferred device in preferred mode
        2. Try preferred device in alternative modes (exclusive->shared, shared->exclusive)
        3. Try last known working device in its last working mode
        4. Try system default device in auto mode
        5. Try all available input devices in auto mode

        Args:
            preferred_device: Device to try first (None for system default)
            samplerate: Sample rate to test with
            blocksize: Block size to test with
            preferred_mode: Preferred audio mode ("exclusive", "shared", or "auto")

        Returns:
            tuple: (working_device_id, error_message, working_mode)
        """
        # Build device fallback chain
        devices_to_try = self.get_device_fallback_chain(preferred_device)

        # Define mode fallback strategy
        mode_fallbacks: Dict[AudioDeviceMode, List[AudioDeviceMode]] = {
            "exclusive": ["exclusive", "shared", "auto"],
            "shared": ["shared", "auto", "exclusive"],
            "auto": ["auto", "shared", "exclusive"],
        }

        # First try the preferred device with mode fallbacks
        if preferred_device is not None:
            for mode in mode_fallbacks[preferred_mode]:
                logger.debug(
                    f"Testing preferred device {preferred_device} in {mode} mode"
                )
                success, error = self.test_device(
                    preferred_device, samplerate, blocksize, mode=mode
                )

                if success:
                    logger.info(
                        f"Found working audio device: {preferred_device} in {mode} mode"
                    )
                    self.last_working_device = preferred_device
                    self.last_working_mode = mode
                    return preferred_device, None, mode

        # If we have a last working device and it's different from preferred, try it
        if (
            self.last_working_device is not None
            and self.last_working_device != preferred_device
            and self.last_working_device in devices_to_try
        ):

            # Try last working mode first, then fallbacks
            fallback_modes: List[AudioDeviceMode] = ["auto", "shared", "exclusive"]
            modes_to_try = [self.last_working_mode] + [
                m for m in fallback_modes if m != self.last_working_mode
            ]

            for mode in modes_to_try:
                logger.debug(
                    f"Testing last working device {self.last_working_device} in {mode} mode"
                )
                success, error = self.test_device(
                    self.last_working_device, samplerate, blocksize, mode=mode
                )

                if success:
                    logger.info(
                        f"Found working audio device: {self.last_working_device} in {mode} mode"
                    )
                    self.last_working_mode = mode
                    return self.last_working_device, None, mode

        # Try remaining devices in auto mode first, then shared, then exclusive
        last_error = None
        for device in devices_to_try:
            # Skip devices we've already tried
            if device == preferred_device or device == self.last_working_device:
                continue

            auto_modes: List[AudioDeviceMode] = ["auto", "shared", "exclusive"]
            for mode in auto_modes:
                logger.debug(f"Testing audio device: {device} in {mode} mode")
                success, error = self.test_device(
                    device, samplerate, blocksize, mode=mode
                )

                if success:
                    logger.info(f"Found working audio device: {device} in {mode} mode")
                    self.last_working_device = device
                    self.last_working_mode = mode
                    return device, None, mode
                else:
                    last_error = error
                    logger.debug(f"Device {device} in {mode} mode failed: {error}")

        # No working device found
        error_msg = f"No working audio input devices found. Last error: {last_error}"
        logger.error(error_msg)
        return None, error_msg, None

    def validate_device_settings(
        self,
        device: int | str | None,
        samplerate: int = 44100,
        blocksize: int = 256,
        mode: AudioDeviceMode = "auto",
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """Validate device settings and return device info if valid.

        Args:
            device: Device ID or name to validate
            samplerate: Sample rate to validate
            blocksize: Block size to validate
            mode: Audio device mode to validate

        Returns:
            tuple: (is_valid, error_message, device_info)
        """
        # First check if device exists
        device_info = self.get_device_info(device)
        if device_info is None:
            return False, f"Device {device} not found", None

        # Then check if device can be opened with these settings
        success, error = self.test_device(device, samplerate, blocksize, mode=mode)
        if not success:
            return False, error, device_info

        return True, None, device_info

    def get_device_fallback_chain(
        self, preferred_device: int | str | None = None
    ) -> List[int | str | None]:
        """Get ordered list of devices to try for fallback."""
        devices: List[int | str | None] = []

        # Preferred device first
        if preferred_device is not None:
            devices.append(preferred_device)

        # Last working device
        if (
            self.last_working_device is not None
            and self.last_working_device != preferred_device
        ):
            devices.append(self.last_working_device)

        # System default
        if None not in devices:
            devices.append(None)

        # All other available devices
        available = self.get_available_input_devices()
        for device_info in available:
            device_id = device_info["index"]
            if device_id not in devices:
                devices.append(device_id)

        return devices

    def clear_cache(self) -> None:
        """Clear the device test cache."""
        self.device_test_cache.clear()

    def get_device_info(self, device: int | str | None) -> Optional[Dict[str, Any]]:
        """Get information about a specific device."""
        try:
            if device is None:
                # Get default device info
                default_device = sd.default.device[0]  # Input device
                if default_device is not None:
                    return dict(sd.query_devices(default_device))
                return None
            else:
                return dict(sd.query_devices(device, "input"))
        except Exception as exc:
            logger.debug(f"Failed to get device info for {device}: {exc}")
            return None


# Convenience functions for backward compatibility
def get_available_devices() -> List[Dict[str, Any]]:
    """Get list of available audio input devices."""
    manager = AudioDeviceManager()
    return manager.get_available_input_devices()


def check_device(
    device: int | str | None,
    samplerate: int = 44100,
    blocksize: int = 256,
    mode: AudioDeviceMode = "auto",
) -> Tuple[bool, Optional[str]]:
    """Test if an audio device works."""
    manager = AudioDeviceManager()
    return manager.test_device(device, samplerate, blocksize, mode=mode)


def find_working_device(
    preferred_device: int | str | None = None,
    samplerate: int = 44100,
    blocksize: int = 256,
    preferred_mode: AudioDeviceMode = "auto",
) -> Tuple[Optional[int | str], Optional[str], Optional[AudioDeviceMode]]:
    """Find a working audio input device with automatic fallback.

    Returns:
        tuple: (working_device_id, error_message, working_mode)
    """
    manager = AudioDeviceManager()
    return manager.find_working_device(
        preferred_device, samplerate, blocksize, preferred_mode
    )
