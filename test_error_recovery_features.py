#!/usr/bin/env python3
"""Comprehensive test for enhanced launcher error recovery features."""

import os
import sys
import tkinter as tk
from unittest.mock import Mock, patch, MagicMock
import tempfile

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_launcher_remains_open_on_error():
    """Test that launcher remains open when errors occur."""
    from switch_interface.launcher import EnhancedLauncher
    
    with patch('tkinter.Tk') as mock_tk, \
         patch('switch_interface.launcher.resources') as mock_resources, \
         patch('switch_interface.__main__.keyboard_main') as mock_keyboard_main:
        
        # Setup mocks
        mock_root = Mock()
        mock_tk.return_value = mock_root
        mock_keyboard_main.side_effect = RuntimeError("Test startup error")
        
        launcher = EnhancedLauncher()
        launcher.create_ui()
        
        # Simulate start button click that causes error
        launcher._start()
        
        # Verify launcher window is shown again after error
        mock_root.deiconify.assert_called()
        print("✓ Launcher remains open on error")

def test_retry_mechanism():
    """Test retry mechanism for failed operations."""
    from switch_interface.launcher import EnhancedLauncher
    
    with patch('tkinter.Tk') as mock_tk, \
         patch('switch_interface.launcher.resources') as mock_resources:
        
        mock_root = Mock()
        mock_tk.return_value = mock_root
        
        launcher = EnhancedLauncher()
        launcher.create_ui()
        
        # Mock the _start method to track calls
        launcher._start = Mock()
        
        # Test retry functionality
        launcher._retry()
        launcher._start.assert_called_once()
        print("✓ Retry mechanism works")

def test_safe_mode_functionality():
    """Test safe mode option for minimal functionality."""
    from switch_interface.launcher import EnhancedLauncher
    
    with patch('tkinter.Tk') as mock_tk, \
         patch('switch_interface.launcher.resources') as mock_resources, \
         patch('switch_interface.__main__.keyboard_main') as mock_keyboard_main:
        
        mock_root = Mock()
        mock_tk.return_value = mock_root
        
        launcher = EnhancedLauncher()
        launcher.create_ui()
        
        # Test safe mode startup
        launcher._start_safe_mode()
        
        # Verify keyboard_main was called with safe mode parameters
        mock_keyboard_main.assert_called()
        args = mock_keyboard_main.call_args[0][0]
        assert "--dwell" in args
        assert "1.0" in args  # Safe mode uses slower timing
        print("✓ Safe mode functionality works")

def test_error_dialog_with_actionable_solutions():
    """Test enhanced error dialog with actionable solutions."""
    from switch_interface.launcher import EnhancedLauncher
    from switch_interface.error_handler import ErrorSeverity
    
    with patch('tkinter.Tk') as mock_tk, \
         patch('tkinter.Toplevel') as mock_toplevel:
        
        mock_root = Mock()
        mock_tk.return_value = mock_root
        mock_dialog = Mock()
        mock_toplevel.return_value = mock_dialog
        
        launcher = EnhancedLauncher()
        launcher.create_ui()
        
        # Test error dialog creation
        error_info = {
            "title": "Test Error",
            "message": "Test error message with solutions",
            "severity": ErrorSeverity.HIGH
        }
        
        launcher._show_error_dialog(error_info)
        
        # Verify dialog was created
        mock_toplevel.assert_called_with(mock_root)
        mock_dialog.title.assert_called_with("Test Error")
        print("✓ Error dialog with actionable solutions works")

def test_enhanced_keyboard_main_error_handling():
    """Test enhanced error handling in keyboard_main function."""
    from switch_interface.__main__ import keyboard_main
    
    # Test with missing layout file
    try:
        keyboard_main(["--layout", "nonexistent_layout.json"])
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert "not found" in str(e)
        print("✓ Enhanced keyboard_main error handling works")

def test_error_button_visibility():
    """Test that error recovery buttons are shown/hidden appropriately."""
    from switch_interface.launcher import EnhancedLauncher
    from switch_interface.error_handler import ErrorSeverity
    
    with patch('tkinter.Tk') as mock_tk:
        mock_root = Mock()
        mock_tk.return_value = mock_root
        
        launcher = EnhancedLauncher()
        launcher.create_ui()
        
        # Mock buttons
        launcher.retry_button = Mock()
        launcher.safe_mode_button = Mock()
        
        # Test showing error buttons for high severity error
        error_info = {"severity": ErrorSeverity.HIGH}
        launcher._show_error_buttons(error_info)
        
        launcher.retry_button.pack.assert_called()
        launcher.safe_mode_button.pack.assert_called()
        
        # Test hiding error buttons
        launcher._hide_error_buttons()
        
        launcher.retry_button.pack_forget.assert_called()
        launcher.safe_mode_button.pack_forget.assert_called()
        print("✓ Error button visibility works correctly")

def test_status_updates():
    """Test status message updates during operations."""
    from switch_interface.launcher import EnhancedLauncher
    
    with patch('tkinter.Tk') as mock_tk:
        mock_root = Mock()
        mock_tk.return_value = mock_root
        
        launcher = EnhancedLauncher()
        launcher.create_ui()
        
        # Mock status label
        launcher.status_label = Mock()
        
        # Test different status updates
        launcher._update_status("Starting...", "blue")
        launcher.status_label.config.assert_called_with(text="Starting...", fg="blue")
        
        launcher._update_status("Error occurred", "red")
        launcher.status_label.config.assert_called_with(text="Error occurred", fg="red")
        
        launcher._update_status("Success!", "green")
        launcher.status_label.config.assert_called_with(text="Success!", fg="green")
        print("✓ Status updates work correctly")

def main():
    """Run all comprehensive tests."""
    print("Testing Enhanced Launcher Error Recovery Features...")
    print("=" * 60)
    
    try:
        test_launcher_remains_open_on_error()
        test_retry_mechanism()
        test_safe_mode_functionality()
        test_error_dialog_with_actionable_solutions()
        test_enhanced_keyboard_main_error_handling()
        test_error_button_visibility()
        test_status_updates()
        
        print("=" * 60)
        print("✅ All enhanced error recovery features are working correctly!")
        print()
        print("Features implemented:")
        print("• Launcher remains open when errors occur")
        print("• Retry mechanisms for failed operations")
        print("• Graceful error display with actionable solutions")
        print("• Safe mode option for minimal functionality")
        print("• Enhanced error handling in keyboard_main")
        print("• Status updates and visual feedback")
        print("• Error recovery button management")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)