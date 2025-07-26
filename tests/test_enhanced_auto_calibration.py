"""Tests for enhanced auto-calibration with error recovery."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock, call
import time

from switch_interface.enhanced_auto_calibration import (
    EnhancedAutoCalibrator,
    EnhancedCalibResult,
    calibrate_with_recovery
)
from switch_interface.calibration_error_recovery import (
    CalibrationRetryStrategy,
    CalibrationError,
    CalibrationErrorType
)
from switch_interface.audio_device_manager import AudioDeviceManager, AudioDeviceError
from switch_interface.auto_calibration import CalibResult


class TestEnhancedCalibResult:
    """Test the EnhancedCalibResult dataclass."""
    
    def test_enhanced_calib_result_creation(self):
        """Test creating enhanced calibration results."""
        result = EnhancedCalibResult(
            events=[1000, 2000, 3000],
            upper_offset=-0.1,
            lower_offset=-0.2,
            debounce_ms=20,
            samplerate=44100,
            confidence_score=0.85,
            signal_quality="good",
            retry_count=1,
            device_used=0,
            device_mode="auto",
            recommendations=["Test recommendation"]
        )
        
        assert result.events == [1000, 2000, 3000]
        assert result.confidence_score == 0.85
        assert result.signal_quality == "good"
        assert result.retry_count == 1
        assert result.device_used == 0
        assert result.device_mode == "auto"
        assert result.recommendations == ["Test recommendation"]
        assert result.recovery_applied is False  # Default value
        
    def test_enhanced_calib_result_defaults(self):
        """Test default values for enhanced calibration results."""
        result = EnhancedCalibResult(
            events=[],
            upper_offset=0.0,
            lower_offset=0.0,
            debounce_ms=20,
            samplerate=44100
        )
        
        assert result.confidence_score == 0.0
        assert result.signal_quality == "unknown"
        assert result.retry_count == 0
        assert result.device_used is None
        assert result.device_mode is None
        assert result.recommendations == []
        assert result.recovery_applied is False
        assert result.session_id is not None  # Should have a UUID


class TestEnhancedAutoCalibrator:
    """Test the EnhancedAutoCalibrator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.audio_manager = Mock(spec=AudioDeviceManager)
        self.calibrator = EnhancedAutoCalibrator(self.audio_manager)
        
        # Create sample audio data
        self.sample_rate = 44100
        self.samples = np.random.normal(0, 0.1, self.sample_rate)  # 1 second of audio
        
    @patch('switch_interface.enhanced_auto_calibration.calibrate')
    def test_calibrate_with_feedback_success_first_attempt(self, mock_calibrate):
        """Test successful calibration on first attempt."""
        # Mock successful calibration
        mock_result = CalibResult(
            events=[1000, 2000, 3000],
            upper_offset=-0.1,
            lower_offset=-0.2,
            debounce_ms=20,
            samplerate=44100,
            baseline_std=0.01,
            min_gap=0.5,
            calib_ok=True
        )
        mock_calibrate.return_value = mock_result
        
        # Mock validation to pass
        self.calibrator.error_recovery.validate_calibration_quality = Mock(return_value=(True, []))
        
        # Mock progress callback
        progress_callback = Mock()
        
        result = self.calibrator.calibrate_with_feedback(
            samples=self.samples,
            fs=self.sample_rate,
            device=0,
            target_presses=3,
            progress_callback=progress_callback,
            verbose=False
        )
        
        # Verify result
        assert isinstance(result, EnhancedCalibResult)
        assert result.calib_ok is True
        assert result.retry_count == 0
        assert result.device_used == 0
        assert result.recovery_applied is False
        assert result.confidence_score > 0
        
        # Verify progress callback was called
        progress_callback.assert_has_calls([
            call("Starting calibration...", 0.0),
            call("Calibration attempt 1/3", 0.0),
            call("Calibration completed successfully", 1.0)
        ])
        
        # Verify calibrate was called with correct parameters
        mock_calibrate.assert_called_once_with(
            samples=self.samples,
            fs=self.sample_rate,
            target_presses=3,
            verbose=False
        )
        
    @patch('switch_interface.enhanced_auto_calibration.calibrate')
    def test_calibrate_with_feedback_retry_on_validation_failure(self, mock_calibrate):
        """Test retry when calibration validation fails."""
        # Mock calibration that passes basic checks but fails validation
        mock_result = CalibResult(
            events=[1000],  # Only one event - will fail validation
            upper_offset=-0.01,
            lower_offset=-0.02,
            debounce_ms=20,
            samplerate=44100,
            baseline_std=0.1,  # High noise
            min_gap=float('inf'),
            calib_ok=True
        )
        mock_calibrate.return_value = mock_result
        
        # Mock validation to fail first time, succeed second time
        validation_results = [(False, ["Poor signal quality"]), (True, [])]
        self.calibrator.error_recovery.validate_calibration_quality = Mock(side_effect=validation_results)
        
        # Mock error recovery
        mock_error = CalibrationError(
            "Validation failed",
            CalibrationErrorType.VALIDATION_FAILURE,
            can_retry=True,
            suggested_parameters={"quality_threshold": 0.2}
        )
        self.calibrator.error_recovery.handle_calibration_error = Mock(
            return_value=(True, mock_error)
        )
        
        result = self.calibrator.calibrate_with_feedback(
            samples=self.samples,
            fs=self.sample_rate,
            device=0,
            target_presses=3
        )
        
        # Should succeed on second attempt
        assert result.calib_ok is True
        assert result.retry_count == 1
        assert result.recovery_applied is True
        
        # Verify calibrate was called twice
        assert mock_calibrate.call_count == 2
        
    @patch('switch_interface.enhanced_auto_calibration.calibrate')
    def test_calibrate_with_feedback_device_fallback(self, mock_calibrate):
        """Test device fallback on device access error."""
        # Mock calibration to fail with device error first, succeed with fallback
        mock_calibrate.side_effect = [
            AudioDeviceError("Device access denied", device_id=0, error_type="access"),
            CalibResult(
                events=[1000, 2000, 3000],
                upper_offset=-0.1,
                lower_offset=-0.2,
                debounce_ms=20,
                samplerate=44100,
                baseline_std=0.01,
                min_gap=0.5,
                calib_ok=True
            )
        ]
        
        # Mock validation to pass
        self.calibrator.error_recovery.validate_calibration_quality = Mock(return_value=(True, []))
        
        # Mock error recovery for device fallback
        device_error = CalibrationError(
            "Device access denied",
            CalibrationErrorType.DEVICE_ACCESS,
            device_id=0,
            can_retry=True
        )
        self.calibrator.error_recovery.handle_calibration_error = Mock(
            return_value=(True, device_error)
        )
        
        # Mock device fallback
        self.calibrator.error_recovery.try_device_fallback = Mock(
            return_value=(1, None, "shared")  # Fallback to device 1 in shared mode
        )
        
        result = self.calibrator.calibrate_with_feedback(
            samples=self.samples,
            fs=self.sample_rate,
            device=0,
            target_presses=3
        )
        
        # Should succeed with fallback device
        assert result.calib_ok is True
        assert result.retry_count == 1
        assert result.device_used == 1
        assert result.device_mode == "shared"
        assert result.recovery_applied is True
        
        # Verify device fallback was attempted
        self.calibrator.error_recovery.try_device_fallback.assert_called_once()
        
    @patch('switch_interface.enhanced_auto_calibration.calibrate')
    def test_calibrate_with_feedback_max_retries_exceeded(self, mock_calibrate):
        """Test behavior when max retries are exceeded."""
        # Mock calibration to always fail
        mock_calibrate.side_effect = Exception("Persistent calibration failure")
        
        # Mock error recovery to allow retries
        mock_error = CalibrationError(
            "Persistent failure",
            CalibrationErrorType.SIGNAL_QUALITY,
            can_retry=True
        )
        self.calibrator.error_recovery.handle_calibration_error = Mock(
            return_value=(True, mock_error)
        )
        
        # Mock improvement suggestions
        self.calibrator.error_recovery.suggest_improvements = Mock(
            return_value=["Try a different microphone", "Reduce background noise"]
        )
        
        retry_strategy = CalibrationRetryStrategy(max_attempts=2)
        
        result = self.calibrator.calibrate_with_feedback(
            samples=self.samples,
            fs=self.sample_rate,
            device=0,
            target_presses=3,
            retry_strategy=retry_strategy
        )
        
        # Should fail after max attempts
        assert result.calib_ok is False
        assert result.retry_count == 2
        assert result.recovery_applied is True
        assert len(result.recommendations) > 0
        
        # Verify calibrate was called max_attempts times
        assert mock_calibrate.call_count == 2
        
    def test_assess_signal_quality(self):
        """Test signal quality assessment."""
        assert self.calibrator._assess_signal_quality(0.9) == "excellent"
        assert self.calibrator._assess_signal_quality(0.7) == "good"
        assert self.calibrator._assess_signal_quality(0.5) == "fair"
        assert self.calibrator._assess_signal_quality(0.3) == "poor"
        
    def test_analyze_signal_quality(self):
        """Test detailed signal quality analysis."""
        # Create test signal with known characteristics
        test_signal = np.concatenate([
            np.random.normal(0, 0.01, 1000),  # Low noise baseline
            np.random.normal(-0.2, 0.02, 100),  # Switch press simulation
            np.random.normal(0, 0.01, 1000)   # Return to baseline
        ])
        
        analysis = self.calibrator.analyze_signal_quality(test_signal, 44100)
        
        # Verify analysis contains expected keys
        expected_keys = [
            "signal_range", "signal_mean", "signal_std", "noise_estimate",
            "snr_estimate", "clipping_ratio", "dc_offset", "sample_rate",
            "duration", "issues", "overall_quality"
        ]
        
        for key in expected_keys:
            assert key in analysis
            
        # Verify reasonable values
        assert analysis["sample_rate"] == 44100
        assert analysis["duration"] > 0
        assert analysis["signal_range"] > 0
        assert analysis["snr_estimate"] > 0
        assert 0 <= analysis["clipping_ratio"] <= 1
        
    def test_analyze_signal_quality_with_issues(self):
        """Test signal quality analysis with various issues."""
        # Create problematic signal
        problematic_signal = np.concatenate([
            np.full(500, 0.98),  # Clipping
            np.random.normal(0.2, 0.2, 500),  # DC offset + noise
            np.full(500, 0.001)  # Very low amplitude
        ])
        
        analysis = self.calibrator.analyze_signal_quality(problematic_signal, 44100)
        
        # Should detect multiple issues
        assert len(analysis["issues"]) > 0
        assert analysis["overall_quality"] == "poor"
        
        # Check for specific issues
        issues_text = " ".join(analysis["issues"])
        assert "clipping" in issues_text.lower() or "amplitude" in issues_text.lower()
        
    @patch('switch_interface.enhanced_auto_calibration.calibrate')
    def test_create_enhanced_result(self, mock_calibrate):
        """Test creation of enhanced results from basic results."""
        base_result = CalibResult(
            events=[1000, 2000, 3000],
            upper_offset=-0.1,
            lower_offset=-0.2,
            debounce_ms=20,
            samplerate=44100,
            baseline_std=0.01,
            min_gap=0.5,
            calib_ok=True
        )
        
        start_time = time.time()
        enhanced_result = self.calibrator._create_enhanced_result(
            base_result=base_result,
            session_id="test_session",
            attempt=2,
            device_used=1,
            device_mode="shared",
            samples=self.samples,
            start_time=start_time,
            recovery_applied=True
        )
        
        # Verify enhanced result properties
        assert enhanced_result.events == base_result.events
        assert enhanced_result.upper_offset == base_result.upper_offset
        assert enhanced_result.lower_offset == base_result.lower_offset
        assert enhanced_result.session_id == "test_session"
        assert enhanced_result.retry_count == 1  # attempt - 1
        assert enhanced_result.device_used == 1
        assert enhanced_result.device_mode == "shared"
        assert enhanced_result.recovery_applied is True
        assert enhanced_result.confidence_score > 0
        assert enhanced_result.signal_quality in ["excellent", "good", "fair", "poor"]
        assert enhanced_result.calibration_duration > 0
        
    def test_create_failure_result(self):
        """Test creation of failure results."""
        error = Exception("Test calibration failure")
        start_time = time.time()
        
        # Mock improvement suggestions
        self.calibrator.error_recovery.suggest_improvements = Mock(
            return_value=["Try a different device", "Check connections"]
        )
        
        failure_result = self.calibrator._create_failure_result(
            error=error,
            session_id="test_session",
            max_attempts=3,
            device_used=0,
            device_mode="auto",
            start_time=start_time
        )
        
        # Verify failure result properties
        assert failure_result.calib_ok is False
        assert failure_result.confidence_score == 0.0
        assert failure_result.signal_quality == "poor"
        assert failure_result.retry_count == 3
        assert failure_result.device_used == 0
        assert failure_result.device_mode == "auto"
        assert failure_result.recovery_applied is True
        assert len(failure_result.recommendations) > 0
        assert failure_result.calibration_duration > 0


