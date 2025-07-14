from __future__ import annotations

import os
import tkinter as tk

from . import __main__, config
from .gui import FirstRunWizard


def main() -> None:
    settings = config.load()
    root = tk.Tk()
    root.withdraw()
    if os.getenv("SKIP_FIRST_RUN") != "1":
        if not settings.get("calibration_complete"):
            FirstRunWizard(root).show_modal()
            settings = config.load()
    root.destroy()
    dwell = settings.get("scan_interval", 0.45)
    __main__.keyboard_main(["--dwell", str(dwell)])


if __name__ == "__main__":  # pragma: no cover - manual launch
    main()
