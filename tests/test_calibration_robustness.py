"""Tests for enhanced calibration robustness."""
import unittest
from unittest.mock import patch, MagicMock, call
import tkinter as tk
import threading
import time

import pytest
import numpy as np
import sounddevice as sd

from switch_interface.calibration import (
    DetectorConfig,
    run_auto_calibration,
    validate_calibration,
    calibrate
)


class TestCalibrationRobustness(unittest.TestCase):
    """Test enhanced calibration robustness features."""
    
    @patch('switch_interface.calibration.sd.rec')
    @patch('switch_interface.calibration.sd.wait')
    def test_auto_calibration_timeout(self, mock_wait, mock_rec):
        """Test auto calibration with timeout handling."""
        # Setup mock to simulate timeout
        def wait_timeout():
            time.sleep(10)  # This will trigger timeout
        
        mock_wait.side_effect = wait_timeout
        mock_rec.return_value = np.zeros((44100 * 3, 1), dtype=np.float32)
        
        # Test with short timeout
        with pytest.raises(TimeoutError):
            run_auto_calibration(device_id=None, timeout_seconds=0.1)
    
    @patch('switch_interface.calibration.sd.rec')
    @patch('switch_interface.calibration.sd.wait')
    @patch('switch_interface.calibration.calibrate')
    def test_auto_calibration_retry(self, mock_calibrate, mock_wait, mock_rec):
        """Test auto calibration with retry mechanism."""
        # Setup mocks
        mock_rec.return_value = np.zeros((44100 * 3, 1), dtype=np.float32)
        
        # First attempt fails, second succeeds
        mock_result1 = MagicMock()
        mock_result1.upper_offset = -0.2
        mock_result1.lower_offset = -0.5
        mock_result1.debounce_ms = 40
        mock_result1.calib_ok = False
        
        mock_result2 = MagicMock()
        mock_result2.upper_offset = -0.2
        mock_result2.lower_offset = -0.5
        mock_result2.debounce_ms = 40
        mock_result2.calib_ok = True
        
        mock_calibrate.side_effect = [mock_result1, mock_result2]
        
        # Should succeed on second attempt
        result = run_auto_calibration(device_id=None, max_attempts=2)
        
        # Verify calibrate was called twice
        self.assertEqual(mock_calibrate.call_count, 2)
        self.assertTrue(result.get("calib_ok", False))
    
    def test_validate_calibration(self):
        """Test calibration validation."""
        # Valid configuration
        valid_config = DetectorConfig(
            upper_offset=-0.2,
            lower_offset=-0.5,
            samplerate=44100,
            blocksize=256,
            debounce_ms=40,
            device=None
        )
        self.assertTrue(validate_calibration(valid_config))
        
        # Invalid upper/lower relationship
        invalid_config1 = DetectorConfig(
            upper_offset=-0.5,  # Upper should be higher (less negative) than lower
            lower_offset=-0.2,
            samplerate=44100,
            blocksize=256,
            debounce_ms=40,
            device=None
        )
        self.assertFalse(validate_calibration(invalid_config1))
        
        # Invalid positive threshold
        invalid_config2 = DetectorConfig(
            upper_offset=0.2,  # Should be negative
            lower_offset=-0.5,
            samplerate=44100,
            blocksize=256,
            debounce_ms=40,
            device=None
        )
        self.assertFalse(validate_calibration(invalid_config2))
        
        # Invalid sample rate
        invalid_config3 = DetectorConfig(
            upper_offset=-0.2,
            lower_offset=-0.5,
            samplerate=12345,  # Not a standard rate
            blocksize=256,
            debounce_ms=40,
            device=None
        )
        self.assertFalse(validate_calibration(invalid_config3))
        
        # Invalid debounce time
        invalid_config4 = DetectorConfig(
            upper_offset=-0.2,
            lower_offset=-0.5,
            samplerate=44100,
            blocksize=256,
            debounce_ms=5,  # Too low
            device=None
        )
        self.assertFalse(validate_calibration(invalid_config4))
    
    @patch('switch_interface.calibration.open_input')
    @patch('tkinter.Toplevel')
    @patch('tkinter.messagebox.askretrycancel')
    def test_calibration_with_retry(self, mock_askretrycancel, mock_toplevel, mock_open_input):
        """Test calibration with retry mechanism."""
        # Setup mocks
        mock_root = MagicMock()
        mock_toplevel.return_value = mock_root
        
        # First attempt fails, retry is selected
        mock_askretrycancel.return_value = True
        
        # First open_input fails, second succeeds
        mock_cm1 = MagicMock()
        mock_cm1.__enter__.side_effect = sd.PortAudioError("Test error")
        
        mock_cm2 = MagicMock()
        mock_stream = MagicMock()
        mock_cm2.__enter__.return_value = mock_stream
        
        mock_open_input.side_effect = [mock_cm1, mock_cm2]
        
        # Mock AudioDeviceManager.find_working_device
        with patch('switch_interface.audio_device_manager.AudioDeviceManager.find_working_device') as mock_find:
            mock_find.return_value = (1, None, "auto")  # Return a working device
            
            # Run calibration with parent window
            parent = MagicMock()
            on_complete = MagicMock()
            
            # Need to simulate early exit since we can't run the full UI
            with patch('switch_interface.calibration.validate_calibration', return_value=True):
                with patch.object(mock_root, 'mainloop', side_effect=SystemExit):
                    try:
                        calibrate(parent=parent, on_complete=on_complete)
                    except SystemExit:
                        pass
            
            # Verify retry was attempted
            self.assertTrue(mock_askretrycancel.called)
            self.assertTrue(mock_find.called)


if __name__ == '__main__':
    unittest.main()