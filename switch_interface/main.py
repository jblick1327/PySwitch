from __future__ import annotations

import tkinter as tk

from . import __main__, config
from .gui import FirstRunWizard


def main() -> None:
    if not config.exists():
        root = tk.Tk()
        root.withdraw()
        wiz = FirstRunWizard(master=root)
        root.wait_window(wiz)
        root.destroy()
    cfg = config.load()
    dwell = cfg.get("scan_interval", 0.45)
    __main__.main(["--dwell", str(dwell)])


if __name__ == "__main__":  # pragma: no cover - manual launch
    main()
