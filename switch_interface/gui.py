from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Literal

import sounddevice as sd

from . import calibration, config


class FirstRunWizard(tk.Toplevel):
    """Guided setup shown on first launch."""

    def __init__(self, master: tk.Misc | None = None):
        super().__init__(master)
        self.title("Setup Wizard")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.device_var = tk.StringVar(master=self)
        self.preset_var = tk.StringVar(master=self, value="medium")
        self.status_var = tk.StringVar(master=self, value="")
        self.progress: ttk.Progressbar | None = None
        self.calib_data: dict | None = None

        self.steps: list[tk.Frame] = []
        self._build_steps()
        self._show_step(0)

        if master is not None:
            self.transient(master if isinstance(master, tk.Wm) else None)
        self.grab_set()
        self.update_idletasks()
        root = master if master is not None else self.master
        assert isinstance(root, tk.Misc)
        self.geometry(
            f"+{root.winfo_screenwidth()//2 - self.winfo_width()//2}"
            f"+{root.winfo_screenheight()//3 - self.winfo_height()//2}"
        )

    def show_modal(self) -> None:
        """Block until the wizard window is closed."""
        self.wait_window(self)

    # ---------- helpers ----------
    def _build_steps(self) -> None:
        self.steps = [
            self._step_device(),
            self._step_calibration(),
            self._step_scan_speed(),
        ]

    def _show_step(self, idx: int) -> None:
        for i, frame in enumerate(self.steps):
            frame.pack_forget()
            if i == idx:
                frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.current = idx

    # ---------- step 1 ----------
    def _step_device(self) -> tk.Frame:
        frame = tk.Frame(self)
        tk.Label(frame, text="Select audio device").pack(pady=(0, 5))
        devices = [
            (i, d["name"])
            for i, d in enumerate(sd.query_devices())
            if d.get("max_input_channels", 0) > 0
        ]
        if not devices:
            self.device_var.set("")
            names = ["None"]
        else:
            names = [f"{i}: {n}" for i, n in devices]
            self.device_var.set(names[0])
        tk.OptionMenu(frame, self.device_var, *names).pack(fill=tk.X)
        if not devices:
            tk.Label(
                frame,
                text="No microphone or line-in devices detected. Please connect one and restart.",
                wraplength=300,
            ).pack(pady=5)
            next_state: Literal["normal", "active", "disabled"] = tk.DISABLED
        else:
            next_state = tk.NORMAL
        tk.Button(
            frame, text="Next", command=lambda: self._show_step(1), state=next_state
        ).pack(pady=5)
        if not devices:
            tk.Button(frame, text="Close", command=self._on_close).pack(pady=5)
        self._device_map = {name: idx for idx, name in devices}
        return frame

    # ---------- step 2 ----------
    def _start_calibration(self) -> None:
        if self.progress:
            self.progress.start()
        self.status_var.set("")

        def worker() -> None:
            try:
                device = self._device_map.get(self.device_var.get(), None)
                self.calib_data = calibration.run_auto_calibration(device)
                msg = "Calibration successful"
            except Exception as exc:  # pragma: no cover - unexpected runtime errors
                self.calib_data = None
                msg = f"Error: {exc}"
            self.after(0, lambda: self._finish_calibration(msg))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_calibration(self, msg: str) -> None:
        if self.progress:
            self.progress.stop()
        self.status_var.set(msg)
        self.next_btn.config(state=tk.NORMAL)

    def _step_calibration(self) -> tk.Frame:
        frame = tk.Frame(self)
        tk.Label(frame, text="Auto-calibration").pack(pady=(0, 5))
        progress = ttk.Progressbar(frame, mode="indeterminate")
        progress.pack(fill=tk.X, pady=5)
        self.progress = progress
        tk.Button(frame, text="Start", command=self._start_calibration).pack()
        tk.Label(frame, textvariable=self.status_var).pack(pady=5)
        self.next_btn = tk.Button(
            frame, text="Next", command=lambda: self._show_step(2), state=tk.DISABLED
        )
        self.next_btn.pack(pady=5)
        return frame

    # ---------- step 3 ----------
    def _step_scan_speed(self) -> tk.Frame:
        frame = tk.Frame(self)
        tk.Label(frame, text="Scanning speed").pack(pady=(0, 5))
        opts = [
            ("Slow (700 ms)", "slow"),
            ("Medium (450 ms)", "medium"),
            ("Fast (250 ms)", "fast"),
        ]
        for lbl, val in opts:
            tk.Radiobutton(frame, text=lbl, value=val, variable=self.preset_var).pack(
                anchor=tk.W
            )
        tk.Button(frame, text="Finish", command=self._finish).pack(pady=5)
        return frame

    # ---------- finish ----------
    def _finish(self) -> None:
        device = self._device_map.get(self.device_var.get(), None)
        cfg = {
            "device": device,
            "scan_interval": config.get_scan_interval(self.preset_var.get()),
            "calibration": self.calib_data,
            "calibration_complete": True,
        }
        try:
            config.save(cfg)
            if self.calib_data is not None:
                calib_cfg = calibration.DetectorConfig(
                    upper_offset=self.calib_data["upper_offset"],
                    lower_offset=self.calib_data["lower_offset"],
                    samplerate=self.calib_data["samplerate"],
                    blocksize=self.calib_data["blocksize"],
                    debounce_ms=self.calib_data["debounce_ms"],
                    device=str(device) if device is not None else None,
                )
                calibration.save_config(calib_cfg)
        except Exception as exc:  # pragma: no cover - filesystem errors
            messagebox.showerror("Error", str(exc), parent=self)
        self.grab_release()
        self.destroy()

    def _on_close(self) -> None:
        self.grab_release()
        self.destroy()
