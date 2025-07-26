"""Tests for calibration error recovery system."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from switch_interface.calibration_error_recovery import (
    CalibrationErrorRecovery,
    CalibrationError,
    CalibrationErrorType,
    CalibrationRetryStrategy,
    ParameterAdjustmentStrategy
)
from switch_interface.audio_device_manager import AudioDeviceError, AudioDeviceManager
from switch_interface.auto_calibration import CalibResult


class TestCalibrationErrorRecovery:
    """Test the CalibrationErrorRecovery class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.audio_manager = Mock(spec=AudioDeviceManager)
        self.recovery = CalibrationErrorRecovery(self.audio_manager)
        
    def test_categorize_audio_device_error(self):
        """Test categorization of audio device errors."""
        audio_error = AudioDeviceError(
            "Device access denied", 
            device_id=1, 
            error_type="access",
            recovery_hint="Close other applications"
        )
        
        context = {"session_id": "test_session"}
        calib_error = self.recovery._categorize_calibration_error(audio_error, context)
        
        assert calib_error.error_type == CalibrationErrorType.DEVICE_ACCESS
        assert calib_error.device_id == 1
        assert calib_error.recovery_hints == ["Close other applications"]
        assert calib_error.can_retry is True
        
    def test_categorize_timeout_error(self):
        """Test categorization of timeout errors."""
        timeout_error = TimeoutError("Calibration timed out")
        context = {"session_id": "test_session"}
        
        calib_error = self.recovery._categorize_calibration_error(timeout_error, context)
        
        assert calib_error.error_type == CalibrationErrorType.TIMEOUT
        assert calib_error.can_retry is True
        
    def test_categorize_signal_quality_error(self):
        """Test categorization of signal quality errors."""
        signal_error = Exception("Poor signal quality detected")
        context = {"session_id": "test_session"}
        
        calib_error = self.recovery._categorize_calibration_error(signal_error, context)
        
        assert calib_error.error_type == CalibrationErrorType.SIGNAL_QUALITY
        assert calib_error.can_retry is True
        
    def test_categorize_detection_failure(self):
        """Test categorization of detection failures."""
        detection_error = Exception("Failed to detect switch presses")
        context = {"session_id": "test_session"}
        
        calib_error = self.recovery._categorize_calibration_error(detection_error, context)
        
        assert calib_error.error_type == CalibrationErrorType.DETECTION_FAILURE
        assert calib_error.can_retry is True
        
    def test_categorize_hardware_failure(self):
        """Test categorization of hardware failures."""
        hardware_error = Exception("Hardware connection failed")
        context = {"session_id": "test_session"}
        
        calib_error = self.recovery._categorize_calibration_error(hardware_error, context)
        
        assert calib_error.error_type == CalibrationErrorType.HARDWARE_FAILURE
        assert calib_error.can_retry is False
        
    def test_should_retry_error_type(self):
        """Test retry logic for different error types."""
        # Hardware failures should not retry
        assert not self.recovery._should_retry_error_type(CalibrationErrorType.HARDWARE_FAILURE, 1)
        
        # Device access errors should retry up to 2 times
        assert self.recovery._should_retry_error_type(CalibrationErrorType.DEVICE_ACCESS, 1)
        assert self.recovery._should_retry_error_type(CalibrationErrorType.DEVICE_ACCESS, 2)
        assert not self.recovery._should_retry_error_type(CalibrationErrorType.DEVICE_ACCESS, 3)
        
        # Signal quality errors should retry up to 3 times
        assert self.recovery._should_retry_error_type(CalibrationErrorType.SIGNAL_QUALITY, 3)
        assert not self.recovery._should_retry_error_type(CalibrationErrorType.SIGNAL_QUALITY, 4)
        
        # Timeout errors should retry once
        assert self.recovery._should_retry_error_type(CalibrationErrorType.TIMEOUT, 1)
        assert not self.recovery._should_retry_error_type(CalibrationErrorType.TIMEOUT, 2)
        
    def test_handle_calibration_error_retry_decision(self):
        """Test error handling and retry decision logic."""
        error = Exception("Signal quality poor")
        context = {
            "session_id": "test_session",
            "parameters": {"sensitivity": 1.0}
        }
        
        # First attempt should allow retry
        should_retry, calib_error = self.recovery.handle_calibration_error(error, 1, 3, context)
        
        assert should_retry is True
        assert calib_error.error_type == CalibrationErrorType.SIGNAL_QUALITY
        assert len(calib_error.recovery_hints) > 0
        assert calib_error.suggested_parameters is not None
        
        # Check retry history was recorded
        history = self.recovery.get_retry_history("test_session")
        assert len(history) == 1
        assert history[0]["attempt"] == 1
        assert history[0]["error_type"] == "signal_quality"
        
    def test_handle_calibration_error_max_attempts(self):
        """Test that retry is disabled when max attempts reached."""
        error = Exception("Signal quality poor")
        context = {"session_id": "test_session"}
        
        # At max attempts, should not retry
        should_retry, calib_error = self.recovery.handle_calibration_error(error, 3, 3, context)
        
        assert should_retry is False
        
    def test_generate_recovery_hints(self):
        """Test generation of recovery hints for different error types."""
        context = {"session_id": "test_session"}
        
        # Device access error hints
        device_error = CalibrationError(
            "Device access failed",
            CalibrationErrorType.DEVICE_ACCESS
        )
        hints = self.recovery._generate_recovery_hints(device_error, 1, context)
        
        assert "Trying alternative audio devices" in hints
        assert "Checking device permissions" in hints
        
        # Signal quality error hints
        signal_error = CalibrationError(
            "Poor signal quality",
            CalibrationErrorType.SIGNAL_QUALITY
        )
        hints = self.recovery._generate_recovery_hints(signal_error, 1, context)
        
        assert "Adjusting sensitivity parameters" in hints
        assert "Trying noise filtering" in hints
        
    def test_suggest_parameter_adjustments(self):
        """Test parameter adjustment suggestions."""
        context = {
            "session_id": "test_session",
            "parameters": {"sensitivity": 1.0, "debounce_ms": 20}
        }
        
        # Signal quality error adjustments
        signal_error = CalibrationError(
            "Poor signal quality",
            CalibrationErrorType.SIGNAL_QUALITY
        )
        adjustments = self.recovery._suggest_parameter_adjustments(signal_error, 2, context)
        
        assert "sensitivity_factor" in adjustments
        assert adjustments["sensitivity_factor"] == 0.8  # Second attempt adjustment
        
        # Detection failure adjustments
        detection_error = CalibrationError(
            "Detection failed",
            CalibrationErrorType.DETECTION_FAILURE
        )
        adjustments = self.recovery._suggest_parameter_adjustments(detection_error, 1, context)
        
        assert "threshold_factor" in adjustments
        assert "debounce_adjustment" in adjustments
        
    def test_try_device_fallback(self):
        """Test device fallback functionality."""
        # Mock audio manager methods
        self.audio_manager.get_device_fallback_chain.return_value = [0, None, 1, 2, 3]
        
        # Mock test_device to fail for None device but succeed for device 1
        def mock_test_device(device, samplerate, blocksize, mode="auto"):
            if device is None:
                return (False, "Failed")
            elif device == 1:
                return (True, None)
            else:
                return (False, "Failed")
        
        self.audio_manager.test_device.side_effect = mock_test_device
        
        device, error, mode = self.recovery.try_device_fallback(
            current_device=0,  # Failed device
            samplerate=44100,
            blocksize=256,
            preferred_mode="auto"
        )
        
        assert device == 1
        assert error is None
        assert mode == "auto"
        
        # Verify the failed device was excluded from fallback chain
        self.audio_manager.get_device_fallback_chain.assert_called_once_with(0)
        
    def test_try_device_fallback_no_working_device(self):
        """Test device fallback when no devices work."""
        self.audio_manager.get_device_fallback_chain.return_value = [1, 2]
        self.audio_manager.test_device.return_value = (False, "All devices failed")
        
        device, error, mode = self.recovery.try_device_fallback(
            current_device=0,
            samplerate=44100,
            blocksize=256,
            preferred_mode="auto"
        )
        
        assert device is None
        assert "No working audio devices available" in error
        assert mode is None
        
    def test_adjust_calibration_parameters(self):
        """Test parameter adjustment application."""
        base_params = {
            "upper_offset": -0.1,
            "lower_offset": -0.2,
            "debounce_ms": 20,
            "timeout": 30.0
        }
        
        adjustments = {
            "sensitivity_factor": 0.8,
            "debounce_adjustment": 5,
            "timeout_factor": 1.5
        }
        
        adjusted = self.recovery.adjust_calibration_parameters(base_params, adjustments, 2)
        
        assert abs(adjusted["upper_offset"] - (-0.08)) < 1e-10  # -0.1 * 0.8
        assert abs(adjusted["lower_offset"] - (-0.16)) < 1e-10  # -0.2 * 0.8
        assert adjusted["debounce_ms"] == 25      # 20 + 5
        assert adjusted["timeout"] == 45.0        # 30.0 * 1.5
        
    def test_validate_calibration_quality_good_result(self):
        """Test validation of good calibration results."""
        # Create a good calibration result
        result = CalibResult(
            events=[1000, 2000, 3000],
            upper_offset=-0.1,
            lower_offset=-0.2,
            debounce_ms=20,
            samplerate=44100,
            baseline_std=0.01,
            min_gap=0.5,
            calib_ok=True
        )
        
        samples = np.random.normal(0, 0.01, 44100)  # 1 second of low-noise signal
        
        is_valid, issues = self.recovery.validate_calibration_quality(result, samples, 0.5)
        
        assert is_valid is True
        assert len(issues) == 0
        
    def test_validate_calibration_quality_poor_result(self):
        """Test validation of poor calibration results."""
        # Create a poor calibration result
        result = CalibResult(
            events=[],  # No events detected
            upper_offset=-0.001,
            lower_offset=-0.002,  # Thresholds too close
            debounce_ms=150,      # Excessive debounce
            samplerate=44100,
            baseline_std=0.1,     # High noise
            min_gap=0.01,         # Events too close
            calib_ok=False
        )
        
        samples = np.random.normal(0, 0.1, 44100)  # Noisy signal
        
        is_valid, issues = self.recovery.validate_calibration_quality(result, samples, 0.5)
        
        assert is_valid is False
        assert len(issues) > 0
        assert any("No switch presses detected" in issue for issue in issues)
        assert any("Thresholds too close together" in issue for issue in issues)
        assert any("Excessive debounce required" in issue for issue in issues)
        
    def test_calculate_quality_score(self):
        """Test quality score calculation."""
        # Good result should have high score
        good_result = CalibResult(
            events=[1000, 2000, 3000],
            upper_offset=-0.1,
            lower_offset=-0.2,
            debounce_ms=20,
            samplerate=44100,
            baseline_std=0.01,
            min_gap=0.5,
            calib_ok=True
        )
        
        samples = np.random.normal(0, 0.01, 44100)
        score = self.recovery._calculate_quality_score(good_result, samples)
        
        assert score > 0.8  # Should be high quality
        
        # Poor result should have low score
        poor_result = CalibResult(
            events=[1000],  # Only one event
            upper_offset=-0.01,
            lower_offset=-0.02,
            debounce_ms=100,  # High debounce
            samplerate=44100,
            baseline_std=0.1,  # High noise
            min_gap=0.01,      # Events too close
            calib_ok=False
        )
        
        score = self.recovery._calculate_quality_score(poor_result, samples)
        
        assert score < 0.5  # Should be low quality
        
    def test_suggest_improvements(self):
        """Test improvement suggestions for different error types."""
        # Device access suggestions
        suggestions = self.recovery.suggest_improvements(CalibrationErrorType.DEVICE_ACCESS)
        
        assert any("microphone is properly connected" in s for s in suggestions)
        assert any("Close other applications" in s for s in suggestions)
        
        # Signal quality suggestions
        suggestions = self.recovery.suggest_improvements(CalibrationErrorType.SIGNAL_QUALITY)
        
        assert any("Move your microphone closer" in s for s in suggestions)
        assert any("Reduce background noise" in s for s in suggestions)
        
        # Detection failure suggestions
        suggestions = self.recovery.suggest_improvements(CalibrationErrorType.DETECTION_FAILURE)
        
        assert any("Press the switch more firmly" in s for s in suggestions)
        assert any("Wait for the prompt" in s for s in suggestions)
        
    def test_analyze_signal_for_suggestions(self):
        """Test signal analysis for improvement suggestions."""
        # Low amplitude signal
        low_signal = np.random.normal(0, 0.001, 1000)
        suggestions = self.recovery._analyze_signal_for_suggestions(low_signal)
        
        assert any("Signal amplitude is very low" in s for s in suggestions)
        
        # High amplitude signal
        high_signal = np.random.normal(0, 0.4, 1000)
        suggestions = self.recovery._analyze_signal_for_suggestions(high_signal)
        
        assert any("Signal amplitude is very high" in s for s in suggestions)
        
        # Clipping signal
        clipping_signal = np.array([0.98, -0.97, 0.96, -0.98])
        suggestions = self.recovery._analyze_signal_for_suggestions(clipping_signal)
        
        assert any("Audio signal is clipping" in s for s in suggestions)
        
        # Noisy signal
        noisy_signal = np.random.normal(0, 0.2, 1000)
        suggestions = self.recovery._analyze_signal_for_suggestions(noisy_signal)
        
        assert any("High background noise detected" in s for s in suggestions)
        
        # DC offset signal
        dc_signal = np.random.normal(0.2, 0.01, 1000)
        suggestions = self.recovery._analyze_signal_for_suggestions(dc_signal)
        
        assert any("DC offset detected" in s for s in suggestions)
        
    def test_retry_history_management(self):
        """Test retry history recording and management."""
        session_id = "test_session"
        error = Exception("Test error")
        context = {"session_id": session_id}
        
        # Handle multiple errors to build history
        self.recovery.handle_calibration_error(error, 1, 3, context)
        self.recovery.handle_calibration_error(error, 2, 3, context)
        
        history = self.recovery.get_retry_history(session_id)
        
        assert len(history) == 2
        assert history[0]["attempt"] == 1
        assert history[1]["attempt"] == 2
        
        # Clear specific session history
        self.recovery.clear_retry_history(session_id)
        history = self.recovery.get_retry_history(session_id)
        
        assert len(history) == 0
        
    def test_clear_all_retry_history(self):
        """Test clearing all retry history."""
        # Add history for multiple sessions
        error = Exception("Test error")
        
        self.recovery.handle_calibration_error(error, 1, 3, {"session_id": "session1"})
        self.recovery.handle_calibration_error(error, 1, 3, {"session_id": "session2"})
        
        assert len(self.recovery.get_retry_history("session1")) == 1
        assert len(self.recovery.get_retry_history("session2")) == 1
        
        # Clear all history
        self.recovery.clear_retry_history()
        
        assert len(self.recovery.get_retry_history("session1")) == 0
        assert len(self.recovery.get_retry_history("session2")) == 0