class TestCalibrationRetryStrategy:
    """Test the CalibrationRetryStrategy integration."""
    
    def test_custom_retry_strategy(self):
        """Test using custom retry strategy."""
        audio_manager = Mock(spec=AudioDeviceManager)
        calibrator = EnhancedAutoCalibrator(audio_manager)
        
        custom_strategy = CalibrationRetryStrategy(
            max_attempts=5,
            device_fallback_enabled=False,
            parameter_adjustment_enabled=False,
            timeout_per_attempt=60.0,
            backoff_multiplier=2.0,
            min_backoff_delay=2.0,
            max_backoff_delay=30.0
        )
        
        # Mock calibration to fail consistently
        with patch('switch_interface.enhanced_auto_calibration.calibrate') as mock_calibrate:
            mock_calibrate.side_effect = Exception("Persistent failure")
            
            # Mock error recovery
            mock_error = CalibrationError(
                "Test failure",
                CalibrationErrorType.SIGNAL_QUALITY,
                can_retry=True
            )
            calibrator.error_recovery.handle_calibration_error = Mock(
                return_value=(True, mock_error)
            )
            calibrator.error_recovery.suggest_improvements = Mock(return_value=[])
            
            samples = np.random.normal(0, 0.1, 44100)
            
            result = calibrator.calibrate_with_feedback(
                samples=samples,
                fs=44100,
                retry_strategy=custom_strategy
            )
            
            # Should fail after custom max attempts
            assert result.calib_ok is False
            assert result.retry_count == 5
            assert mock_calibrate.call_count == 5


