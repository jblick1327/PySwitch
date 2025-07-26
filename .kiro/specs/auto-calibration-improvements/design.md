# Design Document

## Overview

This design improves the auto-calibration system for ablenet style switches by enhancing reliability, user feedback, and error recovery. The current auto-calibration implementation in `auto_calibration.py` provides a solid foundation with its data-driven approach, but needs improvements in user experience, error handling, and robustness.

The design focuses on three main areas:
1. **Enhanced Auto-Calibration Algorithm**: Improve the existing calibration logic with better signal analysis and validation
2. **Improved User Interface**: Provide real-time feedback during calibration with clear progress indicators
3. **Robust Error Recovery**: Implement comprehensive fallback strategies and error handling

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                Auto-Calibration System                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Enhanced        │  │ Real-time       │  │ Error        │ │
│  │ Calibration     │  │ Feedback UI     │  │ Recovery     │ │
│  │ Engine          │  │                 │  │ Manager      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Signal          │  │ Audio Device    │  │ Validation   │ │
│  │ Analyzer        │  │ Manager         │  │ Engine       │ │
│  │                 │  │ (existing)      │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Initialization**: User initiates auto-calibration from UI
2. **Device Setup**: Audio device manager finds working device with fallback
3. **Recording**: System records ablenet switch presses with real-time feedback
4. **Analysis**: Enhanced calibration engine analyzes signal and determines thresholds
5. **Validation**: Validation engine checks calibration quality
6. **Retry Logic**: If validation fails, system retries with adjusted parameters
7. **Completion**: Results are saved and user receives confirmation

## Components and Interfaces

### Enhanced Calibration Engine

Extends the existing `auto_calibration.py` module with:

```python
@dataclass
class EnhancedCalibResult(CalibResult):
    """Extended calibration result with quality metrics."""
    confidence_score: float  # 0.0 to 1.0
    signal_quality: str     # "excellent", "good", "fair", "poor"
    retry_count: int
    device_used: str | None
    recommendations: List[str]

class EnhancedAutoCalibrator:
    """Improved auto-calibration with better signal analysis."""
    
    def calibrate_with_feedback(
        self, 
        device: str | None = None,
        progress_callback: Callable[[str, float], None] = None,
        max_retries: int = 3
    ) -> EnhancedCalibResult:
        """Run auto-calibration with real-time feedback."""
        
    def analyze_signal_quality(self, samples: np.ndarray, fs: int) -> Dict[str, Any]:
        """Analyze signal quality and provide recommendations."""
        
    def validate_calibration_quality(self, result: CalibResult, samples: np.ndarray) -> bool:
        """Validate calibration results with enhanced checks."""
```

### Real-time Feedback UI

New UI component that provides live feedback during calibration:

```python
class CalibrationFeedbackDialog:
    """Real-time feedback dialog for auto-calibration."""
    
    def __init__(self, parent: tk.Widget):
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar()
        self.press_count_var = tk.IntVar()
        
    def update_progress(self, message: str, progress: float):
        """Update progress bar and status message."""
        
    def show_press_detected(self):
        """Visual feedback when switch press is detected."""
        
    def show_signal_quality(self, quality: str, recommendations: List[str]):
        """Display signal quality assessment."""
```

### Error Recovery Manager

Handles calibration failures with intelligent retry logic:

```python
class CalibrationErrorRecovery:
    """Manages error recovery during auto-calibration."""
    
    def handle_calibration_error(
        self, 
        error: Exception, 
        attempt: int, 
        max_attempts: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Handle calibration errors with recovery strategies."""
        
    def suggest_improvements(self, error_type: str, signal_data: np.ndarray) -> List[str]:
        """Provide specific suggestions based on error analysis."""
        
    def try_alternative_parameters(self, base_params: Dict) -> List[Dict]:
        """Generate alternative parameter sets for retry attempts."""
```

### Signal Analyzer

Enhanced signal analysis for better ablenet switch detection:

