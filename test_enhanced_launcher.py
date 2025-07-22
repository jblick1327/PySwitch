#!/usr/bin/env python3
"""Test script to verify enhanced launcher error recovery functionality."""

import os
import sys
import tkinter as tk
from unittest.mock import Mock, patch
import tempfile

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_enhanced_launcher_creation():
    """Test that the enhanced launcher can be created."""
    from switch_interface.launcher import EnhancedLauncher
    
    # Mock tkinter to avoid GUI creation during test
    with patch('tkinter.Tk') as mock_tk:
        mock_root = Mock()
        mock_tk.return_value = mock_root
        
        launcher = EnhancedLauncher()
        assert launcher is not None
        print("✓ Enhanced launcher can be created")

def test_error_handling_integration():
    """Test that error handler integration works."""
    from switch_interface.launcher import EnhancedLauncher
    from switch_interface.error_handler import error_handler
    
    # Test error categorization
    test_error = RuntimeError("Audio device not found")
    error_info = error_handler.handle_error(test_error, "test_context")
    
    assert "title" in error_info
    assert "message" in error_info
    assert "category" in error_info
    assert "severity" in error_info
    print("✓ Error handler integration works")

def test_safe_mode_layout_selection():
    """Test safe mode layout selection logic."""
    from switch_interface.launcher import EnhancedLauncher
    from pathlib import Path
    
    with patch('switch_interface.launcher.list_layouts') as mock_list:
        # Mock available layouts
        mock_layouts = [
            Path("simple_alphabet.json"),
            Path("basic_test.json"),
            Path("complex_layout.json")
        ]
        mock_list.return_value = mock_layouts
        
        with patch('switch_interface.launcher.resources') as mock_resources:
            mock_resources.files.return_value.joinpath.return_value = Path("simple_alphabet.json")
            
            launcher = EnhancedLauncher()
            safe_layout = launcher._get_safe_layout()
            
            # Should prefer simple_alphabet.json for safe mode
            assert "simple_alphabet.json" in str(safe_layout)
            print("✓ Safe mode layout selection works")

def test_status_update_functionality():
    """Test status update functionality."""
    from switch_interface.launcher import EnhancedLauncher
    
    with patch('tkinter.Tk'), patch('tkinter.Label') as mock_label:
        mock_status_label = Mock()
        mock_label.return_value = mock_status_label
        
        launcher = EnhancedLauncher()
        launcher.status_label = mock_status_label
        
        launcher._update_status("Test message", "red")
        mock_status_label.config.assert_called_with(text="Test message", fg="red")
        print("✓ Status update functionality works")

def main():
    """Run all tests."""
    print("Testing Enhanced Launcher Error Recovery...")
    print()
    
    try:
        test_enhanced_launcher_creation()
        test_error_handling_integration()
        test_safe_mode_layout_selection()
        test_status_update_functionality()
        
        print()
        print("✅ All tests passed! Enhanced launcher error recovery is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)