"""Tests for audio device fallback functionality."""
import unittest
from unittest.mock import patch, MagicMock, call

import pytest
import sounddevice as sd

from switch_interface.audio_device_manager import (
    AudioDeviceManager, 
    find_working_device,
    test_device
)
from switch_interface.listener import check_device_with_fallback, listen


class TestAudioDeviceFallback(unittest.TestCase):
    """Test audio device fallback mechanisms."""
    
    @patch('switch_interface.audio_device_manager.open_input')
    def test_device_test_with_modes(self, mock_open_input):
        """Test device testing with different modes."""
        # Setup mock
        mock_cm = MagicMock()
        mock_open_input.return_value = mock_cm
        
        manager = AudioDeviceManager()
        
        # Test exclusive mode
        success, _ = manager.test_device(0, mode="exclusive")
        self.assertTrue(success)
        
        # Test shared mode
        success, _ = manager.test_device(0, mode="shared")
        self.assertTrue(success)
        
        # Test auto mode
        success, _ = manager.test_device(0, mode="auto")
        self.assertTrue(success)
        
        # Verify calls
        self.assertEqual(mock_open_input.call_count, 3)
    
    @patch('switch_interface.audio_device_manager.open_input')
    def test_device_fallback_chain(self, mock_open_input):
        """Test device fallback chain logic."""
        # Setup mock
        mock_cm = MagicMock()
        mock_open_input.return_value = mock_cm
        
        # Mock available devices
        manager = AudioDeviceManager()
        manager.get_available_input_devices = MagicMock(return_value=[
            {"index": 0, "name": "Device 0"},
            {"index": 1, "name": "Device 1"},
            {"index": 2, "name": "Device 2"}
        ])
        
        # Test fallback chain with preferred device
        chain = manager.get_device_fallback_chain(1)
        self.assertEqual(chain[0], 1)  # Preferred device first
        self.assertIn(None, chain)     # System default included
        self.assertIn(0, chain)        # Other devices included
        self.assertIn(2, chain)        # Other devices included
        
        # Test with last working device
        manager.last_working_device = 2
        chain = manager.get_device_fallback_chain(1)
        self.assertEqual(chain[0], 1)  # Preferred device first
        self.assertEqual(chain[1], 2)  # Last working device second
    
    @patch('switch_interface.audio_device_manager.open_input')
    def test_find_working_device_with_fallback(self, mock_open_input):
        """Test finding working device with fallback logic."""
        manager = AudioDeviceManager()
        
        # Mock device testing to fail for device 0 but succeed for device 1
        original_test_device = manager.test_device
        
        def mock_test_device(device, samplerate=44100, blocksize=256, timeout=2.0, mode="auto"):
            if device == 0:
                return False, "Test error"
            elif device == 1:
                return True, None
            else:
                return False, "Unknown device"
        
        manager.test_device = mock_test_device
        manager.get_available_input_devices = MagicMock(return_value=[
            {"index": 0, "name": "Device 0"},
            {"index": 1, "name": "Device 1"}
        ])
        
        # Test fallback from device 0 to device 1
        device, error, mode = manager.find_working_device(0)
        self.assertEqual(device, 1)
        self.assertIsNone(error)
        
        # Restore original method
        manager.test_device = original_test_device
    
    @patch('switch_interface.audio_device_manager.open_input')
    def test_exclusive_to_shared_fallback(self, mock_open_input):
        """Test fallback from exclusive to shared mode."""
        # Setup mocks to fail in exclusive mode but succeed in shared mode
        def mock_open_input_side_effect(*args, **kwargs):
            if 'extra_settings' in kwargs:
                # Exclusive mode fails
                raise sd.PortAudioError("Exclusive mode error")
            # Shared mode succeeds
            mock_cm = MagicMock()
            return mock_cm
        
        mock_open_input.side_effect = mock_open_input_side_effect
        
        manager = AudioDeviceManager()
        
        # Test fallback from exclusive to shared
        device, error, mode = manager.find_working_device(0, preferred_mode="exclusive")
        
        # Should succeed with shared mode
        self.assertEqual(device, 0)
        self.assertEqual(mode, "shared")
        self.assertIsNone(error)
    
    @patch('switch_interface.listener.open_input')
    def test_listen_with_fallback(self, mock_open_input):
        """Test listen function with device fallback."""
        # Setup mock to fail first then succeed
        mock_cm = MagicMock()
        
        def mock_open_input_side_effect(*args, **kwargs):
            if mock_open_input.call_count == 1:
                raise sd.PortAudioError("First attempt fails")
            return mock_cm
        
        mock_open_input.side_effect = mock_open_input_side_effect
        
        # Mock time.sleep to avoid blocking
        with patch('switch_interface.listener.time.sleep', side_effect=KeyboardInterrupt):
            # Should not raise exception due to fallback
            with pytest.raises(KeyboardInterrupt):
                listen(lambda: None, device=0, enable_fallback=True)
            
            # Should have tried twice
            self.assertEqual(mock_open_input.call_count, 2)


if __name__ == '__main__':
    unittest.main()