"""Unified configuration system for PySwitch.

This module consolidates all configuration concerns into a single, type-safe system.
Replaces the fragmented config.py, calibration.py DetectorConfig, and scattered audio settings.
"""
from __future__ import annotations

import json
import os
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
        """Create Settings from dictionary."""
        app_data = data.get("app", {})
        calibration_data = data.get("calibration", {})
        audio_data = data.get("audio", {})

        return cls(
            app=AppSettings(
                scan_interval=app_data.get("scan_interval", 0.6),
                layout=app_data.get("layout", "qwerty_full.json"),
                row_column_scan=app_data.get("row_column_scan", False),
                calibration_complete=app_data.get("calibration_complete", False),
                fallback_mode=app_data.get("fallback_mode", False),
                scan_preset=app_data.get("scan_preset", "medium"),
            ),
            calibration=CalibrationSettings(
                upper_offset=calibration_data.get("upper_offset", -0.2),
                lower_offset=calibration_data.get("lower_offset", -0.5),
                samplerate=calibration_data.get("samplerate", 44_100),
                blocksize=calibration_data.get("blocksize", 256),
                debounce_ms=calibration_data.get("debounce_ms", 40),
            ),
            audio=AudioSettings(
                device=audio_data.get("device"),
                last_working_device=audio_data.get("last_working_device"),
                device_mode=audio_data.get("device_mode", "auto"),
            ),
        )


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
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(settings.to_dict(), f, indent=2)


def get_scan_interval(settings: Settings) -> float:
    """Get effective scan interval from settings."""
    if settings.app.scan_preset in SCAN_PRESETS:
        return SCAN_PRESETS[settings.app.scan_preset]
    return settings.app.scan_interval