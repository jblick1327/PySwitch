"""Unified configuration system for PySwitch.

This module consolidates all configuration concerns into a single, type-safe system.
Replaces the fragmented config.py, calibration.py DetectorConfig, and scattered audio settings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from appdirs import user_config_dir

# Single configuration directory and file
CONFIG_DIR = Path(user_config_dir("pyswitch"))
CONFIG_FILE = CONFIG_DIR / "settings.json"


@dataclass
class AppSettings:
    """Application-level settings."""

    scan_interval: float = 0.6
    layout: str = "qwerty_full.json"
    row_column_scan: bool = False
    calibration_complete: bool = False
    fallback_mode: bool = False
    scan_preset: str = "medium"  # very_slow, slow, medium, fast, very_fast
    always_on_top: bool = False


@dataclass
class CalibrationSettings:
    """Switch detection calibration settings."""

    upper_offset: float = -0.2
    lower_offset: float = -0.5
    samplerate: int = 44_100
    blocksize: int = 256
    debounce_ms: int = 40


@dataclass
class AudioSettings:
    """Audio device and processing settings."""

    device: Optional[str] = None  # Device name/ID, None for auto-detect
    last_working_device: Optional[str] = None
    device_mode: str = "auto"  # auto, exclusive, shared


@dataclass
class Settings:
    """Unified configuration for PySwitch."""

    app: AppSettings = field(default_factory=AppSettings)
    calibration: CalibrationSettings = field(default_factory=CalibrationSettings)
    audio: AudioSettings = field(default_factory=AudioSettings)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "app": {
                "scan_interval": self.app.scan_interval,
                "layout": self.app.layout,
                "row_column_scan": self.app.row_column_scan,
                "calibration_complete": self.app.calibration_complete,
                "fallback_mode": self.app.fallback_mode,
                "scan_preset": self.app.scan_preset,
                "always_on_top": self.app.always_on_top,
            },
            "calibration": {
                "upper_offset": self.calibration.upper_offset,
                "lower_offset": self.calibration.lower_offset,
                "samplerate": self.calibration.samplerate,
                "blocksize": self.calibration.blocksize,
                "debounce_ms": self.calibration.debounce_ms,
            },
            "audio": {
                "device": self.audio.device,
                "last_working_device": self.audio.last_working_device,
                "device_mode": self.audio.device_mode,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Settings:
        """Create Settings from dictionary with type validation."""
        app_data = data.get("app", {})
        calibration_data = data.get("calibration", {})
        audio_data = data.get("audio", {})

        def safe_get(d: dict, key: str, default, expected_type):
            """Safely get value with type checking."""
            value = d.get(key, default)
            if not isinstance(value, expected_type):
                return default
            return value

        return cls(
            app=AppSettings(
                scan_interval=safe_get(app_data, "scan_interval", 0.6, (int, float)),
                layout=safe_get(app_data, "layout", "qwerty_full.json", str),
                row_column_scan=safe_get(app_data, "row_column_scan", False, bool),
                calibration_complete=safe_get(
                    app_data, "calibration_complete", False, bool
                ),
                fallback_mode=safe_get(app_data, "fallback_mode", False, bool),
                scan_preset=safe_get(app_data, "scan_preset", "medium", str),
                always_on_top=safe_get(app_data, "always_on_top", False, bool),
            ),
            calibration=CalibrationSettings(
                upper_offset=safe_get(
                    calibration_data, "upper_offset", -0.2, (int, float)
                ),
                lower_offset=safe_get(
                    calibration_data, "lower_offset", -0.5, (int, float)
                ),
                samplerate=safe_get(calibration_data, "samplerate", 44_100, int),
                blocksize=safe_get(calibration_data, "blocksize", 256, int),
                debounce_ms=safe_get(calibration_data, "debounce_ms", 40, int),
            ),
            audio=AudioSettings(
                device=(
                    audio_data.get("device")
                    if isinstance(audio_data.get("device"), (str, type(None)))
                    else None
                ),
                last_working_device=(
                    audio_data.get("last_working_device")
                    if isinstance(
                        audio_data.get("last_working_device"), (str, type(None))
                    )
                    else None
                ),
                device_mode=safe_get(audio_data, "device_mode", "auto", str),
            ),
        )

    def get(self, key: str, default=None):
        """Get a setting value, for backward compatibility with dict-like access."""
        if key == "always_on_top":
            return self.app.always_on_top
        # Add other mappings as needed
        return default


# Scan speed presets
SCAN_PRESETS = {
    "very_slow": 1.2,
    "slow": 0.8,
    "medium": 0.6,
    "fast": 0.4,
    "very_fast": 0.25,
}


def load() -> Settings:
    """Load settings from file, return defaults if file doesn't exist or is invalid."""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Settings.from_dict(data)
    except Exception:
        # Return defaults on any error - keep it simple
        pass

    return Settings()


def save(settings: Settings) -> None:
    """Save settings to file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings.to_dict(), f, indent=2)


def get_scan_interval(settings: Settings) -> float:
    """Get effective scan interval from settings."""
    if settings.app.scan_preset in SCAN_PRESETS:
        return SCAN_PRESETS[settings.app.scan_preset]
    return settings.app.scan_interval
