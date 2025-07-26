"""
Error recovery and retry mechanisms for auto-calibration.

This module provides intelligent error recovery strategies for calibration failures,
including device fallback, parameter adjustment, and retry logic.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from .audio_device_manager import AudioDeviceManager, AudioDeviceError, AudioDeviceMode
from .auto_calibration import CalibResult, calibrate
from .error_handler import ErrorCategory, ErrorHandler, ErrorSeverity

logger = logging.getLogger(__name__)

__all__ = [
    "CalibrationErrorType", 
    "CalibrationError", 
    "CalibrationRetryStrategy",
    "CalibrationErrorRecovery",
    "ParameterAdjustmentStrategy"
]


class CalibrationErrorType(Enum):
    """Types of calibration errors that can occur."""
    DEVICE_ACCESS = "device_access"
    SIGNAL_QUALITY = "signal_quality"
    DETECTION_FAILURE = "detection_failure"
    VALIDATION_FAILURE = "validation_failure"
    TIMEOUT = "timeout"
    HARDWARE_FAILURE = "hardware_failure"
    UNKNOWN = "unknown"


@dataclass
class CalibrationError(Exception):
    """Exception raised during calibration with recovery information."""
    message: str
    error_type: CalibrationErrorType
    device_id: Optional[int | str] = None
    original_exception: Optional[Exception] = None
    recovery_hints: List[str] = field(default_factory=list)
    can_retry: bool = True
    suggested_parameters: Optional[Dict[str, Any]] = None


@dataclass
class CalibrationRetryStrategy:
    """Configuration for calibration retry behavior."""
    max_attempts: int = 3
    device_fallback_enabled: bool = True
    parameter_adjustment_enabled: bool = True
    timeout_per_attempt: float = 30.0
    backoff_multiplier: float = 1.5
    min_backoff_delay: float = 1.0
    max_backoff_delay: float = 10.0


@dataclass
class ParameterAdjustmentStrategy:
    """Strategy for adjusting calibration parameters on failure."""
    sensitivity_adjustments: List[float] = field(default_factory=lambda: [1.0, 0.8, 1.2, 0.6, 1.5])
    debounce_adjustments: List[int] = field(default_factory=lambda: [0, 5, -5, 10, -10])
    target_press_tolerance: float = 0.2  # Allow 20% deviation from target presses
    signal_quality_threshold: float = 0.3  # Minimum acceptable signal quality


class CalibrationErrorRecovery:
    """Manages error recovery during auto-calibration with intelligent retry logic."""
    
    def __init__(self, audio_manager: Optional[AudioDeviceManager] = None):
        self.audio_manager = audio_manager or AudioDeviceManager()
        self.error_handler = ErrorHandler()
        self.retry_history: Dict[str, List[Dict[str, Any]]] = {}
        self.parameter_cache: Dict[str, Dict[str, Any]] = {}
        
    def handle_calibration_error(
        self,
        error: Exception,
        attempt: int,
        max_attempts: int,
        context: Dict[str, Any]
    ) -> Tuple[bool, CalibrationError]:
        """Handle calibration errors with recovery strategies.
        
        Args:
            error: The original exception that occurred
            attempt: Current attempt number (1-based)
            max_attempts: Maximum number of attempts allowed
            context: Context information about the calibration attempt
            
        Returns:
            Tuple of (should_retry, calibration_error)
        """
        # Categorize the error
        calib_error = self._categorize_calibration_error(error, context)
        
        # Log the error
        logger.warning(
            f"Calibration attempt {attempt}/{max_attempts} failed: {calib_error.message} "
            f"(type: {calib_error.error_type.value})"
        )
        
        # Record retry history
        session_id = context.get("session_id", "unknown")
        if session_id not in self.retry_history:
            self.retry_history[session_id] = []
            
        self.retry_history[session_id].append({
            "attempt": attempt,
            "error_type": calib_error.error_type.value,
            "error_message": calib_error.message,
            "device_id": calib_error.device_id,
            "timestamp": time.time(),
            "context": context.copy()
        })
        
        # Determine if we should retry
        should_retry = (
            attempt < max_attempts and 
            calib_error.can_retry and
            self._should_retry_error_type(calib_error.error_type, attempt)
        )
        
        if should_retry:
            # Generate recovery suggestions
            calib_error.recovery_hints = self._generate_recovery_hints(calib_error, attempt, context)
            
            # Suggest parameter adjustments if enabled
            if context.get("parameter_adjustment_enabled", True):
                calib_error.suggested_parameters = self._suggest_parameter_adjustments(
                    calib_error, attempt, context
                )
        
        return should_retry, calib_error
    
    def _categorize_calibration_error(
        self, 
        error: Exception, 
        context: Dict[str, Any]
    ) -> CalibrationError:
        """Categorize a calibration error and extract relevant information."""
        error_msg = str(error).lower()
        error_type_name = type(error).__name__
        
        # Check for audio device errors first
        if isinstance(error, AudioDeviceError):
            return CalibrationError(
                message=f"Audio device error: {error.error_type}",
                error_type=CalibrationErrorType.DEVICE_ACCESS,
                device_id=error.device_id,
                original_exception=error,
                recovery_hints=[error.recovery_hint] if error.recovery_hint else [],
                can_retry=error.error_type != "not_found"
            )
        
        # Check for timeout errors
        if "timeout" in error_msg or isinstance(error, TimeoutError):
            return CalibrationError(
                message="Calibration timed out",
                error_type=CalibrationErrorType.TIMEOUT,
                original_exception=error,
                can_retry=True
            )
        
        # Check for signal quality issues
        if any(keyword in error_msg for keyword in ["signal", "noise", "quality", "amplitude"]):
            return CalibrationError(
                message="Poor signal quality detected",
                error_type=CalibrationErrorType.SIGNAL_QUALITY,
                original_exception=error,
                can_retry=True
            )
        
        # Check for detection failures
        if any(keyword in error_msg for keyword in ["detection", "press", "threshold", "calibration"]):
            return CalibrationError(
                message="Failed to detect expected switch presses",
                error_type=CalibrationErrorType.DETECTION_FAILURE,
                original_exception=error,
                can_retry=True
            )
        
        # Check for hardware failures
        if any(keyword in error_msg for keyword in ["hardware", "device", "connection", "usb"]):
            return CalibrationError(
                message="Hardware connection issue",
                error_type=CalibrationErrorType.HARDWARE_FAILURE,
                original_exception=error,
                can_retry=False  # Hardware issues usually need manual intervention
            )
        
        # Default to unknown error type
        return CalibrationError(
            message=f"Unknown calibration error: {str(error)}",
            error_type=CalibrationErrorType.UNKNOWN,
            original_exception=error,
            can_retry=True
        )
    
    def _should_retry_error_type(self, error_type: CalibrationErrorType, attempt: int) -> bool:
        """Determine if we should retry based on error type and attempt number."""
        # Hardware failures typically don't benefit from retries
        if error_type == CalibrationErrorType.HARDWARE_FAILURE:
            return False
            
        # Device access errors: retry up to 2 times (device fallback might help)
        if error_type == CalibrationErrorType.DEVICE_ACCESS:
            return attempt <= 2
            
        # Signal quality and detection failures: retry up to 3 times
        if error_type in [CalibrationErrorType.SIGNAL_QUALITY, CalibrationErrorType.DETECTION_FAILURE]:
            return attempt <= 3
            
        # Validation failures: retry up to 2 times
        if error_type == CalibrationErrorType.VALIDATION_FAILURE:
            return attempt <= 2
            
        # Timeout errors: retry once
        if error_type == CalibrationErrorType.TIMEOUT:
            return attempt <= 1
            
        # Unknown errors: retry once to be safe
        return attempt <= 1
    
    def _generate_recovery_hints(
        self, 
        error: CalibrationError, 
        attempt: int, 
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate specific recovery hints based on error type and context."""
        hints = []
        
        if error.error_type == CalibrationErrorType.DEVICE_ACCESS:
            hints.extend([
                "Trying alternative audio devices",
                "Checking device permissions",
                "Attempting shared audio mode if exclusive mode failed"
            ])
            
        elif error.error_type == CalibrationErrorType.SIGNAL_QUALITY:
            hints.extend([
                "Adjusting sensitivity parameters",
                "Trying noise filtering",
                "Checking microphone positioning"
            ])
            
        elif error.error_type == CalibrationErrorType.DETECTION_FAILURE:
            hints.extend([
                "Adjusting detection thresholds",
                "Modifying debounce settings",
                "Trying different press timing"
            ])
            
        elif error.error_type == CalibrationErrorType.VALIDATION_FAILURE:
            hints.extend([
                "Relaxing validation criteria",
                "Adjusting quality thresholds",
                "Trying alternative validation methods"
            ])
            
        elif error.error_type == CalibrationErrorType.TIMEOUT:
            hints.extend([
                "Extending timeout duration",
                "Simplifying calibration process",
                "Checking system performance"
            ])
            
        # Add attempt-specific hints
        if attempt > 1:
            hints.append(f"This is retry attempt {attempt}")
            
        return hints
    
    def _suggest_parameter_adjustments(
        self, 
        error: CalibrationError, 
        attempt: int, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Suggest parameter adjustments based on error type and attempt number."""
        adjustments = {}
        
        # Get base parameters from context
        base_params = context.get("parameters", {})
        
        if error.error_type == CalibrationErrorType.SIGNAL_QUALITY:
            # Adjust sensitivity for signal quality issues
            sensitivity_factor = [1.0, 0.8, 1.2, 0.6][min(attempt - 1, 3)]
            adjustments["sensitivity_factor"] = sensitivity_factor
            
        elif error.error_type == CalibrationErrorType.DETECTION_FAILURE:
            # Adjust thresholds and debounce for detection issues
            threshold_factor = [1.0, 0.9, 1.1, 0.8][min(attempt - 1, 3)]
            debounce_adjustment = [0, 5, -5, 10][min(attempt - 1, 3)]
            
            adjustments["threshold_factor"] = threshold_factor
            adjustments["debounce_adjustment"] = debounce_adjustment
            
        elif error.error_type == CalibrationErrorType.VALIDATION_FAILURE:
            # Relax validation criteria
            quality_threshold = max(0.1, 0.5 - (attempt - 1) * 0.1)
            adjustments["quality_threshold"] = quality_threshold
            
        elif error.error_type == CalibrationErrorType.TIMEOUT:
            # Extend timeout and simplify process
            timeout_factor = 1.5 ** attempt
            adjustments["timeout_factor"] = timeout_factor
            adjustments["simplified_process"] = True
            
        return adjustments
    
    def try_device_fallback(
        self, 
        current_device: Optional[int | str],
        samplerate: int = 44100,
        blocksize: int = 256,
        preferred_mode: AudioDeviceMode = "auto"
    ) -> Tuple[Optional[int | str], Optional[str], Optional[AudioDeviceMode]]:
        """Try to find an alternative working audio device.
        
        Args:
            current_device: The device that failed
            samplerate: Sample rate to test with
            blocksize: Block size to test with
            preferred_mode: Preferred audio mode
            
        Returns:
            Tuple of (working_device_id, error_message, working_mode)
        """
        logger.info(f"Attempting device fallback from {current_device}")
        
        # Get fallback device chain, excluding the failed device
        fallback_chain = self.audio_manager.get_device_fallback_chain(current_device)
        
        # Remove the failed device from the chain
        if current_device in fallback_chain:
            fallback_chain.remove(current_device)
            
        # Try each device in the fallback chain
        for device in fallback_chain:
            logger.debug(f"Testing fallback device: {device}")
            
            # Test device with multiple modes
            modes_to_try = ["auto", "shared", "exclusive"]
            if preferred_mode != "auto":
                modes_to_try = [preferred_mode] + [m for m in modes_to_try if m != preferred_mode]
                
            for mode in modes_to_try:
                success, error = self.audio_manager.test_device(
                    device, samplerate, blocksize, mode=mode
                )
                
                if success:
                    logger.info(f"Found working fallback device: {device} in {mode} mode")
                    return device, None, mode
                    
        logger.warning("No working fallback devices found")
        return None, "No working audio devices available", None
    
    def adjust_calibration_parameters(
        self,
        base_parameters: Dict[str, Any],
        adjustments: Dict[str, Any],
        attempt: int
    ) -> Dict[str, Any]:
        """Apply parameter adjustments to base calibration parameters.
        
        Args:
            base_parameters: Original calibration parameters
            adjustments: Suggested adjustments from error recovery
            attempt: Current attempt number
            
        Returns:
            Adjusted parameters dictionary
        """
        adjusted = base_parameters.copy()
        
        # Apply sensitivity adjustments
        if "sensitivity_factor" in adjustments:
            factor = adjustments["sensitivity_factor"]
            if "upper_offset" in adjusted:
                adjusted["upper_offset"] *= factor
            if "lower_offset" in adjusted:
                adjusted["lower_offset"] *= factor
                
        # Apply threshold adjustments
        if "threshold_factor" in adjustments:
            factor = adjustments["threshold_factor"]
            if "upper_threshold" in adjusted:
                adjusted["upper_threshold"] *= factor
            if "lower_threshold" in adjusted:
                adjusted["lower_threshold"] *= factor
                
        # Apply debounce adjustments
        if "debounce_adjustment" in adjustments:
            adjustment = adjustments["debounce_adjustment"]
            if "debounce_ms" in adjusted:
                adjusted["debounce_ms"] = max(10, adjusted["debounce_ms"] + adjustment)
                
        # Apply quality threshold adjustments
        if "quality_threshold" in adjustments:
            adjusted["quality_threshold"] = adjustments["quality_threshold"]
            
        # Apply timeout adjustments
        if "timeout_factor" in adjustments:
            factor = adjustments["timeout_factor"]
            if "timeout" in adjusted:
                adjusted["timeout"] *= factor
                
        # Apply process simplification
        if adjustments.get("simplified_process", False):
            adjusted["simplified_process"] = True
            adjusted["target_presses"] = min(adjusted.get("target_presses", 5), 3)
            
        logger.debug(f"Applied parameter adjustments for attempt {attempt}: {adjustments}")
        return adjusted
    
    def validate_calibration_quality(
        self, 
        result: CalibResult, 
        samples: np.ndarray,
        quality_threshold: float = 0.5
    ) -> Tuple[bool, List[str]]:
        """Validate calibration results with enhanced quality checks.
        
        Args:
            result: Calibration result to validate
            samples: Original audio samples used for calibration
            quality_threshold: Minimum quality threshold (0.0 to 1.0)
            
        Returns:
            Tuple of (is_valid, validation_issues)
        """
        issues = []
        
        # Check basic calibration success
        if not result.calib_ok:
            issues.append("Basic calibration validation failed")
            
        # Check signal-to-noise ratio
        if result.baseline_std > 0:
            signal_range = abs(result.upper_offset - result.lower_offset)
            snr = signal_range / (3 * result.baseline_std)  # 3-sigma noise level
            
            if snr < 2.0:  # Minimum SNR threshold
                issues.append(f"Poor signal-to-noise ratio: {snr:.2f} (minimum: 2.0)")
                
        # Check threshold separation
        threshold_gap = abs(result.upper_offset - result.lower_offset)
        if threshold_gap < 0.01:  # Minimum threshold separation
            issues.append(f"Thresholds too close together: {threshold_gap:.4f}")
            
        # Check event detection consistency
        if len(result.events) == 0:
            issues.append("No switch presses detected")
        elif result.min_gap < 0.05:  # Minimum 50ms between presses
            issues.append(f"Switch presses too close together: {result.min_gap:.3f}s")
            
        # Check debounce effectiveness
        if result.debounce_ms > 100:  # Excessive debounce might indicate poor signal
            issues.append(f"Excessive debounce required: {result.debounce_ms}ms")
            
        # Calculate overall quality score
        quality_score = self._calculate_quality_score(result, samples)
        if quality_score < quality_threshold:
            issues.append(f"Overall quality too low: {quality_score:.2f} (minimum: {quality_threshold:.2f})")
            
        is_valid = len(issues) == 0
        return is_valid, issues
    
    def _calculate_quality_score(self, result: CalibResult, samples: np.ndarray) -> float:
        """Calculate an overall quality score for calibration results."""
        score = 1.0
        
        # Penalize for basic calibration failure
        if not result.calib_ok:
            score *= 0.5
            
        # Penalize for poor SNR
        if result.baseline_std > 0:
            signal_range = abs(result.upper_offset - result.lower_offset)
            snr = signal_range / (3 * result.baseline_std)
            score *= min(1.0, snr / 3.0)  # Normalize to 3.0 as good SNR
            
        # Penalize for excessive debounce
        debounce_penalty = max(0.5, 1.0 - (result.debounce_ms - 20) / 100)
        score *= debounce_penalty
        
        # Penalize for too few events
        if len(result.events) < 3:
            score *= 0.7
            
        # Penalize for events too close together
        if result.min_gap < 0.1:
            score *= 0.8
            
        return max(0.0, min(1.0, score))
    
    def get_retry_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get retry history for a calibration session."""
        return self.retry_history.get(session_id, [])
    
    def clear_retry_history(self, session_id: Optional[str] = None) -> None:
        """Clear retry history for a session or all sessions."""
        if session_id:
            self.retry_history.pop(session_id, None)
        else:
            self.retry_history.clear()
    
    def suggest_improvements(
        self, 
        error_type: CalibrationErrorType, 
        signal_data: Optional[np.ndarray] = None
    ) -> List[str]:
        """Provide specific suggestions based on error analysis.
        
        Args:
            error_type: Type of calibration error
            signal_data: Optional signal data for analysis
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        if error_type == CalibrationErrorType.DEVICE_ACCESS:
            suggestions.extend([
                "Check that your microphone is properly connected",
                "Close other applications that might be using your microphone",
                "Try a different USB port for USB microphones",
                "Check Windows audio device settings",
                "Run the application as administrator if needed"
            ])
            
        elif error_type == CalibrationErrorType.SIGNAL_QUALITY:
            suggestions.extend([
                "Move your microphone closer to the ablenet switch",
                "Reduce background noise in your environment",
                "Check that your microphone is not muted",
                "Try adjusting microphone sensitivity in Windows settings",
                "Ensure the ablenet switch is properly connected"
            ])
            
        elif error_type == CalibrationErrorType.DETECTION_FAILURE:
            suggestions.extend([
                "Press the switch more firmly during calibration",
                "Wait for the prompt before pressing the switch",
                "Try pressing the switch at a steady rhythm",
                "Check that the switch is making a clear clicking sound",
                "Ensure the switch cable is fully inserted"
            ])
            
        elif error_type == CalibrationErrorType.VALIDATION_FAILURE:
            suggestions.extend([
                "Try calibrating in a quieter environment",
                "Use a different microphone if available",
                "Check that the ablenet switch is working properly",
                "Try manual calibration if auto-calibration continues to fail"
            ])
            
        elif error_type == CalibrationErrorType.HARDWARE_FAILURE:
            suggestions.extend([
                "Check all cable connections",
                "Try a different ablenet switch if available",
                "Test the switch with another device",
                "Contact technical support if problems persist"
            ])
            
        # Add signal-specific suggestions if data is available
        if signal_data is not None:
            signal_suggestions = self._analyze_signal_for_suggestions(signal_data)
            suggestions.extend(signal_suggestions)
            
        return suggestions
    
    def _analyze_signal_for_suggestions(self, signal_data: np.ndarray) -> List[str]:
        """Analyze signal data to provide specific improvement suggestions."""
        suggestions = []
        
        # Check signal amplitude
        signal_range = np.ptp(signal_data)  # Peak-to-peak range
        if signal_range < 0.01:
            suggestions.append("Signal amplitude is very low - try moving microphone closer")
        elif signal_range > 0.8:
            suggestions.append("Signal amplitude is very high - try reducing microphone sensitivity")
            
        # Check for clipping
        if np.any(np.abs(signal_data) > 0.95):
            suggestions.append("Audio signal is clipping - reduce microphone gain")
            
        # Check noise level
        noise_level = np.std(signal_data)
        if noise_level > 0.1:
            suggestions.append("High background noise detected - try a quieter environment")
            
        # Check for DC offset
        dc_offset = np.mean(signal_data)
        if abs(dc_offset) > 0.1:
            suggestions.append("DC offset detected - check microphone connection")
            
        return suggestions