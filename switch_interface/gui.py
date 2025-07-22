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
        # Clear existing content
        for widget in self.winfo_children():
            widget.destroy()
            
        # Add enhanced progress indicator at the top
        progress_frame = tk.Frame(self, bg="#F8F9FA")
        progress_frame.pack(fill=tk.X, padx=0, pady=0)
        
        step_names = ["Audio Device", "Calibration", "Scan Speed"]
        step_descriptions = [
            "Select your switch interface",
            "Configure switch detection", 
            "Set scanning preferences"
        ]
        
        # Main progress header
        header_frame = tk.Frame(progress_frame, bg="#F8F9FA")
        header_frame.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(
            header_frame, 
            text=f"Setup Wizard - Step {idx + 1} of {len(step_names)}", 
            font=("TkDefaultFont", 11, "bold"),
            bg="#F8F9FA"
        ).pack()
        
        tk.Label(
            header_frame,
            text=f"{step_names[idx]}: {step_descriptions[idx]}",
            font=("TkDefaultFont", 9),
            fg="#6C757D",
            bg="#F8F9FA"
        ).pack()
        
        # Visual progress bar with step indicators
        progress_visual = tk.Frame(progress_frame, bg="#F8F9FA")
        progress_visual.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        for i in range(len(step_names)):
            step_frame = tk.Frame(progress_visual, bg="#F8F9FA")
            step_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Step circle
            if i <= idx:
                circle_color = "#28A745"  # Green for completed/current
                text_color = "white"
                step_text = "✓" if i < idx else str(i + 1)
            else:
                circle_color = "#E9ECEF"  # Gray for future steps
                text_color = "#6C757D"
                step_text = str(i + 1)
            
            circle = tk.Label(
                step_frame,
                text=step_text,
                bg=circle_color,
                fg=text_color,
                font=("TkDefaultFont", 8, "bold"),
                width=3,
                height=1
            )
            circle.pack()
            
            # Step name
            tk.Label(
                step_frame,
                text=step_names[i],
                font=("TkDefaultFont", 7),
                fg="#6C757D" if i > idx else "#495057",
                bg="#F8F9FA"
            ).pack()
            
            # Connection line (except for last step)
            if i < len(step_names) - 1:
                line_color = "#28A745" if i < idx else "#E9ECEF"
                line = tk.Frame(step_frame, bg=line_color, height=2)
                line.pack(fill=tk.X, padx=10, pady=5)
        
        # Separator line
        tk.Frame(self, bg="#DEE2E6", height=1).pack(fill=tk.X)
        
        # Rebuild and show current step
        self.steps.clear()
        self._build_steps()
        
        if 0 <= idx < len(self.steps):
            self.steps[idx].pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        self.current = idx

    # ---------- step 1 ----------
    def _step_device(self) -> tk.Frame:
        frame = tk.Frame(self)
        tk.Label(frame, text="Select audio device", font=("TkDefaultFont", 10, "bold")).pack(pady=(0, 5))
        
        # Add helpful instruction text
        instruction = tk.Label(
            frame,
            text="Choose the microphone or audio input device connected to your switch.",
            wraplength=300,
            justify=tk.CENTER
        )
        instruction.pack(pady=5)
        
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
        tk.OptionMenu(frame, self.device_var, *names).pack(fill=tk.X, pady=5)
        
        if not devices:
            # Enhanced guidance for no microphone detected
            error_frame = tk.Frame(frame, relief=tk.RAISED, borderwidth=1, bg="#FFF3CD")
            error_frame.pack(fill=tk.X, pady=10, padx=5)
            
            tk.Label(
                error_frame,
                text="⚠ No audio input devices detected",
                font=("TkDefaultFont", 10, "bold"),
                fg="#856404",
                bg="#FFF3CD"
            ).pack(pady=5)
            
            # Detailed help section
            help_text = tk.Text(
                error_frame, 
                height=8, 
                wrap=tk.WORD, 
                font=("TkDefaultFont", 8),
                bg="#FFF3CD",
                relief=tk.FLAT
            )
            help_text.pack(fill=tk.X, padx=10, pady=5)
            help_text.insert(tk.END, 
                "To connect your switch interface:\n\n"
                "Hardware Setup:\n"
                "• Connect your microphone or switch interface device\n"
                "• For USB devices, try different USB ports\n"
                "• Ensure the device is powered on (if applicable)\n\n"
                "System Settings:\n"
                "• Windows: Settings > System > Sound > Input\n"
                "• macOS: System Preferences > Sound > Input\n"
                "• Linux: Check PulseAudio/ALSA settings\n\n"
                "Don't worry - you can continue with default settings and set up audio later!"
            )
            help_text.config(state=tk.DISABLED)
            
            # Progress indicator for troubleshooting
            progress_label = tk.Label(
                error_frame,
                text="💡 Tip: Most switch interfaces work as standard microphones",
                font=("TkDefaultFont", 8, "italic"),
                bg="#FFF3CD",
                fg="#856404"
            )
            progress_label.pack(pady=2)
            
            # Button frame for refresh and continue options
            button_frame = tk.Frame(error_frame, bg="#FFF3CD")
            button_frame.pack(pady=8)
            
            refresh_btn = tk.Button(
                button_frame, 
                text="🔄 Refresh Devices", 
                command=self._refresh_devices,
                bg="#17A2B8",
                fg="white"
            )
            refresh_btn.pack(side=tk.LEFT, padx=5)
            
            continue_btn = tk.Button(
                button_frame, 
                text="Continue with Defaults", 
                command=lambda: self._show_step(1),
                bg="#28A745",
                fg="white"
            )
            continue_btn.pack(side=tk.LEFT, padx=5)
            
            help_btn = tk.Button(
                button_frame,
                text="Get Help",
                command=self._show_audio_help
            )
            help_btn.pack(side=tk.LEFT, padx=5)
            
            next_state: Literal["normal", "active", "disabled"] = tk.DISABLED
        else:
            next_state = tk.NORMAL
            
        self.device_next_btn = tk.Button(
            frame, text="Next", command=lambda: self._show_step(1), state=next_state
        )
        self.device_next_btn.pack(pady=5)
        
        self._device_map = {name: idx for idx, name in devices}
        return frame

    # ---------- step 2 ----------
    def _start_calibration(self) -> None:
        if self.progress:
            self.progress.start()
        self.status_var.set("Calibrating... Please make some switch presses now.")

        def worker() -> None:
            try:
                device = self._device_map.get(self.device_var.get(), None)
                self.calib_data = calibration.run_auto_calibration(device)
                msg = "Calibration successful! Switch detection is ready."
            except Exception as exc:  # pragma: no cover - unexpected runtime errors
                self.calib_data = None
                # Provide more helpful error messages
                if "No Default Input Device" in str(exc) or "Invalid device" in str(exc):
                    msg = "Error: No microphone detected. Please check your audio device connection."
                elif "Permission" in str(exc):
                    msg = "Error: Permission denied. Please allow microphone access in system settings."
                elif "Device unavailable" in str(exc):
                    msg = "Error: Audio device is busy. Please close other audio applications and try again."
                else:
                    msg = f"Calibration failed: {exc}"
            self.after(0, lambda: self._finish_calibration(msg))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_calibration(self, msg: str) -> None:
        if self.progress:
            self.progress.stop()
        self.status_var.set(msg)
        
        # Enable Next button if calibration was successful or skipped
        if self.calib_data is not None:
            self.next_btn.config(state=tk.NORMAL)
            # Hide retry and help buttons if they exist
            if hasattr(self, 'retry_btn'):
                self.retry_btn.pack_forget()
            if hasattr(self, 'help_frame'):
                self.help_frame.pack_forget()
        else:
            # Show retry options and help for failed calibration
            if not hasattr(self, 'retry_btn'):
                retry_frame = tk.Frame(self.steps[1])
                retry_frame.pack(pady=5)
                
                self.retry_btn = tk.Button(
                    retry_frame, 
                    text="Retry Calibration", 
                    command=self._start_calibration,
                    bg="#2196F3",
                    fg="white"
                )
                self.retry_btn.pack(side=tk.LEFT, padx=5)
                
                skip_after_fail_btn = tk.Button(
                    retry_frame,
                    text="Use Default Settings",
                    command=self._skip_calibration
                )
                skip_after_fail_btn.pack(side=tk.LEFT, padx=5)
            else:
                self.retry_btn.pack(pady=5)
            
            # Show helpful troubleshooting information
            if not hasattr(self, 'help_frame'):
                self.help_frame = tk.Frame(self.steps[1], relief=tk.RIDGE, borderwidth=1)
                self.help_frame.pack(fill=tk.X, pady=10, padx=10)
                
                tk.Label(
                    self.help_frame, 
                    text="Troubleshooting Tips:", 
                    font=("TkDefaultFont", 9, "bold")
                ).pack(pady=(5, 2))
                
                tips_text = tk.Text(self.help_frame, height=4, wrap=tk.WORD, font=("TkDefaultFont", 8))
                tips_text.pack(fill=tk.X, padx=10, pady=5)
                
                if "No microphone detected" in msg or "No Default Input Device" in msg:
                    tips_text.insert(tk.END, 
                        "• Check that your microphone is connected and powered on\n"
                        "• Verify the device appears in your system's sound settings\n"
                        "• Try a different USB port if using a USB microphone\n"
                        "• You can continue with default settings if needed"
                    )
                elif "Permission denied" in msg:
                    tips_text.insert(tk.END,
                        "• Allow microphone access in your system privacy settings\n"
                        "• On Windows: Settings > Privacy > Microphone\n"
                        "• On macOS: System Preferences > Security & Privacy > Microphone\n"
                        "• Restart the application after granting permission"
                    )
                elif "Device unavailable" in msg or "busy" in msg:
                    tips_text.insert(tk.END,
                        "• Close other applications that might be using your microphone\n"
                        "• Check if video calling apps are running (Zoom, Teams, etc.)\n"
                        "• Try selecting a different audio device in the previous step\n"
                        "• Restart your computer if the problem persists"
                    )
                else:
                    tips_text.insert(tk.END,
                        "• Make sure your switch is connected and working\n"
                        "• Try pressing your switch a few times during calibration\n"
                        "• Check that the microphone is close to your switch\n"
                        "• You can skip calibration and use default settings"
                    )
                
                tips_text.config(state=tk.DISABLED)
            else:
                self.help_frame.pack(fill=tk.X, pady=10, padx=10)

    def _skip_calibration(self) -> None:
        """Skip calibration and use sensible default settings."""
        device = self._device_map.get(self.device_var.get(), None)
        
        # Create default calibration settings that work for most users
        # These settings are conservative and should work with most switch setups
        self.calib_data = {
            "upper_offset": -0.15,  # Conservative threshold - not too sensitive
            "lower_offset": -0.6,   # Wide hysteresis gap to prevent false triggers
            "samplerate": 44100,    # Standard sample rate
            "blocksize": 256,       # Standard block size for good responsiveness
            "debounce_ms": 75,      # Longer debounce to prevent accidental double-presses
            "device": device,
        }
        
        self.status_var.set("✓ Using default settings - your switch will work with most common setups")
        self.next_btn.config(state=tk.NORMAL)
        
        # Hide retry button if it exists
        if hasattr(self, 'retry_btn'):
            self.retry_btn.pack_forget()

    def _refresh_devices(self) -> None:
        """Refresh the device list and rebuild the device selection step."""
        # Rebuild the steps to refresh device list
        self.steps.clear()
        self._build_steps()
        self._show_step(0)

    def _show_audio_help(self) -> None:
        """Show detailed audio setup help in a popup window."""
        help_window = tk.Toplevel(self)
        help_window.title("Audio Device Setup Help")
        help_window.geometry("500x400")
        help_window.resizable(True, True)
        help_window.transient(self)
        
        # Create scrollable text widget
        text_frame = tk.Frame(help_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        help_text = tk.Text(
            text_frame, 
            wrap=tk.WORD, 
            yscrollcommand=scrollbar.set,
            font=("TkDefaultFont", 9)
        )
        help_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=help_text.yview)
        
        help_content = """Audio Device Setup Guide

COMMON SWITCH INTERFACES:
• Microphone-based switches (most common)
• USB switch interfaces
• Audio jack adapters
• Bluetooth audio switches

WINDOWS SETUP:
1. Connect your switch interface device
2. Open Settings > System > Sound
3. Under "Input", select your device
4. Test by speaking/activating your switch
5. Adjust input volume if needed

MACOS SETUP:
1. Connect your switch interface device
2. Open System Preferences > Sound
3. Click the "Input" tab
4. Select your device from the list
5. Test the input level meter

LINUX SETUP:
1. Connect your switch interface device
2. Open sound settings (varies by distribution)
3. Select input device
4. Or use command: pactl list sources

TROUBLESHOOTING:
• Device not appearing? Try different USB ports
• No sound detected? Check device volume/gain
• Permission errors? Allow microphone access
• Still having issues? Try restarting the computer

TESTING YOUR SETUP:
• Use your system's sound recorder
• Activate your switch and look for audio input
• The switch should create a clear audio signal

If you continue to have problems, you can skip calibration and use default settings. The application will still work with most switch setups."""
        
        help_text.insert(tk.END, help_content)
        help_text.config(state=tk.DISABLED)
        
        # Close button
        tk.Button(
            help_window, 
            text="Close", 
            command=help_window.destroy
        ).pack(pady=10)

    def _step_calibration(self) -> tk.Frame:
        frame = tk.Frame(self)
        tk.Label(frame, text="Switch Calibration", font=("TkDefaultFont", 10, "bold")).pack(pady=(0, 5))
        
        # Add detailed explanation text
        explanation = tk.Label(
            frame,
            text="Calibration customizes switch detection for your specific setup.\n"
                 "This improves accuracy but is optional.",
            wraplength=350,
            justify=tk.CENTER,
            font=("TkDefaultFont", 9)
        )
        explanation.pack(pady=5)
        
        # Add information frame about what each option does
        info_frame = tk.Frame(frame, relief=tk.RIDGE, borderwidth=1)
        info_frame.pack(fill=tk.X, pady=10, padx=10)
        
        tk.Label(info_frame, text="Your Options:", font=("TkDefaultFont", 9, "bold")).pack(pady=(5, 2))
        
        calibrate_info = tk.Label(
            info_frame,
            text="• Start Calibration: Customize detection for your switch (recommended)",
            wraplength=320,
            justify=tk.LEFT,
            font=("TkDefaultFont", 8)
        )
        calibrate_info.pack(anchor=tk.W, padx=10, pady=1)
        
        skip_info = tk.Label(
            info_frame,
            text="• Skip Calibration: Use default settings that work with most switches",
            wraplength=320,
            justify=tk.LEFT,
            font=("TkDefaultFont", 8)
        )
        skip_info.pack(anchor=tk.W, padx=10, pady=(1, 5))
        
        progress = ttk.Progressbar(frame, mode="indeterminate")
        progress.pack(fill=tk.X, pady=5)
        self.progress = progress
        
        # Button frame for Start and Skip buttons
        button_frame = tk.Frame(frame)
        button_frame.pack(pady=10)
        
        start_btn = tk.Button(
            button_frame, 
            text="Start Calibration", 
            command=self._start_calibration,
            bg="#4CAF50",
            fg="white",
            font=("TkDefaultFont", 9, "bold")
        )
        start_btn.pack(side=tk.LEFT, padx=5)
        
        skip_btn = tk.Button(
            button_frame, 
            text="Skip Calibration", 
            command=self._skip_calibration,
            font=("TkDefaultFont", 9)
        )
        skip_btn.pack(side=tk.LEFT, padx=5)
        
        # Status label with better formatting
        status_label = tk.Label(frame, textvariable=self.status_var, wraplength=350, justify=tk.CENTER)
        status_label.pack(pady=5)
        
        self.next_btn = tk.Button(
            frame, text="Next", command=lambda: self._show_step(2), state=tk.DISABLED
        )
        self.next_btn.pack(pady=5)
        return frame

    # ---------- step 3 ----------
    def _step_scan_speed(self) -> tk.Frame:
        frame = tk.Frame(self)
        tk.Label(frame, text="Scanning Speed Preferences", font=("TkDefaultFont", 10, "bold")).pack(pady=(0, 5))
        
        # Add detailed explanation
        help_text = tk.Label(
            frame,
            text="Scanning speed controls how fast the keyboard highlights move.\n"
                 "Choose a comfortable speed - you can always change this later.",
            wraplength=350,
            justify=tk.CENTER,
            font=("TkDefaultFont", 9)
        )
        help_text.pack(pady=5)
        
        # Speed options with better descriptions
        options_frame = tk.Frame(frame)
        options_frame.pack(pady=10)
        
        opts = [
            ("Very Slow (1.2s) - For users with limited mobility", "very_slow"),
            ("Slow (0.8s) - Recommended for beginners", "slow"),
            ("Medium (0.6s) - Good balance of speed and control", "medium"),
            ("Fast (0.4s) - For experienced users", "fast"),
            ("Very Fast (0.25s) - For expert users", "very_fast"),
        ]
        
        for lbl, val in opts:
            rb = tk.Radiobutton(
                options_frame, 
                text=lbl, 
                value=val, 
                variable=self.preset_var,
                font=("TkDefaultFont", 9),
                wraplength=350,
                justify=tk.LEFT
            )
            rb.pack(anchor=tk.W, pady=3, padx=10)
        
        # Add helpful tips
        tips_frame = tk.Frame(frame, relief=tk.RIDGE, borderwidth=1)
        tips_frame.pack(fill=tk.X, pady=10, padx=10)
        
        tk.Label(tips_frame, text="💡 Tips for choosing speed:", font=("TkDefaultFont", 9, "bold")).pack(pady=(5, 2))
        
        tips_text = tk.Text(tips_frame, height=3, wrap=tk.WORD, font=("TkDefaultFont", 8))
        tips_text.pack(fill=tk.X, padx=10, pady=5)
        tips_text.insert(tk.END,
            "• Start slower than you think you need - you can always speed up later\n"
            "• Slower speeds reduce accidental selections and fatigue\n"
            "• You can adjust this anytime in the application settings"
        )
        tips_text.config(state=tk.DISABLED)
        
        # Add note about changing settings later
        note = tk.Label(
            frame,
            text="Don't worry - all these settings can be changed later!",
            font=("TkDefaultFont", 8, "italic"),
            fg="#28A745"
        )
        note.pack(pady=5)
        
        finish_btn = tk.Button(
            frame, 
            text="🎉 Finish Setup", 
            command=self._finish,
            bg="#28A745",
            fg="white",
            font=("TkDefaultFont", 10, "bold"),
            padx=20,
            pady=5
        )
        finish_btn.pack(pady=15)
        
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
