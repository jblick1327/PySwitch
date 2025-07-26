"""
Enhanced auto-calibration with error recovery and retry mechanisms.

This module extends the existing auto-calibration functionality with intelligent
error recovery, device fallback, and parameter adjustment strategies.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from .audio_device_manager import AudioDeviceManager, AudioDeviceMode
from .auto_calibration import CalibResult, calibrate
from .calibration_error_recovery import (
    CalibrationErrorRecovery,
    CalibrationError,
    CalibrationErrorType,
    CalibrationRetryStrategy
)

logger = logging.getLogger(__name__)

__all__ = [
    "EnhancedCalibResult",
    "EnhancedAutoCalibrator",
    "calibrate_with_recovery"
]


@dataclass
class EnhancedCalibResult(CalibResult):
    """Extended calibration result with quality metrics and recovery information."""
    confidence_score: float = 0.0
    signal_quality: str = "unknown"  # "excellent", "good", "fair", "poor"
    retry_count: int = 0
    device_used: Optional[int | str] = None
    device_mode: Optional[AudioDeviceMode] = None
    recommendations: List[str] = field(default_factory=list)
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    calibration_duration: float = 0.0
    recovery_applied: bool = False


class EnhancedAutoCalibrator:
    """Enhanced auto-calibration with error recovery and intelligent retry logic."""
    
    def __init__(self, audio_manager: Optional[AudioDeviceManager] = None):
        self.audio_manager = audio_manager or AudioDeviceManager()
        self.error_recovery = CalibrationErrorRecovery(self.audio_manager)
        
    def calibrate_with_feedback(
        self,
        samples: np.ndarray,
        fs: int,
        device: Optional[int | str] = None,
        target_presses: Optional[int] = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
        retry_strategy: Optional[CalibrationRetryStrategy] = None,
        verbose: bool = False
    ) -> EnhancedCalibResult:
        """Run auto-calibration with error recovery and real-time feedback.
        
        Args:
            samples: Audio samples to calibrate with
            fs: Sample rate
            device: Audio device to use (None for default)
            target_presses: Expected number of switch presses
            progress_callback: Optional callback for progress updates
            retry_strategy: Retry configuration
            verbose: Enable verbose logging
            
        Returns:
            Enhanced calibration result with recovery information
        """
        if retry_strategy is None:
            retry_strategy = CalibrationRetryStrategy()
            
        session_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Initialize progress callback
        if progress_callback:
            progress_callback("Starting calibration...", 0.0)
            
        # Base calibration parameters
        base_params = {
            "target_presses": target_presses,
            "verbose": verbose,
            "session_id": session_id
        }
        
        last_error = None
        device_used = device
        device_mode = "auto"
        
        for attempt in range(1, retry_strategy.max_attempts + 1):
            try:
                if progress_callback:
                    progress = (attempt - 1) / retry_strategy.max_attempts
                    progress_callback(f"Calibration attempt {attempt}/{retry_strategy.max_attempts}", progress)
                
                logger.info(f"Calibration attempt {attempt}/{retry_strategy.max_attempts} with device {device_used}")
                
                # Run basic calibration
                result = calibrate(
                    samples=samples,
                    fs=fs,
                    target_presses=target_presses,
                    verbose=verbose
                )
                
                # Validate calibration quality
                is_valid, validation_issues = self.error_recovery.validate_calibration_quality(
                    result, samples, quality_threshold=0.3
                )
                
                if is_valid:
                    # Success! Create enhanced result
                    enhanced_result = self._create_enhanced_result(
                        result, session_id, attempt, device_used, device_mode,
                        samples, start_time, recovery_applied=(attempt > 1)
                    )
                    
                    if progress_callback:
                        progress_callback("Calibration completed successfully", 1.0)
                        
                    logger.info(f"Calibration succeeded on attempt {attempt}")
                    return enhanced_result
                else:
                    # Validation failed, treat as calibration error
                    validation_error = Exception(f"Calibration validation failed: {'; '.join(validation_issues)}")
                    raise validation_error
                    
            except Exception as error:
                last_error = error
                
                # Handle the error with recovery logic
                context = {
                    "session_id": session_id,
                    "parameters": base_params,
                    "device_id": device_used,
                    "device_mode": device_mode,
                    "parameter_adjustment_enabled": retry_strategy.parameter_adjustment_enabled
                }
                
                should_retry, calib_error = self.error_recovery.handle_calibration_error(
                    error, attempt, retry_strategy.max_attempts, context
                )
                
                if not should_retry:
                    logger.error(f"Calibration failed permanently after {attempt} attempts")
                    break
                    
                # Apply recovery strategies
                if progress_callback:
                    progress_callback(f"Applying recovery strategies...", 0.5)
                    
                # Try device fallback if enabled and it's a device error
                if (retry_strategy.device_fallback_enabled and 
                    calib_error.error_type == CalibrationErrorType.DEVICE_ACCESS):
                    
                    fallback_device, fallback_error, fallback_mode = self.error_recovery.try_device_fallback(
                        current_device=device_used,
                        samplerate=fs,
                        preferred_mode=device_mode
                    )
                    
                    if fallback_device is not None:
                        device_used = fallback_device
                        device_mode = fallback_mode
                        logger.info(f"Switched to fallback device {device_used} in {device_mode} mode")
                        
                # Apply parameter adjustments if suggested
                if calib_error.suggested_parameters:
                    adjusted_params = self.error_recovery.adjust_calibration_parameters(
                        base_params, calib_error.suggested_parameters, attempt
                    )
                    base_params.update(adjusted_params)
                    logger.debug(f"Applied parameter adjustments: {calib_error.suggested_parameters}")
                    
                # Add backoff delay between attempts
                if attempt < retry_strategy.max_attempts:
                    delay = min(
                        retry_strategy.max_backoff_delay,
                        retry_strategy.min_backoff_delay * (retry_strategy.backoff_multiplier ** (attempt - 1))
                    )
                    logger.debug(f"Waiting {delay:.1f}s before retry")
                    time.sleep(delay)
        
        # All attempts failed, create failure result
        if progress_callback:
            progress_callback("Calibration failed", 1.0)
            
        return self._create_failure_result(
            last_error, session_id, retry_strategy.max_attempts, 
            device_used, device_mode, start_time
        )
    
    def _create_enhanced_result(
        self,
        base_result: CalibResult,
        session_id: str,
        attempt: int,
        device_used: Optional[int | str],
        device_mode: Optional[AudioDeviceMode],
        samples: np.ndarray,
        start_time: float,
        recovery_applied: bool = False
    ) -> EnhancedCalibResult:
        """Create an enhanced calibration result from a basic result."""
        
        # Calculate quality metrics
        confidence_score = self.error_recovery._calculate_quality_score(base_result, samples)
        signal_quality = self._assess_signal_quality(confidence_score)
        
        # Generate recommendations
        recommendations = []
        if confidence_score < 0.7:
            recommendations.extend([
                "Consider improving microphone positioning",
                "Reduce background noise if possible"
            ])
        if base_result.debounce_ms > 50:
            recommendations.append("Switch response may be inconsistent")
        if len(base_result.events) < 3:
            recommendations.append("More switch presses during calibration may improve accuracy")
            
        return EnhancedCalibResult(
            events=base_result.events,
            upper_offset=base_result.upper_offset,
            lower_offset=base_result.lower_offset,
            debounce_ms=base_result.debounce_ms,
            samplerate=base_result.samplerate,
            baseline_std=base_result.baseline_std,
            min_gap=base_result.min_gap,
            calib_ok=base_result.calib_ok,
            confidence_score=confidence_score,
            signal_quality=signal_quality,
            retry_count=attempt - 1,
            device_used=device_used,
            device_mode=device_mode,
            recommendations=recommendations,
            session_id=session_id,
            calibration_duration=time.time() - start_time,
            recovery_applied=recovery_applied
        )
    
    def _create_failure_result(
        self,
        error: Optional[Exception],
        session_id: str,
        max_attempts: int,
        device_used: Optional[int | str],
        device_mode: Optional[AudioDeviceMode],
        start_time: float
    ) -> EnhancedCalibResult:
        """Create a failure result when calibration cannot be completed."""
        
        # Get error-specific recommendations
        recommendations = []
        if error:
            error_type = CalibrationErrorType.UNKNOWN
            if "device" in str(error).lower():
                error_type = CalibrationErrorType.DEVICE_ACCESS
            elif "signal" in str(error).lower():
                error_type = CalibrationErrorType.SIGNAL_QUALITY
            elif "detection" in str(error).lower():
                error_type = CalibrationErrorType.DETECTION_FAILURE
                
            recommendations = self.error_recovery.suggest_improvements(error_type)
        
        return EnhancedCalibResult(
            events=[],
            upper_offset=0.0,
            lower_offset=0.0,
            debounce_ms=20,
            samplerate=44100,
            baseline_std=0.0,
            min_gap=float('inf'),
            calib_ok=False,
            confidence_score=0.0,
            signal_quality="poor",
            retry_count=max_attempts,
            device_used=device_used,
            device_mode=device_mode,
            recommendations=recommendations,
            session_id=session_id,
            calibration_duration=time.time() - start_time,
            recovery_applied=True
        )
    
    def _assess_signal_quality(self, confidence_score: float) -> str:
        """Assess signal quality based on confidence score."""
        if confidence_score >= 0.8:
            return "excellent"
        elif confidence_score >= 0.6:
            return "good"
        elif confidence_score >= 0.4:
            return "fair"
        else:
            return "poor"
    
    def analyze_signal_quality(self, samples: np.ndarray, fs: int) -> Dict[str, Any]:
        """Analyze signal quality and provide detailed metrics."""
        
        # Basic signal statistics
        signal_range = np.ptp(samples)
        signal_mean = np.mean(samples)
        signal_std = np.std(samples)
        
        # Check for clipping
        clipping_ratio = np.sum(np.abs(samples) > 0.95) / len(samples)
        
        # Estimate noise level (using quiet periods)
        # Simple approach: use lower 20% of absolute values as noise estimate
        sorted_abs = np.sort(np.abs(samples))
        noise_estimate = np.mean(sorted_abs[:int(0.2 * len(sorted_abs))])
        
        # Signal-to-noise ratio estimate
        signal_estimate = signal_range / 2  # Rough signal amplitude
        snr_estimate = signal_estimate / max(noise_estimate, 1e-6)
        
        # DC offset check
        dc_offset = abs(signal_mean)
        
        analysis = {
            "signal_range": float(signal_range),
            "signal_mean": float(signal_mean),
            "signal_std": float(signal_std),
            "noise_estimate": float(noise_estimate),
            "snr_estimate": float(snr_estimate),
            "clipping_ratio": float(clipping_ratio),
            "dc_offset": float(dc_offset),
            "sample_rate": fs,
            "duration": len(samples) / fs
        }
        
        # Generate quality assessment
        issues = []
        if signal_range < 0.01:
            issues.append("Very low signal amplitude")
        if signal_range > 0.8:
            issues.append("Very high signal amplitude")
        if clipping_ratio > 0.01:
            issues.append("Audio clipping detected")
        if snr_estimate < 3.0:
            issues.append("Poor signal-to-noise ratio")
        if dc_offset > 0.1:
            issues.append("Significant DC offset")
            
        analysis["issues"] = issues
        analysis["overall_quality"] = "good" if len(issues) == 0 else "poor"
        
        return analysis


def calibrate_with_recovery(
    samples: np.ndarray,
    fs: int,
    device: Optional[int | str] = None,
    target_presses: Optional[int] = None,
    progress_callback: Optional[Callable[[str, float], None]] = None,
    max_retries: int = 3,
    verbose: bool = False
) -> EnhancedCalibResult:
    """Convenience function for enhanced calibration with error recovery.
    
    Args:
        samples: Audio samples to calibrate with
        fs: Sample rate
        device: Audio device to use (None for default)
        target_presses: Expected number of switch presses
        progress_callback: Optional callback for progress updates
        max_retries: Maximum number of retry attempts
        verbose: Enable verbose logging
        
    Returns:
        Enhanced calibration result
    """
    calibrator = EnhancedAutoCalibrator()
    retry_strategy = CalibrationRetryStrategy(max_attempts=max_retries)
    
    return calibrator.calibrate_with_feedback(
        samples=samples,
        fs=fs,
        device=device,
        target_presses=target_presses,
        progress_callback=progress_callback,
        retry_strategy=retry_strategy,
        verbose=verbose
    )