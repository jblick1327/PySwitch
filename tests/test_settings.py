"""Tests for the unified configuration system."""
import json
import tempfile
from pathlib import Path

import pytest

from switch_interface import settings


class TestSettings:
    """Test the Settings dataclass and its components."""

    def test_default_settings(self):
        """Test default settings values."""
        cfg = settings.Settings()
        
        # App defaults
        assert cfg.app.scan_interval == 0.6
        assert cfg.app.layout == "qwerty_full.json"
        assert cfg.app.row_column_scan is False
        assert cfg.app.calibration_complete is False
        assert cfg.app.fallback_mode is False
        assert cfg.app.scan_preset == "medium"
        
        # Calibration defaults
        assert cfg.calibration.upper_offset == -0.2
        assert cfg.calibration.lower_offset == -0.5
        assert cfg.calibration.samplerate == 44_100
        assert cfg.calibration.blocksize == 256
        assert cfg.calibration.debounce_ms == 40
        
        # Audio defaults
        assert cfg.audio.device is None
        assert cfg.audio.last_working_device is None
        assert cfg.audio.device_mode == "auto"

    def test_to_dict(self):
        """Test Settings.to_dict() conversion."""
        cfg = settings.Settings()
        cfg.app.scan_interval = 0.8
        cfg.audio.device = "test_device"
        
        data = cfg.to_dict()
        
        assert data["app"]["scan_interval"] == 0.8
        assert data["app"]["layout"] == "qwerty_full.json"
        assert data["calibration"]["upper_offset"] == -0.2
        assert data["audio"]["device"] == "test_device"
        assert data["audio"]["device_mode"] == "auto"

    def test_from_dict(self):
        """Test Settings.from_dict() creation."""
        data = {
            "app": {
                "scan_interval": 0.8,
                "layout": "custom.json",
                "calibration_complete": True,
            },
            "calibration": {
                "upper_offset": -0.3,
                "samplerate": 48_000,
            },
            "audio": {
                "device": "mic1",
                "device_mode": "shared",
            }
        }
        
        cfg = settings.Settings.from_dict(data)
        
        # Check provided values
        assert cfg.app.scan_interval == 0.8
        assert cfg.app.layout == "custom.json"
        assert cfg.app.calibration_complete is True
        assert cfg.calibration.upper_offset == -0.3
        assert cfg.calibration.samplerate == 48_000
        assert cfg.audio.device == "mic1"
        assert cfg.audio.device_mode == "shared"
        
        # Check defaults for missing values
        assert cfg.app.row_column_scan is False  # Default
        assert cfg.calibration.lower_offset == -0.5  # Default
        assert cfg.audio.last_working_device is None  # Default

    def test_from_dict_empty(self):
        """Test Settings.from_dict() with empty dict."""
        cfg = settings.Settings.from_dict({})
        
        # Should be same as default Settings
        default = settings.Settings()
        assert cfg.app.scan_interval == default.app.scan_interval
        assert cfg.calibration.samplerate == default.calibration.samplerate
        assert cfg.audio.device_mode == default.audio.device_mode

    def test_from_dict_partial(self):
        """Test Settings.from_dict() with partial data."""
        data = {
            "app": {"scan_interval": 1.0},
            "calibration": {},
            # Missing audio section entirely
        }
        
        cfg = settings.Settings.from_dict(data)
        
        assert cfg.app.scan_interval == 1.0
        assert cfg.app.layout == "qwerty_full.json"  # Default
        assert cfg.calibration.upper_offset == -0.2  # Default
        assert cfg.audio.device is None  # Default


class TestScanPresets:
    """Test scan preset functionality."""

    def test_scan_presets_exist(self):
        """Test that all expected scan presets exist."""
        expected = ["very_slow", "slow", "medium", "fast", "very_fast"]
        for preset in expected:
            assert preset in settings.SCAN_PRESETS
            assert isinstance(settings.SCAN_PRESETS[preset], float)

    def test_scan_preset_values(self):
        """Test that scan presets have reasonable values."""
        presets = settings.SCAN_PRESETS
        
        # Should be in ascending speed order
        assert presets["very_slow"] > presets["slow"]
        assert presets["slow"] > presets["medium"]
        assert presets["medium"] > presets["fast"]
        assert presets["fast"] > presets["very_fast"]
        
        # All should be positive
        for value in presets.values():
            assert value > 0

    def test_get_scan_interval_with_preset(self):
        """Test get_scan_interval() with preset values."""
        cfg = settings.Settings()
        
        cfg.app.scan_preset = "slow"
        assert settings.get_scan_interval(cfg) == settings.SCAN_PRESETS["slow"]
        
        cfg.app.scan_preset = "fast"
        assert settings.get_scan_interval(cfg) == settings.SCAN_PRESETS["fast"]

    def test_get_scan_interval_invalid_preset(self):
        """Test get_scan_interval() with invalid preset."""
        cfg = settings.Settings()
        cfg.app.scan_preset = "invalid_preset"
        
        # Should fall back to scan_interval
        assert settings.get_scan_interval(cfg) == cfg.app.scan_interval

    def test_get_scan_interval_empty_preset(self):
        """Test get_scan_interval() with empty preset."""
        cfg = settings.Settings()
        cfg.app.scan_preset = ""
        
        # Should fall back to scan_interval
        assert settings.get_scan_interval(cfg) == cfg.app.scan_interval


