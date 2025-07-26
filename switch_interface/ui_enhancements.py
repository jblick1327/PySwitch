"""
UI Enhancement module for Switch Interface.

This module provides improved visual feedback, messaging, and accessibility
features for the Switch Interface application.
"""
import tkinter as tk
from tkinter import ttk
import time
from typing import Optional, Callable, Dict, Any, List, Tuple

# Constants for styling
COLORS = {
    "info": "#3498db",      # Blue
    "success": "#2ecc71",   # Green
    "warning": "#f39c12",   # Orange
    "error": "#e74c3c",     # Red
    "background": "#f5f5f5",
    "text": "#333333",
    "highlight": "#9b59b6"  # Purple for highlighting
}

FONTS = {
    "header": ("Helvetica", 14, "bold"),
    "subheader": ("Helvetica", 12, "bold"),
    "normal": ("Helvetica", 10),
    "small": ("Helvetica", 8),
    "button": ("Helvetica", 10, "bold")
}


class ProgressIndicator:
    """A progress indicator widget for long-running operations."""
    
    def __init__(self, parent: tk.Widget, width: int = 300, height: int = 20):
        """Initialize the progress indicator.
        
        Args:
            parent: The parent widget
            width: Width of the progress bar
            height: Height of the progress bar
        """
        self.parent = parent
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_bar = ttk.Progressbar(
            parent, 
            variable=self.progress_var,
            length=width,
            mode='determinate'
        )
        self.status_label = tk.Label(
            parent,
            text="",
            font=FONTS["small"]
        )
        
    def pack(self, **kwargs):
        """Pack the progress indicator into its parent."""
        self.progress_bar.pack(**kwargs)
        self.status_label.pack(**kwargs)
        
    def grid(self, **kwargs):
        """Grid the progress indicator into its parent."""
        row = kwargs.pop('row', 0)
        self.progress_bar.grid(row=row, **kwargs)
        self.status_label.grid(row=row+1, **kwargs)
        
    def update(self, value: float, status_text: str = ""):
        """Update the progress indicator.
        
        Args:
            value: Progress value between 0.0 and 100.0
            status_text: Optional status text to display
        """
        self.progress_var.set(value)
        if status_text:
            self.status_label.config(text=status_text)
        self.parent.update_idletasks()
        
    def start_indeterminate(self, status_text: str = "Processing..."):
        """Start indeterminate progress mode for unknown duration tasks."""
        self.progress_bar.config(mode='indeterminate')
        self.status_label.config(text=status_text)
        self.progress_bar.start()
        
    def stop_indeterminate(self):
        """Stop indeterminate progress mode."""
        self.progress_bar.stop()
        self.progress_bar.config(mode='determinate')
        self.status_label.config(text="")


class EnhancedMessageBox:
    """Enhanced message box with better formatting and accessibility."""
    
    def __init__(
        self, 
        parent: tk.Widget, 
        title: str = "", 
        message: str = "", 
        message_type: str = "info"
    ):
        """Initialize the enhanced message box.
        
        Args:
            parent: The parent widget
            title: Title of the message box
            message: Message content
            message_type: Type of message (info, success, warning, error)
        """
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.grab_set()  # Make window modal
        
        # Set window position relative to parent
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        window_width = 400
        window_height = 200
        
        x = parent_x + (parent_width - window_width) // 2
        y = parent_y + (parent_height - window_height) // 2
        
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.window.minsize(window_width, window_height)
        
        # Configure style based on message type
        bg_color = COLORS.get(message_type, COLORS["info"])
        
        # Header frame with icon and title
        header_frame = tk.Frame(self.window, bg=bg_color)
        header_frame.pack(fill=tk.X, padx=0, pady=0)
        
        # We would use icons here, but for simplicity we'll use text indicators
        icon_text = {
            "info": "ℹ️",
            "success": "✓",
            "warning": "⚠️",
            "error": "❌"
        }.get(message_type, "ℹ️")
        
        icon_label = tk.Label(
            header_frame, 
            text=icon_text, 
            font=("Helvetica", 24),
            bg=bg_color,
            fg="white"
        )
        icon_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        title_label = tk.Label(
            header_frame,
            text=title,
            font=FONTS["header"],
            bg=bg_color,
            fg="white"
        )
        title_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Message content
        content_frame = tk.Frame(self.window, bg=COLORS["background"])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        message_label = tk.Label(
            content_frame,
            text=message,
            font=FONTS["normal"],
            bg=COLORS["background"],
            fg=COLORS["text"],
            justify=tk.LEFT,
            wraplength=380
        )
        message_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Button frame
        button_frame = tk.Frame(self.window, bg=COLORS["background"])
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ok_button = tk.Button(
            button_frame,
            text="OK",
            font=FONTS["button"],
            command=self.window.destroy,
            width=10
        )
        ok_button.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Set focus to OK button for keyboard accessibility
        ok_button.focus_set()
        
        # Bind Enter key to OK button
        self.window.bind("<Return>", lambda event: self.window.destroy())
        
        # Set ARIA role for accessibility
        self.window.wm_attributes("-topmost", True)


