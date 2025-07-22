"""Monitor audio input and call a handler when a switch press is detected."""
from __future__ import annotations

import logging
import math
import time
from typing import Callable, Optional, Tuple

import numpy as np

from .audio.stream import open_input
from .audio_device_manager import AudioDeviceManager

logger = logging.getLogger(__name__)

__all__ = ["listen", "check_device", "check_device_with_fallback"]


def check_device(*, samplerate: int = 44_100, blocksize: int = 256, device: int | str | None = None) -> None:
    """Raise ``RuntimeError`` if the input device can't be opened."""
    import sounddevice as sd

    try:
        with open_input(
            samplerate=samplerate,
            blocksize=blocksize,
            channels=1,
            dtype="float32",
            device=device,
            callback=lambda *a: None,
        ):
            pass
    except Exception as exc:
        raise RuntimeError("Failed to open audio input device") from exc


def check_device_with_fallback(
    *, 
    samplerate: int = 44_100, 
    blocksize: int = 256, 
    device: int | str | None = None,
    mode: str = "auto"
) -> Tuple[Optional[int | str], Optional[str], Optional[str]]:
    """Check device with automatic fallback to working alternatives.
    
    Args:
        samplerate: Sample rate to test with
        blocksize: Block size to test with
        device: Device ID or name to test (None for system default)
        mode: Audio device mode ("exclusive", "shared", or "auto")
    
    Returns:
        tuple: (working_device_id, error_message, working_mode)
    """
    from .audio_device_manager import AudioDeviceMode
    
    # Validate mode parameter
    valid_modes = ["exclusive", "shared", "auto"]
    if mode not in valid_modes:
        mode = "auto"
    
    manager = AudioDeviceManager()
    return manager.find_working_device(device, samplerate, blocksize, mode)


def listen(
    on_press: Callable[[], None],
    *,
    upper_offset: float = -0.2,
    lower_offset: float = -0.5,
    samplerate: int = 44_100,
    blocksize: int = 256,
    debounce_ms: int = 40,
    device: Optional[int | str] = None,
    enable_fallback: bool = True,
    device_mode: str = "auto",
) -> None:
    """Block while monitoring the input stream for switch presses.
    
    Args:
        on_press: Callback function when switch is pressed
        upper_offset: Upper threshold offset from bias
        lower_offset: Lower threshold offset from bias
        samplerate: Audio sample rate
        blocksize: Audio block size
        debounce_ms: Debounce time in milliseconds
        device: Audio device ID or name (None for system default)
        enable_fallback: Whether to enable automatic device fallback
        device_mode: Audio device mode ("exclusive", "shared", or "auto")
    """
    from .detection import EdgeState, detect_edges
    from .audio_device_manager import AudioDeviceManager, AudioDeviceMode
    import sounddevice as sd

    if upper_offset <= lower_offset:
        raise ValueError("upper_offset must be > lower_offset (both negative values)")

    # Validate mode parameter
    valid_modes = ["exclusive", "shared", "auto"]
    if device_mode not in valid_modes:
        device_mode = "auto"

    refractory_samples = int(math.ceil((debounce_ms / 1_000) * samplerate))
    state = EdgeState(armed=True, cooldown=0)

    def _callback(indata: np.ndarray, frames: int, _: int, __: int) -> None:
        nonlocal state
        mono = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0]
        state, pressed = detect_edges(
            mono,
            state,
            upper_offset,
            lower_offset,
            refractory_samples,
        )
        if pressed:
            on_press()

    def _run_with_device(target_device: int | str | None, mode: AudioDeviceMode = "auto") -> None:
        """Run listener with specific device and mode."""
        extra_kwargs = {}
        
        # Set mode-specific parameters
        if mode == "exclusive":
            # Force exclusive mode (Windows WASAPI)
            from .audio.backends.wasapi import get_extra_settings
            extra_settings = get_extra_settings()
            if extra_settings:
                extra_kwargs["extra_settings"] = extra_settings
        
        with open_input(
            samplerate=samplerate,
            blocksize=blocksize,
            channels=1,
            dtype="float32",
            callback=_callback,
            device=target_device,
            **extra_kwargs
        ):
            try:
                while True:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                return

    # Try with fallback if enabled
    if enable_fallback:
        manager = AudioDeviceManager()
        working_device, error, working_mode = manager.find_working_device(
            device, samplerate, blocksize, device_mode
        )
        
        if working_device is not None and working_mode is not None:
            logger.info(f"Using audio device: {working_device} in {working_mode} mode")
            try:
                _run_with_device(working_device, working_mode)
                return
            except Exception as exc:
                logger.warning(f"Device {working_device} in {working_mode} mode failed during listening: {exc}")
                
                # Try one more time with a different mode if we haven't tried all modes
                if working_mode == "exclusive":
                    try:
                        logger.info("Attempting fallback to shared mode")
                        _run_with_device(working_device, "shared")
                        return
                    except Exception as fallback_exc:
                        logger.warning(f"Fallback to shared mode failed: {fallback_exc}")
                elif working_mode == "shared" or working_mode == "auto":
                    # Try to find a completely different device
                    try:
                        # Exclude the failed device from consideration
                        available_devices = manager.get_available_input_devices()
                        for device_info in available_devices:
                            if device_info["index"] != working_device:
                                alt_device = device_info["index"]
                                logger.info(f"Trying alternative device: {alt_device}")
                                _run_with_device(alt_device, "auto")
                                return
                    except Exception:
                        # Continue to original approach below
                        pass
        else:
            logger.warning(f"No working audio device found: {error}")
    
    # Fallback to original behavior as last resort
    try:
        _run_with_device(device, "auto")
    except sd.PortAudioError as exc:
        if enable_fallback:
            raise RuntimeError(f"Failed to open any audio input device. Last error: {exc}") from exc
        else:
            raise RuntimeError("Failed to open audio input device") from exc
