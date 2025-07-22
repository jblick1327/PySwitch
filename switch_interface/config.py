from __future__ import annotations

import json
import os
from pathlib import Path
import logging
from tkinter import messagebox
from typing import Any, Dict, Optional

from appdirs import user_config_dir

CONFIG_DIR = Path(user_config_dir("switch_interface"))
CONFIG_FILE = CONFIG_DIR / "config.json"

SCAN_PRESETS = {
    "very_slow": 1.2,   # For users with severe motor difficulties
    "slow": 0.8,        # More accessible for new users
    "medium": 0.6,      # Better default timing - good for beginners
    "fast": 0.4,        # Still fast but not overwhelming
    "very_fast": 0.25   # For experienced users
}

DEFAULT_CONFIG = {
    "scan_interval": 0.6,  # Slower, more beginner-friendly timing
    "layout": "qwerty_full.json",  # Comprehensive QWERTY layout with all essential keys
    "row_column_scan": False,  # Linear scanning is easier for beginners
    "calibration_complete": False,
    "audio_device": None,  # Auto-detect best device
    "fallback_mode": False,  # Normal operation mode
    "scan_preset": "medium",  # Named preset for easier adjustment
}

# Configuration validation schema
CONFIG_SCHEMA = {
    "scan_interval": {"type": float, "min": 0.1, "max": 5.0, "default": 0.6},
    "layout": {"type": str, "default": "qwerty_full.json"},
    "row_column_scan": {"type": bool, "default": False},
    "calibration_complete": {"type": bool, "default": False},
    "audio_device": {"type": (str, type(None)), "default": None},
    "fallback_mode": {"type": bool, "default": False},
    "scan_preset": {"type": str, "default": "medium"},
}


def exists(path: Path = CONFIG_FILE) -> bool:
    return Path(path).exists()


def validate_config_value(key: str, value: Any) -> tuple[bool, Any]:
    """Validate a single configuration value and return (is_valid, corrected_value)."""
    if key not in CONFIG_SCHEMA:
        return False, CONFIG_SCHEMA.get(key, {}).get("default")
    
    schema = CONFIG_SCHEMA[key]
    expected_type = schema["type"]
    
    # Handle None values for optional fields
    if value is None and type(None) in (expected_type if isinstance(expected_type, tuple) else (expected_type,)):
        return True, value
    
    # Type validation
    if isinstance(expected_type, tuple):
        if not isinstance(value, expected_type):
            return False, schema["default"]
    else:
        if not isinstance(value, expected_type):
            return False, schema["default"]
    
    # Special validation for scan_preset
    if key == "scan_preset" and isinstance(value, str):
        if value.lower() not in SCAN_PRESETS:
            return False, schema["default"]
        return True, value.lower()
    
    # Range validation for numeric values
    if isinstance(value, (int, float)):
        if "min" in schema and value < schema["min"]:
            return False, schema["default"]
        if "max" in schema and value > schema["max"]:
            return False, schema["default"]
    
    return True, value


def validate_and_repair_config(config: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
    """Validate configuration and repair invalid values.
    
    Returns:
        tuple: (repaired_config, was_repaired)
    """
    repaired_config = {}
    was_repaired = False
    logger = logging.getLogger(__name__)
    
    # Validate and repair each expected key
    for key, schema in CONFIG_SCHEMA.items():
        if key in config:
            is_valid, corrected_value = validate_config_value(key, config[key])
            if not is_valid:
                logger.warning(f"Invalid config value for '{key}': {config[key]}, using default: {corrected_value}")
                was_repaired = True
            repaired_config[key] = corrected_value
        else:
            # Missing key, use default
            repaired_config[key] = schema["default"]
            if key in DEFAULT_CONFIG:  # Only log for keys that should exist
                logger.info(f"Missing config key '{key}', using default: {schema['default']}")
                was_repaired = True
    
    # Remove unknown keys
    for key in config:
        if key not in CONFIG_SCHEMA:
            logger.warning(f"Unknown config key '{key}' removed")
            was_repaired = True
    
    return repaired_config, was_repaired


def get_safe_defaults() -> Dict[str, Any]:
    """Return a safe default configuration that should always work."""
    return DEFAULT_CONFIG.copy()


def load(path: Path = CONFIG_FILE) -> dict:
    """Load configuration with validation and auto-repair."""
    logger = logging.getLogger(__name__)
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_config = json.load(f)
    except FileNotFoundError:
        logger.info(f"Config file not found at {path}, using defaults")
        return get_safe_defaults()
    except json.JSONDecodeError as exc:
        logger.error(f"Invalid JSON in config file {path}: {exc}")
        logger.info("Using safe defaults due to corrupted config file")
        return get_safe_defaults()
    except Exception as exc:
        logger.exception(f"Failed to load config: {path}")
        logger.info("Using safe defaults due to config loading error")
        return get_safe_defaults()
    
    # Validate and repair the loaded configuration
    repaired_config, was_repaired = validate_and_repair_config(raw_config)
    
    if was_repaired:
        logger.info("Configuration was repaired, saving corrected version")
        try:
            save(repaired_config, path)
        except Exception as exc:
            logger.warning(f"Failed to save repaired config: {exc}")
    
    return repaired_config


def save(cfg: dict, path: Path = CONFIG_FILE) -> None:
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f)


