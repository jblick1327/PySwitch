#!/usr/bin/env python3
"""
Test script for enhanced setup wizard functionality.
Tests the skip calibration feature and improved error handling.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tkinter as tk
from switch_interface.gui import FirstRunWizard


class TestSetupWizardEnhancements(unittest.TestCase):
    """Test the enhanced setup wizard functionality."""

    def setUp(self):
        """Set up test environment."""
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the window during tests

    def tearDown(self):
        """Clean up test environment."""
        self.root.destroy()

    @patch('switch_interface.gui.sd.query_devices')
    def test_skip_calibration_functionality(self, mock_query_devices):
        """Test that skip calibration creates appropriate default settings."""
        # Mock audio devices
        mock_query_devices.return_value = [
            {"name": "Test Microphone", "max_input_channels": 1}
        ]
        
        wizard = FirstRunWizard(self.root)
        
        # Simulate device selection
        wizard.device_var.set("0: Test Microphone")
        wizard._device_map = {"0: Test Microphone": 0}
        
        # Test skip calibration
        wizard._skip_calibration()
        
        # Verify default calibration data is set
        self.assertIsNotNone(wizard.calib_data)
        self.assertEqual(wizard.calib_data["upper_offset"], -0.2)
        self.assertEqual(wizard.calib_data["lower_offset"], -0.5)
        self.assertEqual(wizard.calib_data["samplerate"], 44100)
        self.assertEqual(wizard.calib_data["blocksize"], 256)
        self.assertEqual(wizard.calib_data["debounce_ms"], 50)
        self.assertEqual(wizard.calib_data["device"], 0)
        
        # Verify status message is set
        self.assertIn("default calibration settings", wizard.status_var.get())
        
        wizard.destroy()

    @patch('switch_interface.gui.sd.query_devices')
    def test_no_devices_detected_guidance(self, mock_query_devices):
        """Test that appropriate guidance is shown when no devices are detected."""
        # Mock no audio devices
        mock_query_devices.return_value = []
        
        wizard = FirstRunWizard(self.root)
        
        # Check that device map is empty
        self.assertEqual(wizard._device_map, {})
        
        # Check that device variable is set to empty
        self.assertEqual(wizard.device_var.get(), "")
        
        wizard.destroy()

    @patch('switch_interface.gui.sd.query_devices')
    def test_refresh_devices_functionality(self, mock_query_devices):
        """Test that device refresh works correctly."""
        # Initially no devices
        mock_query_devices.return_value = []
        
        wizard = FirstRunWizard(self.root)
        initial_device_count = len(wizard._device_map)
        
        # Now mock devices being available
        mock_query_devices.return_value = [
            {"name": "New Microphone", "max_input_channels": 1}
        ]
        
        # Refresh devices
        wizard._refresh_devices()
        
        # Check that device map is updated
        self.assertGreater(len(wizard._device_map), initial_device_count)
        
        wizard.destroy()

    @patch('switch_interface.gui.sd.query_devices')
    def test_calibration_error_handling(self, mock_query_devices):
        """Test that calibration errors are handled gracefully."""
        # Mock audio devices
        mock_query_devices.return_value = [
            {"name": "Test Microphone", "max_input_channels": 1}
        ]
        
        wizard = FirstRunWizard(self.root)
        wizard.device_var.set("0: Test Microphone")
        wizard._device_map = {"0: Test Microphone": 0}
        
        # Simulate calibration failure
        wizard._finish_calibration("Error: No Default Input Device")
        
        # Verify that calib_data is None (indicating failure)
        self.assertIsNone(wizard.calib_data)
        
        # Verify error message is displayed
        self.assertIn("Error:", wizard.status_var.get())
        
        wizard.destroy()

    @patch('switch_interface.gui.sd.query_devices')
    def test_progress_indicator_display(self, mock_query_devices):
        """Test that progress indicators are displayed correctly."""
        # Mock audio devices
        mock_query_devices.return_value = [
            {"name": "Test Microphone", "max_input_channels": 1}
        ]
        
        wizard = FirstRunWizard(self.root)
        
        # Test that current step is tracked
        self.assertEqual(wizard.current, 0)
        
        # Move to next step
        wizard._show_step(1)
        self.assertEqual(wizard.current, 1)
        
        wizard.destroy()


if __name__ == "__main__":
    # Run the tests
    unittest.main()