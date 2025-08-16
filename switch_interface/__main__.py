"""Command line entry point for the virtual keyboard interface."""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from queue import Empty, SimpleQueue
from typing import Any, Callable, Dict, Optional

from switch_interface.logging import setup as _setup_logging

from . import launcher

_setup_logging()

_LOG_PATH = Path.home() / ".switch_interface.log"


class ApplicationBootstrap:
    """Manages the initialization and lifecycle of the switch interface application."""

    def __init__(self):
        self.config: Optional[Any] = None
        self.audio_manager: Optional[Any] = None
        self.keyboard: Optional[Any] = None
        self.scanner: Optional[Any] = None
        self.pc_controller: Optional[Any] = None
        self.virtual_keyboard: Optional[Any] = None
        self.shutdown = threading.Event()
        self.press_queue: SimpleQueue[None] = SimpleQueue()

    def parse_arguments(self, argv: list[str] | None = None) -> argparse.Namespace:
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(
            description="Run the switch-accessible virtual keyboard",
        )
        parser.add_argument(
            "--layout",
            default=os.getenv("LAYOUT_PATH"),
            help="Path to keyboard layout JSON",
        )
        parser.add_argument(
            "--dwell",
            type=float,
            default=0.6,
            help="Time in seconds each key remains highlighted",
        )
        parser.add_argument(
            "--row-column",
            action="store_true",
            help="Use row/column scanning instead of simple linear scanning",
        )
        parser.add_argument(
            "--calibrate",
            action="store_true",
            help="Show calibration sliders before launching",
        )
        return parser.parse_args(argv)

    def load_dependencies(self) -> Dict[str, Any]:
        """Load required modules with error handling."""
        try:
            from . import calibration, settings
            from .kb_gui import VirtualKeyboard
            from .kb_layout_io import load_keyboard
            from .listener import listen
            from .pc_control import PCController
            from .scan_engine import Scanner

            return {
                "calibration": calibration,
                "settings": settings,
                "listen": listen,
                "VirtualKeyboard": VirtualKeyboard,
                "load_keyboard": load_keyboard,
                "PCController": PCController,
                "Scanner": Scanner,
            }
        except ImportError as e:
            raise RuntimeError(f"Failed to import required modules: {e}") from e

    def load_configuration(self, modules: Dict[str, Any]) -> Any:
        """Load application configuration."""
        try:
            self.config = modules["settings"].load()
            return self.config
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}") from e

    def handle_calibration(self, args: argparse.Namespace, modules: Dict[str, Any]) -> None:
        """Handle calibration if requested."""
        if not args.calibrate:
            return

        assert self.config is not None, "Configuration must be loaded before calibration"
        try:
            detector_config = modules["calibration"].DetectorConfig(
                upper_offset=self.config.calibration.upper_offset,
                lower_offset=self.config.calibration.lower_offset,
                samplerate=self.config.calibration.samplerate,
                blocksize=self.config.calibration.blocksize,
                debounce_ms=self.config.calibration.debounce_ms,
                device=self.config.audio.device,
            )
            detector_config = modules["calibration"].calibrate(detector_config)

            # Update settings with calibration results
            self.config.calibration.upper_offset = detector_config.upper_offset
            self.config.calibration.lower_offset = detector_config.lower_offset
            self.config.calibration.samplerate = detector_config.samplerate
            self.config.calibration.blocksize = detector_config.blocksize
            self.config.calibration.debounce_ms = detector_config.debounce_ms
            if detector_config.device:
                self.config.audio.device = detector_config.device
            modules["settings"].save(self.config)
        except Exception as e:
            raise RuntimeError(f"Calibration failed: {e}") from e

    def verify_audio_device(self) -> None:
        """Verify audio device availability with fallback."""
        assert self.config is not None, "Configuration must be loaded before verifying audio device"
        ready = threading.Event()
        audio_error: Exception | None = None
        working_device = None
        
        # Capture config values for nested function
        samplerate = self.config.calibration.samplerate
        blocksize = self.config.calibration.blocksize
        device = self.config.audio.device

        def _verify() -> None:
            nonlocal audio_error, working_device
            try:
                from .listener import check_device_with_fallback

                working_device, error, mode = check_device_with_fallback(
                    samplerate=samplerate,
                    blocksize=blocksize,
                    device=device,
                )

                if working_device is None:
                    audio_error = RuntimeError(
                        f"No working audio device found: {error}"
                    )

            except Exception as e:
                audio_error = e
                logging.warning(
                    "Audio check failed: %s – will attempt fallback during startup", e
                )
            finally:
                ready.set()

        threading.Thread(target=_verify, daemon=True).start()
        if not ready.wait(3.0):
            logging.warning(
                "Audio device check timed out – will attempt fallback during startup"
            )
            audio_error = RuntimeError("Audio device check timed out")

        # Update config with working device if different
        if working_device is not None and working_device != device:
            logging.info(f"Using fallback audio device: {working_device}")
            device_str = (
                str(working_device)
                if isinstance(working_device, int)
                else working_device
            )
            self.config.audio.device = device_str
            self.config.audio.last_working_device = device_str

        # Only raise error if no devices are available at all
        if audio_error and working_device is None:
            error_str = str(audio_error).lower()
            if "no device" in error_str or "no working audio" in error_str:
                raise RuntimeError(
                    f"No audio input device available: {audio_error}"
                ) from audio_error
            else:
                logging.warning(
                    f"Audio device check had issues but will continue: {audio_error}"
                )

    def setup_keyboard_and_controller(self, args: argparse.Namespace, modules: Dict[str, Any]) -> None:
        """Set up keyboard layout and PC controller."""
        self.pc_controller = modules["PCController"]()
        try:
            self.keyboard, metadata = modules["load_keyboard"](args.layout)
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Layout file '{args.layout}' not found. Check that the file exists and is accessible."
            ) from e
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Invalid JSON in layout file '{args.layout}': {e.msg}. Check the file format."
            ) from e
        except Exception as e:
            raise RuntimeError(
                f"Failed to load keyboard layout '{args.layout}': {e}"
            ) from e

    def create_virtual_keyboard(self, modules: Dict[str, Any]) -> None:
        """Create the virtual keyboard interface."""
        assert self.keyboard is not None, "Keyboard must be loaded before creating virtual keyboard"
        assert self.pc_controller is not None, "PC controller must be created before virtual keyboard"
        try:
            self.virtual_keyboard = modules["VirtualKeyboard"](
                self.keyboard,
                on_key=self.pc_controller.on_key,
                state=self.pc_controller.state,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to create virtual keyboard interface: {e}"
            ) from e

    def initialize_scanner(self, args: argparse.Namespace, modules: Dict[str, Any]) -> None:
        """Initialize the scanning system."""
        assert self.virtual_keyboard is not None, "Virtual keyboard must be created before scanner"
        try:
            self.scanner = modules["Scanner"](
                self.virtual_keyboard, dwell=args.dwell, row_column_scan=args.row_column
            )
            self.scanner.start()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize scanning system: {e}") from e

    def setup_event_handlers(self) -> tuple[Callable[[], None], Callable[[], None], Callable[[], None]]:
        """Set up event handlers for switch presses and GUI events."""

        def _on_switch() -> None:
            self.press_queue.put(None)

        def _pump_queue() -> None:
            assert self.scanner is not None, "Scanner must be initialized"
            assert self.virtual_keyboard is not None, "Virtual keyboard must be created"
            while True:
                try:
                    self.press_queue.get_nowait()
                except Empty:
                    break
                self.scanner.on_press()
            if not self.shutdown.is_set():
                self.virtual_keyboard.root.after(10, _pump_queue)

        def _on_close() -> None:
            assert self.scanner is not None, "Scanner must be initialized"
            assert self.virtual_keyboard is not None, "Virtual keyboard must be created"
            self.shutdown.set()
            self.scanner.stop()
            self.virtual_keyboard.root.destroy()

        return _on_switch, _pump_queue, _on_close

    def start_audio_listener(self, modules: Dict[str, Any], _on_switch: Callable[[], None]) -> None:
        """Start the audio listener thread."""
        assert self.config is not None, "Configuration must be loaded before starting audio listener"
        try:
            threading.Thread(
                target=modules["listen"],
                args=(_on_switch,),
                kwargs={
                    "upper_offset": self.config.calibration.upper_offset,
                    "lower_offset": self.config.calibration.lower_offset,
                    "samplerate": self.config.calibration.samplerate,
                    "blocksize": self.config.calibration.blocksize,
                    "debounce_ms": self.config.calibration.debounce_ms,
                    "device": self.config.audio.device,
                    "device_mode": self.config.audio.device_mode,
                },
                daemon=True,
            ).start()
        except Exception as e:
            raise RuntimeError(f"Failed to start audio listener: {e}") from e

    def run_gui(self, _pump_queue: Callable[[], None], _on_close: Callable[[], None]) -> None:
        """Start the GUI main loop."""
        assert self.virtual_keyboard is not None, "Virtual keyboard must be created before running GUI"
        assert self.scanner is not None, "Scanner must be initialized before running GUI"
        try:
            self.virtual_keyboard.root.protocol("WM_DELETE_WINDOW", _on_close)
            self.virtual_keyboard.root.after(10, _pump_queue)
            self.virtual_keyboard.run()
        except Exception as e:
            # Clean up on GUI error
            self.shutdown.set()
            if self.scanner is not None:
                self.scanner.stop()
            raise RuntimeError(f"GUI error during operation: {e}") from e