class TestSettingsIO:
    """Test settings load and save functionality."""

    def test_load_nonexistent_file(self):
        """Test loading when settings file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock CONFIG_FILE to point to temp directory
            original_config_file = settings.CONFIG_FILE
            settings.CONFIG_FILE = Path(temp_dir) / "nonexistent.json"
            
            try:
                cfg = settings.load()
                
                # Should return defaults
                assert cfg.app.scan_interval == 0.6
                assert cfg.app.layout == "qwerty_full.json"
                assert cfg.calibration.upper_offset == -0.2
            finally:
                settings.CONFIG_FILE = original_config_file

    def test_load_invalid_json(self):
        """Test loading with invalid JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "invalid.json"
            config_file.write_text("invalid json {")
            
            original_config_file = settings.CONFIG_FILE
            settings.CONFIG_FILE = config_file
            
            try:
                cfg = settings.load()
                
                # Should return defaults on error
                assert cfg.app.scan_interval == 0.6
                assert cfg.calibration.samplerate == 44_100
            finally:
                settings.CONFIG_FILE = original_config_file

    def test_save_and_load_roundtrip(self):
        """Test saving and loading settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_settings.json"
            
            original_config_file = settings.CONFIG_FILE
            settings.CONFIG_FILE = config_file
            
            try:
                # Create custom settings
                original_cfg = settings.Settings()
                original_cfg.app.scan_interval = 0.9
                original_cfg.app.layout = "test.json"
                original_cfg.app.calibration_complete = True
                original_cfg.calibration.upper_offset = -0.1
                original_cfg.audio.device = "test_mic"
                
                # Save
                settings.save(original_cfg)
                assert config_file.exists()
                
                # Load
                loaded_cfg = settings.load()
                
                # Verify all values match
                assert loaded_cfg.app.scan_interval == 0.9
                assert loaded_cfg.app.layout == "test.json"
                assert loaded_cfg.app.calibration_complete is True
                assert loaded_cfg.calibration.upper_offset == -0.1
                assert loaded_cfg.audio.device == "test_mic"
                
            finally:
                settings.CONFIG_FILE = original_config_file

    def test_save_creates_directory(self):
        """Test that save() creates directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "subdir" / "settings.json"
            
            original_config_file = settings.CONFIG_FILE
            settings.CONFIG_FILE = config_file
            
            try:
                cfg = settings.Settings()
                settings.save(cfg)
                
                assert config_file.exists()
                assert config_file.parent.exists()
                
            finally:
                settings.CONFIG_FILE = original_config_file

    def test_load_partial_file(self):
        """Test loading file with only some settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "partial.json"
            
            # Write partial settings
            partial_data = {
                "app": {"scan_interval": 1.5},
                "calibration": {"samplerate": 22_050}
                # Missing audio section
            }
            config_file.write_text(json.dumps(partial_data))
            
            original_config_file = settings.CONFIG_FILE
            settings.CONFIG_FILE = config_file
            
            try:
                cfg = settings.load()
                
                # Should have saved values
                assert cfg.app.scan_interval == 1.5
                assert cfg.calibration.samplerate == 22_050
                
                # Should have defaults for missing values
                assert cfg.app.layout == "qwerty_full.json"
                assert cfg.calibration.upper_offset == -0.2
                assert cfg.audio.device is None
                
            finally:
                settings.CONFIG_FILE = original_config_file


class TestBackwardCompatibility:
    """Test handling of various data formats."""

    def test_load_with_extra_fields(self):
        """Test loading file with extra unknown fields."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "extra_fields.json"
            
            data = {
                "app": {
                    "scan_interval": 0.7,
                    "unknown_field": "should_be_ignored"
                },
                "calibration": {"samplerate": 48000},
                "audio": {"device": "mic1"},
                "unknown_section": {"foo": "bar"}
            }
            config_file.write_text(json.dumps(data))
            
            original_config_file = settings.CONFIG_FILE
            settings.CONFIG_FILE = config_file
            
            try:
                cfg = settings.load()
                
                # Should load known fields correctly
                assert cfg.app.scan_interval == 0.7
                assert cfg.calibration.samplerate == 48000
                assert cfg.audio.device == "mic1"
                
                # Unknown fields are ignored (no error)
                
            finally:
                settings.CONFIG_FILE = original_config_file

    def test_load_with_wrong_types(self):
        """Test loading with wrong data types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "wrong_types.json"
            
            data = {
                "app": {
                    "scan_interval": "not_a_number",  # Wrong type
                    "calibration_complete": "yes"      # Should be bool
                },
                "calibration": {
                    "samplerate": "44100"  # Should be int
                }
            }
            config_file.write_text(json.dumps(data))
            
            original_config_file = settings.CONFIG_FILE
            settings.CONFIG_FILE = config_file
            
            try:
                cfg = settings.load()
                
                # Should use defaults for invalid types
                assert cfg.app.scan_interval == 0.6  # Default
                assert cfg.app.calibration_complete is False  # Default
                assert cfg.calibration.samplerate == 44_100  # Default
                
            finally:
                settings.CONFIG_FILE = original_config_file