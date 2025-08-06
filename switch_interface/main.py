from __future__ import annotations

import tkinter as tk

from . import __main__, settings
from .gui import FirstRunWizard


def main() -> None:
    cfg = settings.load()
    if not cfg.app.calibration_complete:
        root = tk.Tk()
        root.withdraw()
        wiz = FirstRunWizard(master=root)
        root.wait_window(wiz)
        root.destroy()
        cfg = settings.load()  # Reload after wizard
    dwell = settings.get_scan_interval(cfg)
    __main__.keyboard_main(["--dwell", str(dwell)])


if __name__ == "__main__":  # pragma: no cover - manual launch
    main()