def _open_log_if_exists() -> None:
    if _LOG_PATH.exists() and _LOG_PATH.is_file():
        try:
            if sys.platform == "win32":
                os.startfile(_LOG_PATH)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", str(_LOG_PATH)], check=True)
            else:
                subprocess.run(["xdg-open", str(_LOG_PATH)], check=True)
        except (subprocess.CalledProcessError, OSError) as e:
            logging.warning("Failed to open log file: %s", e)


def keyboard_main(argv: list[str] | None = None) -> None:
    """Launch the scanning keyboard interface with enhanced error handling."""
    app = ApplicationBootstrap()

    # Parse arguments
    args = app.parse_arguments(argv)

    # Load dependencies and configuration
    modules = app.load_dependencies()
    app.load_configuration(modules)

    # Handle calibration if requested
    app.handle_calibration(args, modules)

    # Verify audio device
    app.verify_audio_device()

    # Set up keyboard and controller
    app.setup_keyboard_and_controller(args, modules)

    # Create virtual keyboard
    app.create_virtual_keyboard(modules)

    # Initialize scanner
    app.initialize_scanner(args, modules)

    # Set up event handlers
    _on_switch, _pump_queue, _on_close = app.setup_event_handlers()

    # Start audio listener
    app.start_audio_listener(modules, _on_switch)

    # Run GUI
    app.run_gui(_pump_queue, _on_close)


def main(argv: list[str] | None = None) -> None:
    """Launch the GUI launcher."""
    launcher.main()


if __name__ == "__main__":  # pragma: no cover - manual entry point
    try:
        main()
    except Exception:
        _open_log_if_exists()
        raise