class TooltipManager:
    """Manager for tooltips on UI elements."""
    
    def __init__(self, delay: float = 0.5):
        """Initialize the tooltip manager.
        
        Args:
            delay: Delay in seconds before showing tooltip
        """
        self.delay = delay
        self.tooltip_window = None
        self.widget = None
        self.id = None
        self.x = 0
        self.y = 0
        
    def add_tooltip(self, widget: tk.Widget, text: str):
        """Add a tooltip to a widget.
        
        Args:
            widget: The widget to add tooltip to
            text: Tooltip text
        """
        widget.bind("<Enter>", lambda event: self._schedule_tooltip(event, text))
        widget.bind("<Leave>", self._hide_tooltip)
        widget.bind("<ButtonPress>", self._hide_tooltip)
        
    def _schedule_tooltip(self, event, text: str):
        """Schedule tooltip display after delay.
        
        Args:
            event: Mouse event
            text: Tooltip text
        """
        self._hide_tooltip(event)
        self.widget = event.widget
        self.id = self.widget.after(int(self.delay * 1000), lambda: self._show_tooltip(event, text))
        
    def _show_tooltip(self, event, text: str):
        """Show the tooltip.
        
        Args:
            event: Mouse event
            text: Tooltip text
        """
        self.x = event.x_root + 20
        self.y = event.y_root + 10
        
        # Create tooltip window
        self.tooltip_window = tk.Toplevel(event.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{self.x}+{self.y}")
        
        label = tk.Label(
            self.tooltip_window,
            text=text,
            justify=tk.LEFT,
            background=COLORS["background"],
            relief="solid",
            borderwidth=1,
            font=FONTS["small"],
            padx=5,
            pady=2
        )
        label.pack()
        
    def _hide_tooltip(self, event=None):
        """Hide the tooltip."""
        if self.id:
            widget = self.widget
            id = self.id
            self.id = None
            self.widget = None
            if widget:
                widget.after_cancel(id)
        
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class StatusBar:
    """Status bar for displaying application status."""
    
    def __init__(self, parent: tk.Widget):
        """Initialize the status bar.
        
        Args:
            parent: The parent widget
        """
        self.parent = parent
        self.frame = tk.Frame(parent, bd=1, relief=tk.SUNKEN)
        
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(
            self.frame,
            textvariable=self.status_var,
            font=FONTS["small"],
            anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.progress = ttk.Progressbar(
            self.frame,
            length=100,
            mode='indeterminate'
        )
        
        # Initialize with empty status
        self.set_status("")
        
    def pack(self, **kwargs):
        """Pack the status bar into its parent."""
        self.frame.pack(fill=tk.X, **kwargs)
        
    def grid(self, **kwargs):
        """Grid the status bar into its parent."""
        self.frame.grid(**kwargs)
        
    def set_status(self, text: str, message_type: str = "info"):
        """Set the status text.
        
        Args:
            text: Status text
            message_type: Type of message (info, success, warning, error)
        """
        self.status_var.set(text)
        
        # Set color based on message type
        color = COLORS.get(message_type, COLORS["text"])
        self.status_label.config(fg=color)
        
    def show_progress(self):
        """Show progress indicator in status bar."""
        self.progress.pack(side=tk.RIGHT, padx=5, pady=2)
        self.progress.start()
        
    def hide_progress(self):
        """Hide progress indicator in status bar."""
        self.progress.stop()
        self.progress.pack_forget()


def create_enhanced_button(
    parent: tk.Widget,
    text: str,
    command: Callable,
    tooltip: str = "",
    button_type: str = "normal"
) -> tk.Button:
    """Create an enhanced button with better styling and optional tooltip.
    
    Args:
        parent: The parent widget
        text: Button text
        command: Button command
        tooltip: Optional tooltip text
        button_type: Button type (normal, primary, danger)
    
    Returns:
        The created button
    """
    # Configure button style based on type
    button_config = {
        "text": text,
        "command": command,
        "font": FONTS["button"],
        "padx": 10,
        "pady": 5,
        "cursor": "hand2"  # Hand cursor for better UX
    }
    
    # Create the button
    button = tk.Button(parent, **button_config)
    
    # Add tooltip if provided
    if tooltip:
        tooltip_manager = TooltipManager()
        tooltip_manager.add_tooltip(button, tooltip)
        
    return button


def show_message(
    parent: tk.Widget,
    title: str,
    message: str,
    message_type: str = "info"
) -> None:
    """Show an enhanced message box.
    
    Args:
        parent: The parent widget
        title: Message box title
        message: Message content
        message_type: Type of message (info, success, warning, error)
    """
    EnhancedMessageBox(parent, title, message, message_type)


def apply_high_contrast_theme(root: tk.Tk) -> None:
    """Apply high contrast theme for better accessibility.
    
    Args:
        root: The root Tk instance
    """
    # Define high contrast colors
    high_contrast = {
        "background": "#000000",  # Black
        "foreground": "#FFFFFF",  # White
        "accent": "#FFFF00",      # Yellow
        "button": "#000080",      # Navy
        "button_text": "#FFFFFF", # White
        "highlight": "#00FF00"    # Green
    }
    
    # Configure ttk styles
    style = ttk.Style(root)
    style.configure("TButton", background=high_contrast["button"], 
                   foreground=high_contrast["button_text"])
    style.configure("TLabel", background=high_contrast["background"],
                   foreground=high_contrast["foreground"])
    style.configure("TFrame", background=high_contrast["background"])
    style.configure("TProgressbar", background=high_contrast["accent"])
    
    # Configure Tk widgets
    root.configure(background=high_contrast["background"])
    
    # Update all existing widgets
    for widget in root.winfo_children():
        _update_widget_contrast(widget, high_contrast)


def _update_widget_contrast(widget, high_contrast):
    """Recursively update widgets for high contrast mode."""
    widget_type = widget.winfo_class()
    
    if widget_type in ("Button", "Label", "Message"):
        widget.configure(
            background=high_contrast["background"],
            foreground=high_contrast["foreground"],
            activebackground=high_contrast["accent"],
            activeforeground=high_contrast["background"]
        )
    elif widget_type == "Frame":
        widget.configure(background=high_contrast["background"])
    elif widget_type == "Entry":
        widget.configure(
            background=high_contrast["foreground"],
            foreground=high_contrast["background"],
            insertbackground=high_contrast["background"]
        )
    
    # Recursively update children
    for child in widget.winfo_children():
        _update_widget_contrast(child, high_contrast)


class FeedbackMessage:
    """Temporary feedback message that appears and fades out."""
    
    def __init__(
        self, 
        parent: tk.Widget, 
        message: str, 
        message_type: str = "info", 
        duration: float = 3.0
    ):
        """Initialize the feedback message.
        
        Args:
            parent: The parent widget
            message: Message content
            message_type: Type of message (info, success, warning, error)
            duration: Duration in seconds before fading out
        """
        self.parent = parent
        
        # Get parent dimensions and position
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_width = parent.winfo_width()
        
        # Create message frame
        self.frame = tk.Frame(
            parent,
            bd=1,
            relief=tk.RAISED,
            bg=COLORS.get(message_type, COLORS["info"])
        )
        
        # Message label
        self.label = tk.Label(
            self.frame,
            text=message,
            font=FONTS["normal"],
            bg=COLORS.get(message_type, COLORS["info"]),
            fg="white",
            padx=10,
            pady=5
        )
        self.label.pack(fill=tk.BOTH, expand=True)
        
        # Position at the top center of parent
        self.frame.place(
            relx=0.5,
            rely=0.1,
            anchor=tk.CENTER
        )
        
        # Schedule removal
        self.parent.after(int(duration * 1000), self.fade_out)
        
    def fade_out(self):
        """Fade out the message."""
        self.frame.destroy()


def show_feedback(
    parent: tk.Widget,
    message: str,
    message_type: str = "info",
    duration: float = 3.0
) -> None:
    """Show a temporary feedback message.
    
    Args:
        parent: The parent widget
        message: Message content
        message_type: Type of message (info, success, warning, error)
        duration: Duration in seconds before fading out
    """
    FeedbackMessage(parent, message, message_type, duration)
cla
ss AccessibilityManager:
    """Manager for application-wide accessibility features."""
    
    def __init__(self, root: tk.Tk):
        """Initialize the accessibility manager.
        
        Args:
            root: The root Tk instance
        """
        self.root = root
        self.high_contrast_mode = False
        self.screen_reader_mode = False
        self.keyboard_navigation_enabled = True
        self.large_text_mode = False
        self.focus_highlight_enabled = True
        
        # Track focused widget for keyboard navigation
        self.focused_widgets = []
        self.current_focus_index = 0
        
        # Initialize focus highlighting
        self._setup_focus_highlighting()
        
    def _setup_focus_highlighting(self):
        """Set up focus highlighting for keyboard navigation."""
        # Bind to FocusIn events at the root level
        self.root.bind_all("<FocusIn>", self._highlight_focused_widget)
        
    def _highlight_focused_widget(self, event):
        """Highlight the currently focused widget.
        
        Args:
            event: Focus event
        """
        if not self.focus_highlight_enabled:
            return
            
        widget = event.widget
        
        # Reset previous highlights
        for w in self.root.winfo_children():
            self._reset_highlight(w)
            
        # Highlight current widget
        try:
            original_bg = widget.cget("background")
            original_bd = widget.cget("bd")
            
            # Store original values as widget attributes
            widget._original_bg = original_bg
            widget._original_bd = original_bd
            
            # Apply highlight
            widget.config(bd=2)
            
            # For ttk widgets, we need a different approach
            if str(widget).startswith('.!ttk'):
                style = ttk.Style()
                style.map("TEntry", 
                         fieldbackground=[("focus", COLORS["highlight"])])
                style.map("TButton",
                         background=[("focus", COLORS["highlight"])])
        except (tk.TclError, AttributeError):
            # Some widgets don't support these configurations
            pass
    
    def _reset_highlight(self, widget):
        """Reset highlight on a widget."""
        try:
            if hasattr(widget, "_original_bg") and hasattr(widget, "_original_bd"):
                widget.config(
                    background=widget._original_bg,
                    bd=widget._original_bd
                )
        except (tk.TclError, AttributeError):
            # Some widgets don't support these configurations
            pass
            
        # Recursively reset children
        for child in widget.winfo_children():
            self._reset_highlight(child)
    
    def toggle_high_contrast(self):
        """Toggle high contrast mode."""
        self.high_contrast_mode = not self.high_contrast_mode
        
        if self.high_contrast_mode:
            apply_high_contrast_theme(self.root)
        else:
            # Reset to default theme (would need to store original theme)
            pass
            
        return self.high_contrast_mode
    
    def toggle_large_text(self):
        """Toggle large text mode."""
        self.large_text_mode = not self.large_text_mode
        
        # Scale factor for fonts
        scale = 1.5 if self.large_text_mode else 1.0
        
        # Update font sizes
        for font_name, font_tuple in FONTS.items():
            family, size, *style = font_tuple
            new_size = int(size * scale)
            
            # Recreate font tuple with new size
            if len(style) > 0:
                FONTS[font_name] = (family, new_size, style[0])
            else:
                FONTS[font_name] = (family, new_size)
                
        # Update all widgets
        self._update_widget_fonts(self.root)
        
        return self.large_text_mode
    
    def _update_widget_fonts(self, widget):
        """Recursively update widget fonts."""
        try:
            # Check if widget has font property
            current_font = widget.cget("font")
            if current_font:
                # Determine which font category this is
                for font_name, font_tuple in FONTS.items():
                    if isinstance(current_font, str):
                        # For named fonts
                        widget.config(font=font_tuple)
                        break
        except (tk.TclError, AttributeError):
            # Some widgets don't have font property
            pass
            
        # Recursively update children
        for child in widget.winfo_children():
            self._update_widget_fonts(child)
    
    def enable_keyboard_navigation(self):
        """Enable enhanced keyboard navigation."""
        if self.keyboard_navigation_enabled:
            return
            
        self.keyboard_navigation_enabled = True
        
        # Collect all focusable widgets
        self.focused_widgets = self._collect_focusable_widgets(self.root)
        
        # Bind Tab key for navigation
        self.root.bind_all("<Tab>", self._tab_navigation)
        
        # Set initial focus if no widget has focus
        if not self.root.focus_get() and self.focused_widgets:
            self.focused_widgets[0].focus_set()
            
    def disable_keyboard_navigation(self):
        """Disable enhanced keyboard navigation."""
        self.keyboard_navigation_enabled = False
        self.root.unbind_all("<Tab>")
        
    def _tab_navigation(self, event):
        """Handle Tab key navigation.
        
        Args:
            event: Key event
        """
        if not self.keyboard_navigation_enabled or not self.focused_widgets:
            return
            
        # Prevent default Tab behavior
        event.widget.tk_focusNext().focus_set()
        return "break"
    
    def _collect_focusable_widgets(self, widget):
        """Recursively collect all focusable widgets.
        
        Args:
            widget: The widget to start from
            
        Returns:
            List of focusable widgets
        """
        focusable = []
        
        # Check if this widget is focusable
        try:
            if "state" not in widget.keys() or widget.cget("state") != "disabled":
                focusable.append(widget)
        except (tk.TclError, AttributeError):
            # Widget doesn't have state or can't be checked
            pass
            
        # Recursively check children
        for child in widget.winfo_children():
            focusable.extend(self._collect_focusable_widgets(child))
            
        return focusable
    
    def add_screen_reader_support(self, widget, description):
        """Add screen reader support to a widget.
        
        Args:
            widget: The widget to add support to
            description: Accessible description
        """
        # Set ARIA attributes (this is a simulation as Tkinter doesn't directly support ARIA)
        widget.accessible_desc = description
        
        # For real screen reader support, we would use platform-specific accessibility APIs
        # This is a simplified version that adds tooltips as a visual indicator
        tooltip_manager = TooltipManager()
        tooltip_manager.add_tooltip(widget, f"Screen reader: {description}")


def create_accessible_button(
    parent: tk.Widget,
    text: str,
    command: Callable,
    description: str,
    **kwargs
) -> tk.Button:
    """Create an accessible button with screen reader support.
    
    Args:
        parent: The parent widget
        text: Button text
        command: Button command
        description: Accessible description
        **kwargs: Additional button parameters
        
    Returns:
        The created button
    """
    button = tk.Button(parent, text=text, command=command, **kwargs)
    
    # Add screen reader description
    button.accessible_desc = description
    
    # Ensure keyboard accessibility
    button.bind("<Return>", lambda e: command())
    button.bind("<space>", lambda e: command())
    
    return button


def create_accessibility_toolbar(parent: tk.Widget, acc_manager: AccessibilityManager) -> tk.Frame:
    """Create a toolbar with accessibility options.
    
    Args:
        parent: The parent widget
        acc_manager: The accessibility manager
        
    Returns:
        Frame containing the accessibility toolbar
    """
    frame = tk.Frame(parent, bd=1, relief=tk.RAISED)
    
    # High contrast toggle
    high_contrast_btn = create_accessible_button(
        frame,
        text="High Contrast",
        command=acc_manager.toggle_high_contrast,
        description="Toggle high contrast mode for better visibility"
    )
    high_contrast_btn.pack(side=tk.LEFT, padx=5, pady=2)
    
    # Large text toggle
    large_text_btn = create_accessible_button(
        frame,
        text="Large Text",
        command=acc_manager.toggle_large_text,
        description="Toggle large text mode for better readability"
    )
    large_text_btn.pack(side=tk.LEFT, padx=5, pady=2)
    
    # Keyboard navigation toggle
    keyboard_nav_var = tk.BooleanVar(value=True)
    keyboard_nav_check = tk.Checkbutton(
        frame,
        text="Keyboard Navigation",
        variable=keyboard_nav_var,
        command=lambda: acc_manager.enable_keyboard_navigation() 
                if keyboard_nav_var.get() 
                else acc_manager.disable_keyboard_navigation()
    )
    keyboard_nav_check.pack(side=tk.LEFT, padx=5, pady=2)
    acc_manager.add_screen_reader_support(
        keyboard_nav_check, 
        "Toggle enhanced keyboard navigation"
    )
    
    return frame


def make_widget_accessible(widget: tk.Widget, description: str) -> None:
    """Make a widget accessible by adding ARIA attributes and keyboard support.
    
    Args:
        widget: The widget to make accessible
        description: Accessible description
    """
    # Add accessible description
    widget.accessible_desc = description
    
    # Add keyboard support based on widget type
    widget_type = widget.winfo_class()
    
    if widget_type == "Button":
        # Buttons already have keyboard support in Tkinter
        pass
    elif widget_type == "Entry":
        # Entries already have keyboard support
        pass
    elif widget_type == "Checkbutton":
        # Add space key support
        original_command = widget.cget("command")
        widget.bind("<space>", lambda e: original_command())
    elif widget_type == "Radiobutton":
        # Add space key support
        original_command = widget.cget("command")
        widget.bind("<space>", lambda e: original_command())
    
    # Add tooltip as visual indicator of accessibility
    tooltip_manager = TooltipManager()
    tooltip_manager.add_tooltip(widget, f"Accessible: {description}")


def setup_accessibility(root: tk.Tk) -> AccessibilityManager:
    """Set up accessibility features for the application.
    
    Args:
        root: The root Tk instance
        
    Returns:
        The created AccessibilityManager
    """
    acc_manager = AccessibilityManager(root)
    acc_manager.enable_keyboard_navigation()
    
    # Create accessibility menu
    if hasattr(root, 'menubar'):
        accessibility_menu = tk.Menu(root.menubar, tearoff=0)
        root.menubar.add_cascade(label="Accessibility", menu=accessibility_menu)
        
        accessibility_menu.add_checkbutton(
            label="High Contrast Mode",
            command=acc_manager.toggle_high_contrast
        )
        
        accessibility_menu.add_checkbutton(
            label="Large Text Mode",
            command=acc_manager.toggle_large_text
        )
        
        accessibility_menu.add_checkbutton(
            label="Enhanced Keyboard Navigation",
            command=acc_manager.enable_keyboard_navigation,
            onvalue=True,
            offvalue=False,
            variable=tk.BooleanVar(value=True)
        )
    
    return acc_manager