class TestConvenienceFunction:
    """Test the calibrate_with_recovery convenience function."""
    
    @patch('switch_interface.enhanced_auto_calibration.EnhancedAutoCalibrator')
    def test_calibrate_with_recovery(self, mock_calibrator_class):
        """Test the convenience function."""
        # Mock calibrator instance
        mock_calibrator = Mock()
        mock_result = EnhancedCalibResult(
            events=[1000, 2000],
            upper_offset=-0.1,
            lower_offset=-0.2,
            debounce_ms=20,
            samplerate=44100,
            calib_ok=True
        )
        mock_calibrator.calibrate_with_feedback.return_value = mock_result
        mock_calibrator_class.return_value = mock_calibrator
        
        # Test data
        samples = np.random.normal(0, 0.1, 44100)
        progress_callback = Mock()
        
        result = calibrate_with_recovery(
            samples=samples,
            fs=44100,
            device=1,
            target_presses=5,
            progress_callback=progress_callback,
            max_retries=4,
            verbose=True
        )
        
        # Verify calibrator was created and called correctly
        mock_calibrator_class.assert_called_once()
        mock_calibrator.calibrate_with_feedback.assert_called_once()
        
        call_args = mock_calibrator.calibrate_with_feedback.call_args
        assert np.array_equal(call_args[1]["samples"], samples)
        assert call_args[1]["fs"] == 44100
        assert call_args[1]["device"] == 1
        assert call_args[1]["target_presses"] == 5
        assert call_args[1]["progress_callback"] == progress_callback
        assert call_args[1]["verbose"] is True
        
        # Verify retry strategy was configured
        retry_strategy = call_args[1]["retry_strategy"]
        assert retry_strategy.max_attempts == 4
        
        # Verify result
        assert result == mock_result


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def setup_method(self):
        """Set up integration test fixtures."""
        self.audio_manager = Mock(spec=AudioDeviceManager)
        self.calibrator = EnhancedAutoCalibrator(self.audio_manager)
        self.samples = np.random.normal(0, 0.1, 44100)
        
    @patch('switch_interface.enhanced_auto_calibration.calibrate')
    @patch('switch_interface.enhanced_auto_calibration.time.sleep')  # Speed up tests
    def test_full_recovery_scenario(self, mock_sleep, mock_calibrate):
        """Test a complete recovery scenario with multiple failure types."""
        # Simulate sequence: device error -> signal error -> success
        mock_calibrate.side_effect = [
            AudioDeviceError("Device busy", device_id=0, error_type="access"),
            Exception("Poor signal quality"),
            CalibResult(
                events=[1000, 2000, 3000],
                upper_offset=-0.1,
                lower_offset=-0.2,
                debounce_ms=20,
                samplerate=44100,
                baseline_std=0.01,
                min_gap=0.5,
                calib_ok=True
            )
        ]
        
        # Mock validation to pass on final attempt
        validation_results = [(True, [])]  # Only called once (on success)
        self.calibrator.error_recovery.validate_calibration_quality = Mock(side_effect=validation_results)
        
        # Mock error recovery responses
        device_error = CalibrationError(
            "Device busy", CalibrationErrorType.DEVICE_ACCESS, can_retry=True
        )
        signal_error = CalibrationError(
            "Poor signal", CalibrationErrorType.SIGNAL_QUALITY, 
            can_retry=True, suggested_parameters={"sensitivity_factor": 0.8}
        )
        
        self.calibrator.error_recovery.handle_calibration_error = Mock(
            side_effect=[(True, device_error), (True, signal_error)]
        )
        
        # Mock device fallback
        self.calibrator.error_recovery.try_device_fallback = Mock(
            return_value=(1, None, "shared")
        )
        
        # Mock parameter adjustment
        self.calibrator.error_recovery.adjust_calibration_parameters = Mock(
            return_value={"sensitivity_factor": 0.8, "target_presses": 3}
        )
        
        result = self.calibrator.calibrate_with_feedback(
            samples=self.samples,
            fs=44100,
            device=0,
            target_presses=3
        )
        
        # Should succeed after recovery
        assert result.calib_ok is True
        assert result.retry_count == 2
        assert result.device_used == 1
        assert result.device_mode == "shared"
        assert result.recovery_applied is True
        
        # Verify all recovery mechanisms were used
        self.calibrator.error_recovery.try_device_fallback.assert_called_once()
        self.calibrator.error_recovery.adjust_calibration_parameters.assert_called_once()
        
        # Verify backoff delays were applied
        assert mock_sleep.call_count == 2  # Two retry delays
        
    @patch('switch_interface.enhanced_auto_calibration.calibrate')
    def test_hardware_failure_no_retry(self, mock_calibrate):
        """Test that hardware failures don't trigger retries."""
        # Simulate hardware failure
        mock_calibrate.side_effect = Exception("Hardware connection failed")
        
        # Mock error recovery to categorize as hardware failure
        hardware_error = CalibrationError(
            "Hardware failure", CalibrationErrorType.HARDWARE_FAILURE, can_retry=False
        )
        self.calibrator.error_recovery.handle_calibration_error = Mock(
            return_value=(False, hardware_error)
        )
        
        # Mock improvement suggestions
        self.calibrator.error_recovery.suggest_improvements = Mock(
            return_value=["Check cable connections", "Try a different switch"]
        )
        
        result = self.calibrator.calibrate_with_feedback(
            samples=self.samples,
            fs=44100,
            device=0,
            target_presses=3
        )
        
        # Should fail immediately without retries
        assert result.calib_ok is False
        assert result.retry_count == 1  # Only one attempt
        assert len(result.recommendations) > 0
        
        # Verify calibrate was only called once
        assert mock_calibrate.call_count == 1