```python
class AblenetSignalAnalyzer:
    """Specialized signal analysis for ablenet switches."""
    
    def analyze_switch_characteristics(self, samples: np.ndarray, fs: int) -> Dict[str, float]:
        """Analyze ablenet switch signal characteristics."""
        
    def detect_noise_patterns(self, samples: np.ndarray) -> Dict[str, Any]:
        """Detect and characterize background noise."""
        
    def estimate_optimal_thresholds(self, samples: np.ndarray, fs: int) -> Tuple[float, float]:
        """Estimate optimal thresholds for ablenet switches."""
```

## Data Models

### Enhanced Calibration Configuration

```python
@dataclass
class EnhancedDetectorConfig(DetectorConfig):
    """Extended detector configuration with quality metrics."""
    confidence_score: float = 0.0
    signal_quality: str = "unknown"
    calibration_timestamp: float = 0.0
    device_info: Dict[str, Any] = field(default_factory=dict)
    retry_history: List[Dict[str, Any]] = field(default_factory=list)
```

### Calibration Session Data

```python
@dataclass
class CalibrationSession:
    """Tracks a complete calibration session."""
    session_id: str
    start_time: float
    device_attempts: List[str]
    parameter_attempts: List[Dict[str, Any]]
    final_result: Optional[EnhancedCalibResult]
    user_feedback: Optional[str]
```

## Error Handling

### Error Categories

1. **Device Errors**: Audio device access failures
   - Fallback to alternative devices using AudioDeviceManager
   - Clear error messages with device-specific guidance

2. **Signal Quality Errors**: Poor signal quality or excessive noise
   - Analyze signal characteristics and provide specific recommendations
   - Suggest physical setup improvements (microphone placement, switch connection)

3. **Detection Errors**: Unable to detect expected number of switch presses
   - Retry with adjusted sensitivity parameters
   - Provide guidance on switch pressing technique

4. **Validation Errors**: Calibration results fail quality checks
   - Automatic retry with alternative parameters
   - Option to accept lower-quality calibration with warning

### Recovery Strategies

1. **Parameter Adjustment**: Automatically adjust detection parameters based on signal analysis
2. **Device Fallback**: Try alternative audio devices if primary device fails
3. **Sensitivity Scaling**: Adjust threshold sensitivity based on detected signal strength
4. **Noise Filtering**: Apply additional noise filtering for noisy environments

## Testing Strategy

### Unit Tests

1. **Enhanced Calibration Engine Tests**
   - Test signal analysis algorithms with synthetic ablenet switch signals
   - Verify threshold calculation accuracy
   - Test validation logic with various signal qualities

2. **Error Recovery Tests**
   - Test fallback mechanisms with simulated device failures
   - Verify retry logic with different error conditions
   - Test parameter adjustment algorithms

3. **Signal Analysis Tests**
   - Test noise detection and filtering
   - Verify ablenet switch characteristic detection
   - Test signal quality assessment

### Integration Tests

1. **End-to-End Calibration Tests**
   - Test complete calibration workflow with real audio devices
   - Verify UI feedback and progress reporting
   - Test error recovery with actual device failures

2. **Device Compatibility Tests**
   - Test with various audio devices and sample rates
   - Verify fallback behavior across different hardware configurations
   - Test with different ablenet switch models

### User Experience Tests

1. **Feedback Clarity Tests**
   - Verify progress indicators are clear and accurate
   - Test error messages are actionable and helpful
   - Validate that recommendations improve success rates

2. **Reliability Tests**
   - Measure calibration success rates across different setups
   - Test consistency of calibration results
   - Verify false positive/negative rates meet requirements

## Implementation Notes

### Backward Compatibility

- Maintain compatibility with existing `DetectorConfig` format
- Extend rather than replace existing calibration functions
- Preserve existing manual calibration UI as fallback option

### Performance Considerations

- Cache signal analysis results to avoid redundant calculations
- Use efficient numpy operations for real-time signal processing
- Minimize UI update frequency to prevent performance issues

### Configuration Management

- Store enhanced calibration metadata alongside existing configuration
- Implement migration logic for existing calibration files
- Provide option to reset to factory defaults if calibration becomes corrupted