class TestCalibrationError:
    """Test the CalibrationError class."""
    
    def test_calibration_error_creation(self):
        """Test creating calibration errors."""
        error = CalibrationError(
            message="Test error",
            error_type=CalibrationErrorType.SIGNAL_QUALITY,
            device_id=1,
            recovery_hints=["Try again"],
            can_retry=True
        )
        
        assert error.message == "Test error"
        assert error.error_type == CalibrationErrorType.SIGNAL_QUALITY
        assert error.device_id == 1
        assert error.recovery_hints == ["Try again"]
        assert error.can_retry is True
        
    def test_calibration_error_defaults(self):
        """Test default values for calibration errors."""
        error = CalibrationError(
            message="Test error",
            error_type=CalibrationErrorType.UNKNOWN
        )
        
        assert error.device_id is None
        assert error.original_exception is None
        assert error.recovery_hints == []
        assert error.can_retry is True
        assert error.suggested_parameters is None


class TestParameterAdjustmentStrategy:
    """Test the ParameterAdjustmentStrategy class."""
    
    def test_default_strategy(self):
        """Test default parameter adjustment strategy."""
        strategy = ParameterAdjustmentStrategy()
        
        assert len(strategy.sensitivity_adjustments) > 0
        assert len(strategy.debounce_adjustments) > 0
        assert strategy.target_press_tolerance == 0.2
        assert strategy.signal_quality_threshold == 0.3
        
    def test_custom_strategy(self):
        """Test custom parameter adjustment strategy."""
        strategy = ParameterAdjustmentStrategy(
            sensitivity_adjustments=[1.0, 0.5, 2.0],
            debounce_adjustments=[0, 10, -10],
            target_press_tolerance=0.1,
            signal_quality_threshold=0.5
        )
        
        assert strategy.sensitivity_adjustments == [1.0, 0.5, 2.0]
        assert strategy.debounce_adjustments == [0, 10, -10]
        assert strategy.target_press_tolerance == 0.1
        assert strategy.signal_quality_threshold == 0.5


class TestCalibrationRetryStrategy:
    """Test the CalibrationRetryStrategy class."""
    
    def test_default_strategy(self):
        """Test default retry strategy."""
        strategy = CalibrationRetryStrategy()
        
        assert strategy.max_attempts == 3
        assert strategy.device_fallback_enabled is True
        assert strategy.parameter_adjustment_enabled is True
        assert strategy.timeout_per_attempt == 30.0
        assert strategy.backoff_multiplier == 1.5
        
    def test_custom_strategy(self):
        """Test custom retry strategy."""
        strategy = CalibrationRetryStrategy(
            max_attempts=5,
            device_fallback_enabled=False,
            parameter_adjustment_enabled=False,
            timeout_per_attempt=60.0,
            backoff_multiplier=2.0
        )
        
        assert strategy.max_attempts == 5
        assert strategy.device_fallback_enabled is False
        assert strategy.parameter_adjustment_enabled is False
        assert strategy.timeout_per_attempt == 60.0
        assert strategy.backoff_multiplier == 2.0