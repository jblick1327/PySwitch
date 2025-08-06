"""Enhanced GUI launcher for the switch interface with improved error handling."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, ttk
from importlib import resources
from pathlib import Path
import threading
import logging
import traceback
from typing import Optional

from . import __main__, calibration, settings
from .gui import FirstRunWizard
from .error_handler import error_handler, ErrorSeverity

LAYOUT_PACKAGE = "switch_interface.resources.layouts"


def list_layouts() -> list[Path]:
    """Return available layout file paths bundled with the package."""
    files: list[Path] = []
    for entry in resources.files(LAYOUT_PACKAGE).iterdir():
        p = Path(str(entry))
        if p.name.endswith(".json"):
            files.append(p)
    return sorted(files, key=lambda p: p.name)


class EnhancedLauncher:
    """Enhanced launcher with improved error recovery and retry mechanisms."""
    
    def __init__(self):
        self.root: Optional[tk.Tk] = None
        self.layout_var: Optional[tk.StringVar] = None
        self.dwell_var: Optional[tk.DoubleVar] = None
        self.rowcol_var: Optional[tk.BooleanVar] = None
        self.status_label: Optional[tk.Label] = None
        self.start_button: Optional[tk.Button] = None
        self.safe_mode_button: Optional[tk.Button] = None
        self.retry_button: Optional[tk.Button] = None
        self.last_error: Optional[Exception] = None
        self.safe_mode_enabled = False
        
    def create_ui(self) -> None:
        """Create the launcher user interface."""
        self.root = tk.Tk()
        self.root.title("Launch Switch Interface")
        self.root.resizable(False, False)
        
        # Load settings
        cfg = settings.load()
        
        # Layout selection
        layout_paths = list_layouts()
        self.layout_var = tk.StringVar(master=self.root)
        if layout_paths:
            self.layout_var.set(layout_paths[0].name)

        tk.Label(self.root, text="Layout").pack(padx=10, pady=(10, 0))
        tk.OptionMenu(self.root, self.layout_var, *[p.name for p in layout_paths]).pack(
            fill=tk.X, padx=10
        )

        # Dwell time setting
        self.dwell_var = tk.DoubleVar(master=self.root, value=settings.get_scan_interval(cfg))
        tk.Label(self.root, text="Dwell time (s)").pack(padx=10, pady=(10, 0))
        tk.Scale(
            self.root,
            variable=self.dwell_var,
            from_=0.1,
            to=2.0,
            resolution=0.1,
            orient=tk.HORIZONTAL,
        ).pack(fill=tk.X, padx=10)

        # Row/column scanning option
        self.rowcol_var = tk.BooleanVar(master=self.root, value=False)
        tk.Checkbutton(self.root, text="Row/column scanning", variable=self.rowcol_var).pack(
            padx=10, pady=5
        )
        
        # Status label for error messages and feedback
        self.status_label = tk.Label(self.root, text="", fg="blue", wraplength=300)
        self.status_label.pack(padx=10, pady=5)
        
        # Button frame
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Calibrate button
        tk.Button(button_frame, text="Calibrate", command=self._calibrate).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        
        # Retry button (initially hidden)
        self.retry_button = tk.Button(button_frame, text="Retry", command=self._retry)
        
        # Safe mode button (initially hidden)
        self.safe_mode_button = tk.Button(button_frame, text="Safe Mode", command=self._start_safe_mode)
        
        # Start button
        self.start_button = tk.Button(button_frame, text="Start", command=self._start)
        self.start_button.pack(side=tk.RIGHT, padx=(5, 0))
        
    def _calibrate(self) -> None:
        """Handle calibration with error recovery."""
        try:
            self._update_status("Starting calibration...", "blue")
            self.root.update()
            calibration.calibrate()
            self._update_status("Calibration completed successfully!", "green")
        except Exception as e:
            error_info = error_handler.handle_error(e, "calibration")
            self._show_error_dialog(error_info)
            self._update_status("Calibration failed. You can skip it or try again.", "red")
            
    def _start(self) -> None:
        """Start the main application with enhanced error handling."""
        try:
            self._update_status("Starting Switch Interface...", "blue")
            self._hide_error_buttons()
            self.root.update()
            
            layout = resources.files(LAYOUT_PACKAGE).joinpath(self.layout_var.get())
            args = ["--layout", str(layout), "--dwell", str(self.dwell_var.get())]
            if self.rowcol_var.get():
                args.append("--row-column")
            
            # Hide launcher window during startup attempt
            self.root.withdraw()
            
            # Try to start the main application
            __main__.keyboard_main(args)
            
            # If we get here, the application started successfully and then closed
            # Show the launcher again for potential restart
            self.root.deiconify()
            self._update_status("Application closed. Ready to restart.", "blue")
            
        except Exception as e:
            # Always show the launcher again on error
            self.root.deiconify()
            self.last_error = e
            
            # Use enhanced error handler
            error_info = error_handler.handle_error(e, "application_startup")
            self._show_error_dialog(error_info)
            
            # Update status and show recovery options
            self._update_status("Startup failed. Try the suggestions above or use recovery options.", "red")
            self._show_error_buttons(error_info)
            
    def _start_safe_mode(self) -> None:
        """Start the application in safe mode with minimal functionality."""
        try:
            self._update_status("Starting in Safe Mode...", "blue")
            self._hide_error_buttons()
            self.root.update()
            
            # Use safe mode settings: simple layout, slower timing, basic functionality
            safe_layout = self._get_safe_layout()
            args = ["--layout", str(safe_layout), "--dwell", "1.0"]  # Slower timing for safety
            
            self.root.withdraw()
            __main__.keyboard_main(args)
            
            # If we get here, safe mode worked and then closed
            self.root.deiconify()
            self._update_status("Safe mode closed. Ready to restart.", "blue")
            
        except Exception as e:
            self.root.deiconify()
            self.last_error = e
            
            error_info = error_handler.handle_error(e, "safe_mode_startup")
            self._show_error_dialog(error_info)
            self._update_status("Safe mode also failed. Check hardware connections.", "red")
            
    def _retry(self) -> None:
        """Retry the last failed operation."""
        if self.safe_mode_enabled:
            self._start_safe_mode()
        else:
            self._start()
            
    def _get_safe_layout(self) -> Path:
        """Get a safe fallback layout for safe mode."""
        layout_paths = list_layouts()
        
        # Prefer simple layouts for safe mode
        safe_layout_names = ["simple_alphabet.json", "basic_test.json", "pred_test.json"]
        
        for safe_name in safe_layout_names:
            for layout_path in layout_paths:
                if layout_path.name == safe_name:
                    return resources.files(LAYOUT_PACKAGE).joinpath(safe_name)
        
        # Fallback to first available layout
        if layout_paths:
            return resources.files(LAYOUT_PACKAGE).joinpath(layout_paths[0].name)
        
        # This should never happen, but provide a fallback
        return resources.files(LAYOUT_PACKAGE).joinpath("basic_test.json")
        
    def _show_error_dialog(self, error_info: dict) -> None:
        """Show enhanced error dialog with actionable solutions."""
        title = error_info["title"]
        message = error_info["message"]
        
        # Create custom dialog with more options
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("500x400")
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (400 // 2)
        dialog.geometry(f"500x400+{x}+{y}")
        
        # Error message
        text_frame = tk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, height=15)
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget.insert(tk.END, message)
        text_widget.config(state=tk.DISABLED)
        
        # Buttons
        button_frame = tk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Button(button_frame, text="OK", command=dialog.destroy).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Show safe mode option for severe errors
        if error_info["severity"] in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            tk.Button(button_frame, text="Try Safe Mode", 
                     command=lambda: [dialog.destroy(), self._enable_safe_mode()]).pack(side=tk.RIGHT, padx=(5, 0))
        
    def _show_error_buttons(self, error_info: dict) -> None:
        """Show retry and safe mode buttons after an error."""
        self.retry_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Show safe mode button for severe errors
        if error_info["severity"] in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.safe_mode_button.pack(side=tk.RIGHT, padx=(5, 0))
            
    def _hide_error_buttons(self) -> None:
        """Hide retry and safe mode buttons."""
        self.retry_button.pack_forget()
        self.safe_mode_button.pack_forget()
        self.safe_mode_enabled = False
        
    def _enable_safe_mode(self) -> None:
        """Enable safe mode for the next startup attempt."""
        self.safe_mode_enabled = True
        self._update_status("Safe mode enabled. Click 'Retry' to start with minimal functionality.", "orange")
        
    def _update_status(self, message: str, color: str = "black") -> None:
        """Update the status label with a message."""
        if self.status_label:
            self.status_label.config(text=message, fg=color)
            
    def run(self) -> None:
        """Run the launcher main loop."""
        if self.root:
            self.root.mainloop()


def main() -> None:
    if os.getenv("SI_TEST_MODE") == "1":
        print("launcher-main-invoked")
        return

    # Handle first run wizard
    cfg = settings.load()
    if os.getenv("SKIP_FIRST_RUN") != "1" and not cfg.app.calibration_complete:
        try:
            tmp_root = tk.Tk()
            tmp_root.withdraw()
            FirstRunWizard(tmp_root).show_modal()
            tmp_root.destroy()
            cfg = settings.load()
        except Exception as e:
            # If first run wizard fails, continue to launcher with error info
            logging.error(f"First run wizard failed: {e}")
            error_info = error_handler.handle_error(e, "first_run_wizard")
            # Show a simple error message and continue
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(error_info["title"], 
                               f"{error_info['message']}\n\nContinuing to main launcher...")
            root.destroy()

    # Create and run enhanced launcher
    launcher = EnhancedLauncher()
    launcher.create_ui()
    launcher.run()


if __name__ == "__main__":  # pragma: no cover - manual entry point
    main()