def get_scan_interval(preset: str) -> float:
    """Get scan interval for a named preset."""
    return SCAN_PRESETS.get(preset.lower(), SCAN_PRESETS["medium"])


def get_beginner_config() -> Dict[str, Any]:
    """Return configuration optimized for new users."""
    return {
        "scan_interval": 0.8,  # Slower for easier use
        "layout": "qwerty_full.json",  # Complete layout
        "row_column_scan": False,  # Simpler linear scanning
        "calibration_complete": False,
        "audio_device": None,
        "fallback_mode": False,
        "scan_preset": "slow",  # Slower preset for beginners
    }


def get_accessible_config() -> Dict[str, Any]:
    """Return configuration for users with severe motor difficulties."""
    return {
        "scan_interval": 1.2,  # Very slow for accessibility
        "layout": "simple_alphabet.json",  # Simplified layout
        "row_column_scan": False,  # Linear scanning
        "calibration_complete": False,
        "audio_device": None,
        "fallback_mode": False,
        "scan_preset": "very_slow",
    }


def apply_scan_preset(config: Dict[str, Any], preset: str) -> Dict[str, Any]:
    """Apply a scan preset to configuration."""
    if preset in SCAN_PRESETS:
        config = config.copy()
        config["scan_interval"] = SCAN_PRESETS[preset]
        config["scan_preset"] = preset
    return config


def validate_layout_exists(layout_name: str) -> str:
    """Validate that a layout file exists, return fallback if not."""
    from pathlib import Path
    import pkg_resources
    from .kb_layout_io import get_default_layout
    
    logger = logging.getLogger(__name__)
    
    # Check if layout exists in resources
    try:
        layout_path = f"switch_interface/resources/layouts/{layout_name}"
        if pkg_resources.resource_exists("switch_interface", f"resources/layouts/{layout_name}"):
            return layout_name
    except Exception:
        pass
    
    # Get the default layout using the new function
    try:
        default_layout = get_default_layout()
        if default_layout != layout_name:
            logger.warning(f"Layout '{layout_name}' not found, using default: {default_layout}")
        return default_layout
    except Exception as exc:
        logger.error(f"Error getting default layout: {exc}")
    
    # Fallback to hardcoded layouts if the function fails
    fallback_layouts = ["qwerty_full.json", "simple_alphabet.json", "pred_test.json", "basic_test.json"]
    
    for fallback in fallback_layouts:
        try:
            if pkg_resources.resource_exists("switch_interface", f"resources/layouts/{fallback}"):
                if fallback != layout_name:
                    logger.warning(f"Layout '{layout_name}' not found, using fallback: {fallback}")
                return fallback
        except Exception:
            continue
    
    # If no fallback found, return the original name and let the application handle it
    logger.error(f"No valid layout found, returning original: {layout_name}")
    return layout_name


def load_with_layout_validation(path: Path = CONFIG_FILE) -> dict:
    """Load configuration with layout validation."""
    config = load(path)
    
    # Validate layout exists and use fallback if necessary
    original_layout = config.get("layout", DEFAULT_CONFIG["layout"])
    validated_layout = validate_layout_exists(original_layout)
    
    if validated_layout != original_layout:
        config["layout"] = validated_layout
        # Save the corrected configuration
        try:
            save(config, path)
        except Exception as exc:
            logging.getLogger(__name__).warning(f"Failed to save layout correction: {exc}")
    
    return config
