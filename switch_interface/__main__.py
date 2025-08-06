"""Command line entry point for the virtual keyboard interface."""

from __future__ import annotations

from switch_interface.logging import setup as _setup_logging
from . import launcher

_setup_logging()

import argparse
import json
import os
import subprocess
import sys
import threading
import logging
from pathlib import Path
from queue import Empty, SimpleQueue

_LOG_PATH = Path.home() / ".switch_interface.log"


def _open_log_if_exists() -> None:
    if _LOG_PATH.exists():
        if sys.platform == "win32":
            os.startfile(_LOG_PATH)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", _LOG_PATH])
        else:
            subprocess.run(["xdg-open", _LOG_PATH])


def keyboard_main(argv: list[str] | None = None) -> None:
    """Launch the scanning keyboard interface with enhanced error handling."""
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

    args = parser.parse_args(argv)

    try:
        from . import calibration, settings
        from .listener import check_device, listen
        from .kb_gui import VirtualKeyboard
        from .kb_layout_io import load_keyboard
        from .pc_control import PCController
        from .scan_engine import Scanner
        from .error_handler import error_handler
    except ImportError as e:
        # Critical startup error - missing required modules
        raise RuntimeError(f"Failed to import required modules: {e}") from e

    # Load configuration with error handling
    try:
        cfg = settings.load()
    except Exception as e:
        raise RuntimeError(f"Failed to load configuration: {e}") from e
        
    if args.calibrate:
        try:
            detector_config = calibration.DetectorConfig(
                upper_offset=cfg.calibration.upper_offset,
                lower_offset=cfg.calibration.lower_offset,
                samplerate=cfg.calibration.samplerate,
                blocksize=cfg.calibration.blocksize,
                debounce_ms=cfg.calibration.debounce_ms,
                device=cfg.audio.device
            )
            detector_config = calibration.calibrate(detector_config)
            # Update settings with calibration results
            cfg.calibration.upper_offset = detector_config.upper_offset
            cfg.calibration.lower_offset = detector_config.lower_offset
            cfg.calibration.samplerate = detector_config.samplerate
            cfg.calibration.blocksize = detector_config.blocksize
            cfg.calibration.debounce_ms = detector_config.debounce_ms
            if detector_config.device:
                cfg.audio.device = detector_config.device
            settings.save(cfg)
        except Exception as e:
            raise RuntimeError(f"Calibration failed: {e}") from e

    # Audio device verification with enhanced error handling and fallback
    ready = threading.Event()
    audio_error = None
    working_device = None

    def _verify() -> None:
        nonlocal audio_error, working_device
        try:
            # First try the configured device with fallback
            from .listener import check_device_with_fallback
            working_device, error = check_device_with_fallback(
                samplerate=cfg.calibration.samplerate,
                blocksize=cfg.calibration.blocksize,
                device=cfg.audio.device,
            )
            
            if working_device is None:
                audio_error = RuntimeError(f"No working audio device found: {error}")
            else:
                # Update config with working device if different
                if working_device != cfg.audio.device:
                    logging.info(f"Using fallback audio device: {working_device}")
                    cfg.audio.device = working_device
                    cfg.audio.last_working_device = working_device
                    
        except Exception as e:
            audio_error = e
            logging.warning(
                "Audio check failed: %s \u2013 will attempt fallback during startup", e
            )
        finally:
            ready.set()

    threading.Thread(target=_verify, daemon=True).start()
    if not ready.wait(3.0):  # Increased timeout for fallback testing
        logging.warning(
            "Audio device check timed out \u2013 will attempt fallback during startup"
        )
        audio_error = RuntimeError("Audio device check timed out")

    # Only raise error if no devices are available at all
    if audio_error and working_device is None:
        # Check if it's a critical "no device" error
        error_str = str(audio_error).lower()
        if "no device" in error_str or "no working audio" in error_str:
            raise RuntimeError(f"No audio input device available: {audio_error}") from audio_error
        else:
            # Non-critical error, log and continue
            logging.warning(f"Audio device check had issues but will continue: {audio_error}")

    # Load keyboard layout with better error handling
    pc_controller = PCController()
    try:
        keyboard = load_keyboard(args.layout)
    except FileNotFoundError as e:
        raise RuntimeError(f"Layout file '{args.layout}' not found. Check that the file exists and is accessible.") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in layout file '{args.layout}': {e.msg}. Check the file format.") from e
    except Exception as e:
        raise RuntimeError(f"Failed to load keyboard layout '{args.layout}': {e}") from e

    # Create virtual keyboard with error handling
    try:
        vk = VirtualKeyboard(
            keyboard, on_key=pc_controller.on_key, state=pc_controller.state
        )
    except Exception as e:
        raise RuntimeError(f"Failed to create virtual keyboard interface: {e}") from e

    # Initialize scanner with error handling
    try:
        scanner = Scanner(vk, dwell=args.dwell, row_column_scan=args.row_column)
        scanner.start()
    except Exception as e:
        raise RuntimeError(f"Failed to initialize scanning system: {e}") from e

    press_queue: SimpleQueue[None] = SimpleQueue()
    shutdown = threading.Event()

    def _on_switch() -> None:
        press_queue.put(None)

    def _pump_queue() -> None:
        while True:
            try:
                press_queue.get_nowait()
            except Empty:
                break
            scanner.on_press()
        if not shutdown.is_set():
            vk.root.after(10, _pump_queue)

    def _on_close() -> None:
        shutdown.set()
        scanner.stop()
        vk.root.destroy()

    # Start audio listener with error handling
    try:
        threading.Thread(
            target=listen,
            args=(_on_switch,),
            kwargs={
                "upper_offset": cfg.calibration.upper_offset,
                "lower_offset": cfg.calibration.lower_offset,
                "samplerate": cfg.calibration.samplerate,
                "blocksize": cfg.calibration.blocksize,
                "debounce_ms": cfg.calibration.debounce_ms,
                "device": cfg.audio.device,
                "device_mode": cfg.audio.device_mode,
            },
            daemon=True,
        ).start()
    except Exception as e:
        raise RuntimeError(f"Failed to start audio listener: {e}") from e

    # Set up GUI and start main loop
    try:
        vk.root.protocol("WM_DELETE_WINDOW", _on_close)
        vk.root.after(10, _pump_queue)
        vk.run()
    except Exception as e:
        # Clean up on GUI error
        shutdown.set()
        scanner.stop()
        raise RuntimeError(f"GUI error during operation: {e}") from e


def main(argv: list[str] | None = None) -> None:
    """Launch the GUI launcher."""
    launcher.main()


if __name__ == "__main__":  # pragma: no cover - manual entry point
    try:
        main()
    except Exception:
        _open_log_if_exists()
        raise
