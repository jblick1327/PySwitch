"""Command line entry point for the virtual keyboard interface."""

from __future__ import annotations

from switch_interface.logging import setup as _setup_logging

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


def main(argv: list[str] | None = None) -> None:
    """Launch the scanning keyboard interface."""
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

    from .calibration import calibrate, load_config, save_config
    from .detection import check_device, listen
    from .kb_gui import VirtualKeyboard
    from .kb_layout_io import load_keyboard
    from .pc_control import PCController
    from .scan_engine import Scanner

    cfg = load_config()
    if args.calibrate:
        cfg = calibrate(cfg)
        save_config(cfg)

    ready = threading.Event()

    def _verify() -> None:
        try:
            check_device(
                samplerate=cfg.samplerate,
                blocksize=cfg.blocksize,
                device=cfg.device,
            )
        except Exception as e:  # pragma: no cover - just logs
            logging.warning(
                "Audio check failed: %s \u2013 continuing in shared mode", e
            )
        finally:
            ready.set()

    threading.Thread(target=_verify, daemon=True).start()
    if not ready.wait(2.0):
        logging.warning(
            "Audio device check timed out \u2013 proceeding without exclusive access"
        )

    pc_controller = PCController()
    try:
        keyboard = load_keyboard(args.layout)
    except FileNotFoundError:
        parser.error(f"Layout file '{args.layout}' not found")
    except json.JSONDecodeError as exc:
        parser.error(f"Invalid JSON in layout file '{args.layout}': {exc.msg}")

    vk = VirtualKeyboard(
        keyboard, on_key=pc_controller.on_key, state=pc_controller.state
    )

    scanner = Scanner(vk, dwell=args.dwell, row_column_scan=args.row_column)
    scanner.start()

    press_queue: SimpleQueue[None] = SimpleQueue()

    def _on_switch() -> None:
        press_queue.put(None)

    def _pump_queue() -> None:
        while True:
            try:
                press_queue.get_nowait()
            except Empty:
                break
            scanner.on_press()
        vk.root.after(10, _pump_queue)

    threading.Thread(
        target=listen,
        args=(_on_switch, cfg),
        daemon=True,
    ).start()
    vk.root.after(10, _pump_queue)
    vk.run()


if __name__ == "__main__":  # pragma: no cover - manual entry point
    try:
        main()
    except Exception:
        _open_log_if_exists()
        raise
