from __future__ import annotations

import os
import tkinter as tk

from . import __main__, settings
from .gui import FirstRunWizard


def main() -> None:
    config = settings.load()
    root = tk.Tk()
    root.withdraw()
    if os.getenv("SKIP_FIRST_RUN") != "1":
        if not config.app.calibration_complete:
            FirstRunWizard(root).show_modal()
            config = settings.load()
    root.destroy()
    dwell = settings.get_scan_interval(config)
    __main__.keyboard_main(["--dwell", str(dwell)])


if __name__ == "__main__":  # pragma: no cover - manual launch
    main()
