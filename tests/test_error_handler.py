"""Tests for the centralized error handler."""

import pytest
import sounddevice as sd
from unittest.mock import Mock, patch

from switch_interface.error_handler import (
    ErrorHandler, ErrorCategory, ErrorSeverity, error_handler
)


class TestErrorHandler:
    """Test the ErrorHandler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = ErrorHandler()
    
    def test_categorize_audio_errors(self):
        """Test categorization of audio-related errors."""
        # PortAudioError
        audio_error = sd.PortAudioError("Device not found")
        assert self.handler.categorize_error(audio_error) == ErrorCategory.AUDIO
        
        # OSError with audio context
        os_error = OSError("Audio device unavailable")
        assert self.handler.categorize_error(os_error) == ErrorCategory.AUDIO
        
        # Generic error with audio keywords
        generic_error = RuntimeError("microphone access failed")
        assert self.handler.categorize_error(generic_error) == ErrorCategory.AUDIO
        
        device_error = Exception("sounddevice initialization error")
        assert self.handler.categorize_error(device_error) == ErrorCategory.AUDIO
    
    def test_categorize_config_errors(self):
        """Test categorization of configuration errors."""
        # FileNotFoundError with config context
        config_error = FileNotFoundError("config.json not found")
        assert self.handler.categorize_error(config_error) == ErrorCategory.CONFIG
        
        # PermissionError with config context
        perm_error = PermissionError("Cannot write to config.json")
        assert self.handler.categorize_error(perm_error) == ErrorCategory.CONFIG
    
    def test_categorize_layout_errors(self):
        """Test categorization of layout errors."""
        layout_error = Exception("keyboard layout not found")
        assert self.handler.categorize_error(layout_error) == ErrorCategory.LAYOUT
        
        json_error = Exception("Invalid JSON in layout file")
        assert self.handler.categorize_error(json_error) == ErrorCategory.LAYOUT
    
    def test_categorize_startup_errors(self):
        """Test categorization of startup errors."""
        import_error = ImportError("No module named 'required_module'")
        assert self.handler.categorize_error(import_error) == ErrorCategory.STARTUP
        
        module_error = ModuleNotFoundError("Module not found")
        assert self.handler.categorize_error(module_error) == ErrorCategory.STARTUP
        
        startup_error = Exception("startup failed")
        assert self.handler.categorize_error(startup_error) == ErrorCategory.STARTUP
    
    def test_categorize_calibration_errors(self):
        """Test categorization of calibration errors."""
        calib_error = Exception("calibration failed")
        assert self.handler.categorize_error(calib_error) == ErrorCategory.CALIBRATION
        
        detector_error = Exception("detector threshold error")
        assert self.handler.categorize_error(detector_error) == ErrorCategory.CALIBRATION
    
    def test_categorize_hardware_errors(self):
        """Test categorization of hardware errors."""
        hw_error = Exception("hardware connection failed")
        assert self.handler.categorize_error(hw_error) == ErrorCategory.HARDWARE
        
        usb_error = Exception("USB connection failed")
        assert self.handler.categorize_error(usb_error) == ErrorCategory.HARDWARE
    
    def test_categorize_unknown_errors(self):
        """Test categorization of unknown errors."""
        unknown_error = Exception("Something went wrong")
        assert self.handler.categorize_error(unknown_error) == ErrorCategory.UNKNOWN
    
    def test_get_severity(self):
        """Test error severity determination."""
        # Startup errors are critical
        startup_error = ImportError("Module not found")
        assert self.handler.get_severity(startup_error, ErrorCategory.STARTUP) == ErrorSeverity.CRITICAL
        
        # Audio errors are high severity
        audio_error = sd.PortAudioError("Device not found")
        assert self.handler.get_severity(audio_error, ErrorCategory.AUDIO) == ErrorSeverity.HIGH
        
        # Config errors are medium severity
        config_error = FileNotFoundError("config.json")
        assert self.handler.get_severity(config_error, ErrorCategory.CONFIG) == ErrorSeverity.MEDIUM
        
        # Hardware errors are high severity
        hw_error = Exception("hardware failure")
        assert self.handler.get_severity(hw_error, ErrorCategory.HARDWARE) == ErrorSeverity.HIGH
        
        # Unknown errors are medium severity
        unknown_error = Exception("unknown")
        assert self.handler.get_severity(unknown_error, ErrorCategory.UNKNOWN) == ErrorSeverity.MEDIUM
    
    def test_audio_error_messages(self):
        """Test audio error message generation."""
        # Device not found error
        device_error = sd.PortAudioError("No device found")
        title, message = self.handler._handle_audio_error(device_error)
        
        assert title == "Audio Device Error"
        assert "microphone or audio input device" in message
        assert "Connect a microphone" in message
        assert "Calibrate" in message
        
        # Exclusive access error
        access_error = sd.PortAudioError("Exclusive access denied")
        title, message = self.handler._handle_audio_error(access_error)
        
        assert title == "Audio Device Error"
        assert "exclusive access" in message
        assert "Close other applications" in message
        assert "shared mode" in message
        
        # Permission error
        perm_error = OSError("Permission denied for microphone")
        title, message = self.handler._handle_audio_error(perm_error)
        
        assert title == "Audio Device Error"
        assert "Permission denied" in message
        assert "Privacy settings" in message
        assert "administrator" in message
    
    def test_config_error_messages(self):
        """Test configuration error message generation."""
        # Permission error
        perm_error = PermissionError("Cannot write config")
        title, message = self.handler._handle_config_error(perm_error)
        
        assert title == "Configuration Error"
        assert "Could not save or load configuration" in message
        assert "administrator" in message
        
        # JSON decode error
        json_error = Exception("JSON decode error in config")
        title, message = self.handler._handle_config_error(json_error)
        
        assert title == "Configuration Error"
        assert "corrupted" in message
        assert "default settings" in message
    
    def test_startup_error_messages(self):
        """Test startup error message generation."""
        # Import error
        import_error = ImportError("No module named 'test'")
        title, message = self.handler._handle_startup_error(import_error)
        
        assert title == "Startup Error"
        assert "required component" in message
        assert "Reinstall" in message
        
        # Permission error
        perm_error = PermissionError("Access denied")
        title, message = self.handler._handle_startup_error(perm_error)
        
        assert title == "Startup Error"
        assert "does not have permission" in message
        assert "administrator" in message
    
    def test_layout_error_messages(self):
        """Test layout error message generation."""
        # File not found
        not_found_error = FileNotFoundError("Layout not found")
        title, message = self.handler._handle_layout_error(not_found_error)
        
        assert title == "Keyboard Layout Error"
        assert "could not be found" in message
        assert "default layout" in message
        
        # JSON error
        json_error = Exception("JSON decode error in layout")
        title, message = self.handler._handle_layout_error(json_error)
        
        assert title == "Keyboard Layout Error"
        assert "corrupted" in message
        assert "default layout" in message
    
    def test_calibration_error_messages(self):
        """Test calibration error message generation."""
        calib_error = Exception("Calibration failed")
        title, message = self.handler._handle_calibration_error(calib_error)
        
        assert title == "Calibration Error"
        assert "Skip Calibration" in message
        assert "default settings" in message
        assert "microphone is working" in message
    
    def test_hardware_error_messages(self):
        """Test hardware error message generation."""
        hw_error = Exception("Hardware connection failed")
        title, message = self.handler._handle_hardware_error(hw_error)
        
        assert title == "Hardware Error"
        assert "hardware setup" in message
        assert "cable connections" in message
        assert "USB ports" in message
    
    def test_unknown_error_messages(self):
        """Test unknown error message generation."""
        unknown_error = Exception("Something unexpected")
        title, message = self.handler._handle_unknown_error(unknown_error)
        
        assert title == "Unexpected Error"
        assert "unexpected error" in message
        assert "Restart the application" in message
        assert "Technical details" in message
    
    def test_handle_error_logging(self):
        """Test that errors are logged appropriately."""
        # Test critical error logging
        critical_error = ImportError("Critical failure")
        result = self.handler.handle_error(critical_error, "startup")
        
        assert result["severity"] == ErrorSeverity.CRITICAL
        assert result["context"] == "startup"
        
        # Test high severity error logging
        high_error = sd.PortAudioError("Audio failure")
        result = self.handler.handle_error(high_error, "audio_init")
        
        assert result["severity"] == ErrorSeverity.HIGH
    
    def test_handle_error_structure(self):
        """Test the structure of the error handling result."""
        error = Exception("Test error")
        result = self.handler.handle_error(error, "test_context")
        
        # Check all required keys are present
        required_keys = [
            "title", "message", "category", "severity", 
            "technical_details", "context", "suggestions"
        ]
        for key in required_keys:
            assert key in result
        
        assert result["context"] == "test_context"
        assert result["technical_details"] == "Test error"
        assert isinstance(result["suggestions"], list)
        assert len(result["suggestions"]) > 0
    
    def test_recovery_suggestions(self):
        """Test recovery suggestions for different error categories."""
        # Audio error suggestions
        suggestions = self.handler._get_recovery_suggestions(ErrorCategory.AUDIO, ErrorSeverity.HIGH)
        assert "Core functionality may be affected" in suggestions
        assert "Try the 'Calibrate' button to select your microphone" in suggestions
        
        # Config error suggestions
        suggestions = self.handler._get_recovery_suggestions(ErrorCategory.CONFIG, ErrorSeverity.MEDIUM)
        assert "Application will use default settings" in suggestions
        
        # Startup error suggestions
        suggestions = self.handler._get_recovery_suggestions(ErrorCategory.STARTUP, ErrorSeverity.CRITICAL)
        assert "Application cannot continue normally" in suggestions
        assert "Restart the application" in suggestions
    
    def test_can_continue(self):
        """Test whether application can continue after errors."""
        # Critical errors should not allow continuation
        assert not self.handler.can_continue(ErrorCategory.STARTUP, ErrorSeverity.CRITICAL)
        
        # High severity startup errors should not allow continuation
        assert not self.handler.can_continue(ErrorCategory.STARTUP, ErrorSeverity.HIGH)
        
        # Other high severity errors should allow continuation
        assert self.handler.can_continue(ErrorCategory.AUDIO, ErrorSeverity.HIGH)
        
        # Medium and low severity errors should allow continuation
        assert self.handler.can_continue(ErrorCategory.CONFIG, ErrorSeverity.MEDIUM)
        assert self.handler.can_continue(ErrorCategory.LAYOUT, ErrorSeverity.LOW)
    
    def test_suggest_safe_mode(self):
        """Test safe mode suggestions."""
        # High severity audio errors should suggest safe mode
        assert self.handler.suggest_safe_mode(ErrorCategory.AUDIO, ErrorSeverity.HIGH)
        
        # Critical hardware errors should suggest safe mode
        assert self.handler.suggest_safe_mode(ErrorCategory.HARDWARE, ErrorSeverity.CRITICAL)
        
        # Medium severity config errors should not suggest safe mode
        assert not self.handler.suggest_safe_mode(ErrorCategory.CONFIG, ErrorSeverity.MEDIUM)
        
        # Low severity errors should not suggest safe mode
        assert not self.handler.suggest_safe_mode(ErrorCategory.AUDIO, ErrorSeverity.LOW)
    
    def test_global_error_handler_instance(self):
        """Test that the global error handler instance is available."""
        assert error_handler is not None
        assert isinstance(error_handler, ErrorHandler)


class TestErrorIntegration:
    """Integration tests for error handling."""
    
    def test_real_audio_error_handling(self):
        """Test handling of real audio errors."""
        handler = ErrorHandler()
        
        # Simulate a real PortAudioError
        try:
            # This should fail with a PortAudioError
            sd.check_input_settings(device="nonexistent_device_12345")
        except Exception as e:
            result = handler.handle_error(e, "audio_test")
            
            assert result["category"] == ErrorCategory.AUDIO
            assert result["severity"] == ErrorSeverity.HIGH
            assert "Audio Device Error" in result["title"]
            assert len(result["suggestions"]) > 0
    
    def test_real_file_error_handling(self):
        """Test handling of real file errors."""
        handler = ErrorHandler()
        
        try:
            with open("nonexistent_config.json", "r") as f:
                f.read()
        except FileNotFoundError as e:
            result = handler.handle_error(e, "config_load")
            
            assert result["category"] == ErrorCategory.CONFIG
            assert result["severity"] == ErrorSeverity.MEDIUM
            assert "Configuration Error" in result["title"]
    
    def test_real_import_error_handling(self):
        """Test handling of real import errors."""
        handler = ErrorHandler()
        
        try:
            import nonexistent_module_12345
        except ImportError as e:
            result = handler.handle_error(e, "startup")
            
            assert result["category"] == ErrorCategory.STARTUP
            assert result["severity"] == ErrorSeverity.CRITICAL
            assert "Startup Error" in result["title"]
            assert not handler.can_continue(result["category"], result["severity"])