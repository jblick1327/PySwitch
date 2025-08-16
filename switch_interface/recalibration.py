"""Recalibration functionality for the Switch Interface."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional

from .audio_device_manager import AudioDeviceManager
from .calibration import DetectorConfig, calibrate, load_config, save_config

logger = logging.getLogger(__name__)


def show_recalibration_dialog(
    parent: Optional[tk.Tk | tk.Toplevel] = None,
    on_complete: Optional[Callable[[DetectorConfig], None]] = None,
) -> None:
    """Show recalibration dialog without requiring application restart.

    Args:
        parent: Parent window
        on_complete: Callback function when recalibration completes
    """
    # Load current calibration settings
    try:
        current_config = load_config()
    except Exception as exc:
        logger.warning(f"Failed to load calibration config: {exc}")
        current_config = DetectorConfig()

    # Create dialog
    dialog = tk.Toplevel(parent)
    dialog.title("Recalibration")
    dialog.geometry("400x300")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    # Center dialog on parent
    if parent:
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (400 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (300 // 2)
        dialog.geometry(f"+{x}+{y}")

    # Create content
    tk.Label(
        dialog, text="Recalibrate Switch Detection", font=("TkDefaultFont", 12, "bold")
    ).pack(pady=(15, 5))

    tk.Label(
        dialog,
        text="You can recalibrate your switch without restarting the application.",
        wraplength=350,
    ).pack(pady=5)

    # Show current settings
    settings_frame = tk.Frame(dialog, relief=tk.RIDGE, borderwidth=1)
    settings_frame.pack(fill=tk.X, padx=15, pady=10)

    tk.Label(
        settings_frame, text="Current Settings:", font=("TkDefaultFont", 10, "bold")
    ).pack(anchor=tk.W, padx=10, pady=5)

    tk.Label(
        settings_frame,
        text=f"Upper Threshold: {current_config.upper_offset:.2f}",
        anchor=tk.W,
    ).pack(fill=tk.X, padx=10)

    tk.Label(
        settings_frame,
        text=f"Lower Threshold: {current_config.lower_offset:.2f}",
        anchor=tk.W,
    ).pack(fill=tk.X, padx=10)

    tk.Label(
        settings_frame, text=f"Debounce: {current_config.debounce_ms} ms", anchor=tk.W
    ).pack(fill=tk.X, padx=10)

    device_name = current_config.device or "Default"
    tk.Label(settings_frame, text=f"Device: {device_name}", anchor=tk.W).pack(
        fill=tk.X, padx=10, pady=(0, 5)
    )

    # Options
    def start_manual_calibration():
        dialog.withdraw()

        def on_calibration_complete(new_config: DetectorConfig):
            # Save new configuration
            try:
                save_config(new_config)
                messagebox.showinfo(
                    "Recalibration Complete",
                    "Switch calibration has been updated successfully!",
                )

                # Call completion callback if provided
                if on_complete:
                    on_complete(new_config)
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to save calibration: {exc}")

            dialog.destroy()

        # Start calibration with parent and callback
        calibrate(current_config, parent, on_calibration_complete)

    def start_auto_calibration():
        dialog.withdraw()

        try:
            # Show instructions
            messagebox.showinfo(
                "Auto Calibration",
                "Press your switch 3-5 times when prompted.\n"
                "Calibration will begin in 2 seconds.",
            )

            import time

            time.sleep(2)

            # Run auto calibration
            from .calibration import run_auto_calibration

            auto_settings = run_auto_calibration(current_config.device)

            # Create new config from auto settings
            new_config = DetectorConfig(
                upper_offset=auto_settings["upper_offset"],
                lower_offset=auto_settings["lower_offset"],
                samplerate=auto_settings["samplerate"],
                blocksize=auto_settings["blocksize"],
                debounce_ms=auto_settings["debounce_ms"],
                device=auto_settings["device"],
            )

            # Save new configuration
            save_config(new_config)

            messagebox.showinfo(
                "Auto Calibration Complete",
                "Switch calibration has been updated successfully!",
            )

            # Call completion callback if provided
            if on_complete:
                on_complete(new_config)

        except Exception as exc:
            messagebox.showerror(
                "Auto Calibration Error", f"Auto-calibration failed: {exc}"
            )

        dialog.destroy()

    def try_alternative_device():
        # Find alternative device
        manager = AudioDeviceManager()
        working_device, error, mode = manager.find_working_device(
            None, current_config.samplerate, current_config.blocksize  # Try any device
        )

        if working_device is not None:
            # Update config with new device
            new_config = DetectorConfig(
                upper_offset=current_config.upper_offset,
                lower_offset=current_config.lower_offset,
                samplerate=current_config.samplerate,
                blocksize=current_config.blocksize,
                debounce_ms=current_config.debounce_ms,
                device=working_device,
            )

            # Save new configuration
            try:
                save_config(new_config)
                messagebox.showinfo(
                    "Device Changed",
                    f"Audio device has been changed to: {working_device}",
                )

                # Call completion callback if provided
                if on_complete:
                    on_complete(new_config)

                dialog.destroy()
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to save configuration: {exc}")
        else:
            messagebox.showerror(
                "No Devices Found", f"No working audio devices found: {error}"
            )

    # Button frame
    button_frame = tk.Frame(dialog)
    button_frame.pack(pady=15)

    tk.Button(
        button_frame,
        text="Manual Calibration",
        command=start_manual_calibration,
        width=15,
    ).pack(side=tk.LEFT, padx=5)

    tk.Button(
        button_frame, text="Auto Calibration", command=start_auto_calibration, width=15
    ).pack(side=tk.LEFT, padx=5)

    # Additional options
    options_frame = tk.Frame(dialog)
    options_frame.pack(pady=5)

    tk.Button(
        options_frame, text="Try Different Device", command=try_alternative_device
    ).pack(side=tk.LEFT, padx=5)

    tk.Button(options_frame, text="Cancel", command=dialog.destroy).pack(
        side=tk.LEFT, padx=5
    )
