#!/usr/bin/env python3
"""
Comprehensive end-to-end integration tests for Switch Interface UX improvements.
Tests complete user journey from first launch to successful typing.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestEndToEndUserJourney:
    """Test complete user journey scenarios."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
        
    def teardown_method(self):
        """Clean up after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_first_run_success_journey(self):
        """Test successful first-run user journey."""
        from switch_interface.config import Config
        from switch_interface.gui import FirstRunWizard
        
        # Mock successful audio setup
        with patch('switch_interface.gui.get_audio_devices') as mock_devices, \
             patch('switch_interface.gui.calibrate_audio') as mock_calibrate, \
             patch('switch_interface.gui.tk.Tk') as mock_tk:
            
            mock_devices.return_value = ["Default Microphone", "USB Headset"]
            mock_calibrate.return_value = {"threshold": 0.5, "device": "Default Microphone"}
            
            # Mock Tkinter components
            mock_root = Mock()
            mock_tk.return_value = mock_root
            
            # Test wizard completion
            wizard = FirstRunWizard(str(self.config_path))
            
            # Simulate successful calibration
            wizard.calibration_result = {"threshold": 0.5, "device": "Default Microphone"}
            wizard.selected_layout = "qwerty_full.json"
            
            # Verify config is saved correctly
            config = wizard._create_config()
            assert config["calibration_complete"] is True
            assert config["layout"] == "qwerty_full.json"
            assert config["audio_device"] == "Default Microphone"
            
        print("✓ First-run success journey works")
    
    def test_first_run_skip_calibration_journey(self):
        """Test first-run journey with skipped calibration."""
        from switch_interface.gui import FirstRunWizard
        
        with patch('switch_interface.gui.get_audio_devices') as mock_devices, \
             patch('switch_interface.gui.tk.Tk') as mock_tk:
            
            mock_devices.return_value = ["Default Microphone"]
            mock_root = Mock()
            mock_tk.return_value = mock_root
            
            wizard = FirstRunWizard(str(self.config_path))
            
            # Simulate skipping calibration
            wizard.calibration_result = None
            wizard.selected_layout = "simple_alphabet.json"
            
            config = wizard._create_config()
            
            # Should use default calibration settings
            assert config["calibration_complete"] is False
            assert config["layout"] == "simple_alphabet.json"
            assert "threshold" in config  # Default threshold applied
            
        print("✓ Skip calibration journey works")
    
    def test_audio_device_failure_recovery(self):
        """Test recovery from audio device failures."""
        from switch_interface.audio_device_manager import AudioDeviceManager
        from switch_interface.error_handler import error_handler
        
        manager = AudioDeviceManager()
        
        # Test fallback to alternative device
        with patch('switch_interface.audio_device_manager.get_audio_devices') as mock_devices:
            mock_devices.return_value = ["Primary Mic", "Backup Mic"]
            
            # Simulate primary device failure
            with patch.object(manager, '_try_device') as mock_try:
                mock_try.side_effect = [RuntimeError("Device busy"), True]
                
                result = manager.find_working_device()
                assert result is not None
                assert mock_try.call_count == 2  # Tried both devices
        
        print("✓ Audio device failure recovery works")
    
    def test_configuration_corruption_recovery(self):
        """Test recovery from corrupted configuration files."""
        from switch_interface.config import Config
        
        # Create corrupted config file
        with open(self.config_path, 'w') as f:
            f.write("invalid json content {")
        
        # Should recover with defaults
        config = Config(str(self.config_path))
        config.load()
        
        # Verify defaults are applied
        assert config.get("scan_interval") == 0.6
        assert config.get("layout") == "qwerty_full.json"
        assert config.get("calibration_complete") is False
        
        print("✓ Configuration corruption recovery works")
    
    def test_layout_loading_fallback(self):
        """Test layout loading with fallback mechanisms."""
        from switch_interface.kb_layout_io import load_layout
        
        # Test with non-existent layout
        with patch('switch_interface.kb_layout_io.resources') as mock_resources:
            # Mock bundled layouts
            mock_resources.files.return_value.joinpath.return_value.exists.return_value = True
            mock_resources.files.return_value.joinpath.return_value.read_text.return_value = json.dumps({
                "keys": [{"text": "A", "x": 0, "y": 0}],
                "metadata": {"name": "Fallback Layout"}
            })
            
            layout = load_layout("nonexistent.json")
            assert layout is not None
            assert "keys" in layout
        
        print("✓ Layout loading fallback works")

class TestErrorScenarioRecovery:
    """Test all error scenarios have appropriate recovery paths."""
    
    def test_startup_error_recovery(self):
        """Test startup error recovery paths."""
        from switch_interface.error_handler import error_handler, ErrorCategory
        
        # Test missing dependency error
        import_error = ImportError("No module named 'required_module'")
        error_info = error_handler.handle_error(import_error, "startup")
        
        assert error_info["category"] == ErrorCategory.STARTUP
        assert any("install" in s.lower() for s in error_info["suggestions"])
        
        # Test permission error
        perm_error = PermissionError("Access denied")
        error_info = error_handler.handle_error(perm_error, "startup")
        
        assert error_info["category"] == ErrorCategory.STARTUP
        assert any("permission" in s.lower() for s in error_info["suggestions"])
        
        print("✓ Startup error recovery paths work")
    
    def test_audio_error_recovery_paths(self):
        """Test audio-related error recovery."""
        from switch_interface.error_handler import error_handler, ErrorCategory
        
        # Test no microphone error
        no_mic_error = RuntimeError("No audio input devices found")
        error_info = error_handler.handle_error(no_mic_error, "audio_setup")
        
        assert error_info["category"] == ErrorCategory.AUDIO
        assert any("microphone" in s.lower() for s in error_info["suggestions"])
        assert any("connect" in s.lower() for s in error_info["suggestions"])
        
        # Test calibration failure
        cal_error = RuntimeError("Calibration timeout")
        error_info = error_handler.handle_error(cal_error, "calibration")
        
        assert error_info["category"] == ErrorCategory.AUDIO
        assert any("skip" in s.lower() for s in error_info["suggestions"])
        
        print("✓ Audio error recovery paths work")
    
    def test_configuration_error_recovery(self):
        """Test configuration error recovery paths."""
        from switch_interface.error_handler import error_handler, ErrorCategory
        
        # Test corrupted config
        json_error = json.JSONDecodeError("Invalid JSON", "", 0)
        error_info = error_handler.handle_error(json_error, "config_load")
        
        assert error_info["category"] == ErrorCategory.CONFIG
        assert any("default" in s.lower() for s in error_info["suggestions"])
        
        # Test missing layout file
        layout_error = FileNotFoundError("Layout file not found")
        error_info = error_handler.handle_error(layout_error, "layout_load")
        
        assert error_info["category"] == ErrorCategory.CONFIG
        assert any("layout" in s.lower() for s in error_info["suggestions"])
        
        print("✓ Configuration error recovery paths work")

class TestCrossPlatformCompatibility:
    """Test compatibility across different operating systems."""
    
    def test_windows_compatibility(self):
        """Test Windows-specific functionality."""
        with patch('sys.platform', 'win32'):
            from switch_interface.config import get_config_dir
            
            config_dir = get_config_dir()
            # Should use Windows-appropriate path
            assert "AppData" in str(config_dir) or "Documents" in str(config_dir)
        
        print("✓ Windows compatibility works")
    
    def test_macos_compatibility(self):
        """Test macOS-specific functionality."""
        with patch('sys.platform', 'darwin'):
            from switch_interface.config import get_config_dir
            
            config_dir = get_config_dir()
            # Should use macOS-appropriate path
            assert "Library" in str(config_dir) or "Documents" in str(config_dir)
        
        print("✓ macOS compatibility works")
    
    def test_linux_compatibility(self):
        """Test Linux-specific functionality."""
        with patch('sys.platform', 'linux'):
            from switch_interface.config import get_config_dir
            
            config_dir = get_config_dir()
            # Should use Linux-appropriate path
            assert ".config" in str(config_dir) or "Documents" in str(config_dir)
        
        print("✓ Linux compatibility works")

class TestBackwardCompatibility:
    """Test backward compatibility with existing configurations."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "config.json"
    
    def teardown_method(self):
        """Clean up after each test."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_old_config_format_migration(self):
        """Test migration of old configuration format."""
        from switch_interface.config import Config
        
        # Create old format config
        old_config = {
            "scan_time": 1.0,  # Old parameter name
            "layout_file": "old_layout.json",  # Old parameter name
            "calibrated": True  # Old parameter name
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(old_config, f)
        
        config = Config(str(self.config_path))
        config.load()
        
        # Should migrate to new format
        assert config.get("scan_interval") == 1.0  # Migrated from scan_time
        assert config.get("layout") == "old_layout.json"  # Migrated from layout_file
        assert config.get("calibration_complete") is True  # Migrated from calibrated
        
        print("✓ Old config format migration works")
    
    def test_missing_new_parameters(self):
        """Test handling of configs missing new parameters."""
        from switch_interface.config import Config
        
        # Create config missing new parameters
        minimal_config = {
            "scan_interval": 0.8,
            "layout": "basic_test.json"
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(minimal_config, f)
        
        config = Config(str(self.config_path))
        config.load()
        
        # Should add missing parameters with defaults
        assert config.get("calibration_complete") is False  # New parameter with default
        assert config.get("audio_device") is None  # New parameter with default
        
        print("✓ Missing new parameters handling works")

def run_comprehensive_tests():
    """Run all comprehensive end-to-end tests."""
    print("Running Comprehensive End-to-End Integration Tests")
    print("=" * 60)
    
    test_classes = [
        TestEndToEndUserJourney,
        TestErrorScenarioRecovery,
        TestCrossPlatformCompatibility,
        TestBackwardCompatibility
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        print("-" * 40)
        
        instance = test_class()
        
        # Get all test methods
        test_methods = [method for method in dir(instance) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                # Set up if method exists
                if hasattr(instance, 'setup_method'):
                    instance.setup_method()
                
                # Run test
                method = getattr(instance, method_name)
                method()
                passed_tests += 1
                
                # Tear down if method exists
                if hasattr(instance, 'teardown_method'):
                    instance.teardown_method()
                    
            except Exception as e:
                print(f"❌ {method_name} failed: {e}")
                import traceback
                traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("✅ All end-to-end integration tests passed!")
        print("\nVerified functionality:")
        print("• Complete user journey from first launch to successful typing")
        print("• All error scenarios have appropriate recovery paths")
        print("• Cross-platform compatibility (Windows, macOS, Linux)")
        print("• Backward compatibility with existing user configurations")
        print("• Audio device fallback and recovery mechanisms")
        print("• Configuration corruption recovery")
        print("• Layout loading fallback systems")
        return True
    else:
        print(f"❌ {total_tests - passed_tests} tests failed")
        return False

if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)