"""Centralized error handling system for Switch Interface.

This module provides a unified approach to handling errors across the application,
with user-friendly messages and specific troubleshooting suggestions.
"""

from __future__ import annotations

import logging
import sys
import traceback
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import sounddevice as sd


class ErrorCategory(Enum):
    """Categories of errors that can occur in the application."""
    AUDIO = "audio"
    CONFIG = "config"
    STARTUP = "startup"
    LAYOUT = "layout"
    CALIBRATION = "calibration"
    HARDWARE = "hardware"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"          # Minor issues, application can continue
    MEDIUM = "medium"    # Significant issues, some functionality affected
    HIGH = "high"        # Major issues, core functionality affected
    CRITICAL = "critical"  # Application cannot function


class ErrorHandler:
    """Centralized error handler with user-friendly messages and troubleshooting."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize an error based on its type and context."""
        error_type = type(error).__name__
        error_msg = str(error).lower()
        
        # Startup errors (check first as they're most critical)
        if (isinstance(error, (ImportError, ModuleNotFoundError)) or
            "startup" in error_msg or "launch" in error_msg):
            return ErrorCategory.STARTUP
            
        # Configuration errors (check before audio to catch config-specific file errors)
        if (isinstance(error, (FileNotFoundError, PermissionError)) and 
            ("config" in error_msg or ".json" in error_msg)):
            return ErrorCategory.CONFIG
            
        # Layout errors (check before audio to catch layout-specific errors)
        if ("layout" in error_msg or ("keyboard" in error_msg and "json" in error_msg)):
            return ErrorCategory.LAYOUT
            
        # Calibration errors (check before audio to catch calibration-specific errors)
        if ("calibration" in error_msg or "detector" in error_msg or
            "threshold" in error_msg):
            return ErrorCategory.CALIBRATION
            
        # Hardware errors (check before audio to catch hardware-specific errors)
        if ("hardware" in error_msg or ("connection" in error_msg and "usb" in error_msg) or
            ("usb" in error_msg and "device" not in error_msg)):
            return ErrorCategory.HARDWARE
            
        # Audio-related errors (broader check, but after more specific categories)
        if (isinstance(error, (sd.PortAudioError, OSError)) or 
            "audio" in error_msg or "microphone" in error_msg or 
            "portaudio" in error_msg or "sounddevice" in error_msg or
            ("device" in error_msg and any(word in error_msg for word in ["sound", "input", "record"]))):
            return ErrorCategory.AUDIO
            
        return ErrorCategory.UNKNOWN
    
    def get_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine the severity of an error."""
        if category == ErrorCategory.STARTUP:
            return ErrorSeverity.CRITICAL
        elif category == ErrorCategory.AUDIO:
            # Audio errors are high severity as they affect core functionality
            return ErrorSeverity.HIGH
        elif category in [ErrorCategory.CONFIG, ErrorCategory.LAYOUT]:
            return ErrorSeverity.MEDIUM
        elif category == ErrorCategory.CALIBRATION:
            return ErrorSeverity.MEDIUM
        elif category == ErrorCategory.HARDWARE:
            return ErrorSeverity.HIGH
        else:
            return ErrorSeverity.MEDIUM
    
    def generate_user_message(self, error: Exception, category: ErrorCategory) -> Tuple[str, str]:
        """Generate user-friendly error message and troubleshooting suggestions.
        
        Returns:
            Tuple of (title, detailed_message)
        """
        if category == ErrorCategory.AUDIO:
            return self._handle_audio_error(error)
        elif category == ErrorCategory.CONFIG:
            return self._handle_config_error(error)
        elif category == ErrorCategory.STARTUP:
            return self._handle_startup_error(error)
        elif category == ErrorCategory.LAYOUT:
            return self._handle_layout_error(error)
        elif category == ErrorCategory.CALIBRATION:
            return self._handle_calibration_error(error)
        elif category == ErrorCategory.HARDWARE:
            return self._handle_hardware_error(error)
        else:
            return self._handle_unknown_error(error)
    
    def _handle_audio_error(self, error: Exception) -> Tuple[str, str]:
        """Handle audio-related errors."""
        title = "Audio Device Error"
        
        error_msg = str(error).lower()
        
        if "no device" in error_msg or "device not found" in error_msg:
            message = (
                "No microphone or audio input device was detected.\n\n"
                "Solutions to try:\n"
                "• Connect a microphone or headset to your computer\n"
                "• Check that your audio device is properly plugged in\n"
                "• Try a different USB port if using a USB microphone\n"
                "• Check Windows Sound settings to ensure the device is recognized\n"
                "• Restart the application after connecting your device\n\n"
                "If you continue having issues, try the 'Calibrate' button to select a different device."
            )
        elif "exclusive" in error_msg or "access" in error_msg:
            message = (
                "Could not get exclusive access to your audio device.\n\n"
                "This usually happens when another application is using your microphone.\n\n"
                "Solutions to try:\n"
                "• Close other applications that might be using your microphone\n"
                "• Close video conferencing apps (Zoom, Teams, Skype, etc.)\n"
                "• Close voice recording software\n"
                "• Restart your computer to free up audio resources\n\n"
                "The application will try to use shared mode automatically."
            )
        elif "permission" in error_msg:
            message = (
                "Permission denied when trying to access your microphone.\n\n"
                "Solutions to try:\n"
                "• Check Windows Privacy settings for microphone access\n"
                "• Allow this application to access your microphone\n"
                "• Run the application as administrator\n"
                "• Check antivirus software settings\n\n"
                "Go to Settings > Privacy > Microphone to adjust permissions."
            )
        else:
            message = (
                "There was a problem with your audio device.\n\n"
                "Solutions to try:\n"
                "• Click 'Calibrate' to select your microphone\n"
                "• Check that your microphone is connected and working\n"
                "• Try unplugging and reconnecting your audio device\n"
                "• Restart the application\n"
                "• Try a different microphone if available\n\n"
                f"Technical details: {str(error)}"
            )
        
        return title, message
    
    def _handle_config_error(self, error: Exception) -> Tuple[str, str]:
        """Handle configuration-related errors."""
        title = "Configuration Error"
        
        error_msg = str(error).lower()
        error_type = type(error).__name__
        
        if isinstance(error, PermissionError) or "permission" in error_msg:
            message = (
                "Could not save or load configuration settings.\n\n"
                "Solutions to try:\n"
                "• Run the application as administrator\n"
                "• Check that you have write permissions to your user folder\n"
                "• Close any antivirus software temporarily\n"
                "• Try running from a different location\n\n"
                "Your settings will use defaults until this is resolved."
            )
        elif "json" in error_msg or "decode" in error_msg:
            message = (
                "Your configuration file appears to be corrupted.\n\n"
                "The application will reset to default settings.\n\n"
                "What happened:\n"
                "• Your settings file became corrupted\n"
                "• This can happen due to unexpected shutdowns or disk errors\n"
                "• All settings will be reset to safe defaults\n\n"
                "You can reconfigure your preferences in the launcher."
            )
        else:
            message = (
                "There was a problem with your configuration settings.\n\n"
                "Solutions to try:\n"
                "• The application will use default settings\n"
                "• You can reconfigure your preferences in the launcher\n"
                "• If problems persist, try deleting the settings folder\n\n"
                f"Technical details: {str(error)}"
            )
        
        return title, message
    
    def _handle_startup_error(self, error: Exception) -> Tuple[str, str]:
        """Handle startup-related errors."""
        title = "Startup Error"
        
        error_msg = str(error).lower()
        error_type = type(error).__name__
        
        if isinstance(error, (ImportError, ModuleNotFoundError)) or "module" in error_msg or "import" in error_msg:
            message = (
                "A required component could not be loaded.\n\n"
                "This usually means the application was not installed correctly.\n\n"
                "Solutions to try:\n"
                "• Reinstall the Switch Interface application\n"
                "• Check that all required files are present\n"
                "• Try running from the original installation location\n"
                "• Contact support if the problem persists\n\n"
                f"Missing component: {str(error)}"
            )
        elif isinstance(error, PermissionError) or "permission" in error_msg:
            message = (
                "The application does not have permission to start properly.\n\n"
                "Solutions to try:\n"
                "• Run the application as administrator\n"
                "• Check antivirus software settings\n"
                "• Try installing to a different location\n"
                "• Check Windows User Account Control settings\n\n"
                "Contact your system administrator if needed."
            )
        else:
            message = (
                "The application could not start properly.\n\n"
                "Solutions to try:\n"
                "• Restart your computer and try again\n"
                "• Run the application as administrator\n"
                "• Reinstall the application\n"
                "• Check the log file for more details\n\n"
                f"Technical details: {str(error)}"
            )
        
        return title, message
    
    def _handle_layout_error(self, error: Exception) -> Tuple[str, str]:
        """Handle layout-related errors."""
        title = "Keyboard Layout Error"
        
        error_msg = str(error).lower()
        
        if "not found" in error_msg or "filenotfound" in error_msg:
            message = (
                "The selected keyboard layout could not be found.\n\n"
                "Solutions to try:\n"
                "• The application will use a default layout\n"
                "• Check that the layout file exists\n"
                "• Try selecting a different layout in the launcher\n"
                "• Reinstall the application to restore default layouts\n\n"
                "You can continue using the default layout."
            )
        elif "json" in error_msg or "decode" in error_msg:
            message = (
                "The keyboard layout file appears to be corrupted.\n\n"
                "Solutions to try:\n"
                "• The application will use a default layout\n"
                "• Try selecting a different layout\n"
                "• If using a custom layout, check the JSON format\n"
                "• Reinstall to restore default layouts\n\n"
                "You can continue with the default layout."
            )
        else:
            message = (
                "There was a problem loading the keyboard layout.\n\n"
                "Solutions to try:\n"
                "• The application will use a default layout\n"
                "• Try selecting a different layout in the launcher\n"
                "• Check that layout files are not corrupted\n"
                "• Reinstall if problems persist\n\n"
                f"Technical details: {str(error)}"
            )
        
        return title, message
    
    def _handle_calibration_error(self, error: Exception) -> Tuple[str, str]:
        """Handle calibration-related errors."""
        title = "Calibration Error"
        
        message = (
            "There was a problem with the calibration process.\n\n"
            "Solutions to try:\n"
            "• Click 'Skip Calibration' to use default settings\n"
            "• Try calibrating with a different microphone\n"
            "• Check that your microphone is working properly\n"
            "• Make sure your microphone is not muted\n"
            "• Try moving closer to your microphone\n\n"
            "You can skip calibration and adjust settings later if needed."
        )
        
        return title, message
    
    def _handle_hardware_error(self, error: Exception) -> Tuple[str, str]:
        """Handle hardware-related errors."""
        title = "Hardware Error"
        
        message = (
            "There was a problem with your hardware setup.\n\n"
            "Solutions to try:\n"
            "• Check all cable connections\n"
            "• Try different USB ports\n"
            "• Restart your computer\n"
            "• Try a different microphone or switch\n"
            "• Check device manager for hardware issues\n\n"
            "Contact technical support if problems persist."
        )
        
        return title, message
    
    def _handle_unknown_error(self, error: Exception) -> Tuple[str, str]:
        """Handle unknown or unexpected errors."""
        title = "Unexpected Error"
        
        message = (
            "An unexpected error occurred.\n\n"
            "Solutions to try:\n"
            "• Restart the application\n"
            "• Restart your computer\n"
            "• Check the log file for more details\n"
            "• Contact support if the problem persists\n\n"
            f"Technical details: {str(error)}"
        )
        
        return title, message
    
    def handle_error(self, error: Exception, context: Optional[str] = None) -> Dict[str, Any]:
        """Main error handling method that processes an error and returns structured information.
        
        Args:
            error: The exception that occurred
            context: Optional context about where the error occurred
            
        Returns:
            Dictionary containing error information for display or logging
        """
        category = self.categorize_error(error)
        severity = self.get_severity(error, category)
        title, message = self.generate_user_message(error, category)
        
        # Log the error with appropriate level
        log_message = f"Error in {context or 'unknown context'}: {str(error)}"
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, exc_info=True)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, exc_info=True)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message, exc_info=True)
        else:
            self.logger.info(log_message, exc_info=True)
        
        return {
            "title": title,
            "message": message,
            "category": category,
            "severity": severity,
            "technical_details": str(error),
            "traceback": traceback.format_exc() if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None,
            "context": context,
            "suggestions": self._get_recovery_suggestions(category, severity)
        }
    
    def _get_recovery_suggestions(self, category: ErrorCategory, severity: ErrorSeverity) -> list[str]:
        """Get specific recovery suggestions based on error category and severity."""
        suggestions = []
        
        if category == ErrorCategory.AUDIO:
            suggestions = [
                "Try the 'Calibrate' button to select your microphone",
                "Check microphone connections",
                "Close other applications using audio",
                "Restart the application"
            ]
        elif category == ErrorCategory.CONFIG:
            suggestions = [
                "Application will use default settings",
                "Reconfigure preferences in launcher",
                "Check file permissions"
            ]
        elif category == ErrorCategory.STARTUP:
            suggestions = [
                "Restart the application",
                "Run as administrator",
                "Reinstall the application"
            ]
        elif category == ErrorCategory.LAYOUT:
            suggestions = [
                "Try a different keyboard layout",
                "Use default layout",
                "Check layout file format"
            ]
        elif category == ErrorCategory.CALIBRATION:
            suggestions = [
                "Skip calibration and use defaults",
                "Try different microphone",
                "Check microphone is not muted"
            ]
        elif category == ErrorCategory.HARDWARE:
            suggestions = [
                "Check hardware connections",
                "Try different USB ports",
                "Restart computer"
            ]
        else:
            suggestions = [
                "Restart the application",
                "Check log files",
                "Contact support"
            ]
        
        # Add severity-specific suggestions
        if severity == ErrorSeverity.CRITICAL:
            suggestions.insert(0, "Application cannot continue normally")
        elif severity == ErrorSeverity.HIGH:
            suggestions.insert(0, "Core functionality may be affected")
        
        return suggestions
    
    def can_continue(self, category: ErrorCategory, severity: ErrorSeverity) -> bool:
        """Determine if the application can continue after this error."""
        if severity == ErrorSeverity.CRITICAL:
            return False
        if category == ErrorCategory.STARTUP and severity == ErrorSeverity.HIGH:
            return False
        return True
    
    def suggest_safe_mode(self, category: ErrorCategory, severity: ErrorSeverity) -> bool:
        """Determine if safe mode should be suggested for this error."""
        return (severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] and 
                category in [ErrorCategory.AUDIO, ErrorCategory.HARDWARE, ErrorCategory.STARTUP])


# Global error handler instance
error_handler = ErrorHandler()