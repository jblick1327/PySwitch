"""Tests for configuration validation and auto-repair functionality."""

import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from switch_interface import config


class TestConfigValidation:
    """Test configuration validation functions."""
    
    def test_validate_config_value_valid_float(self):
        """Test validation of valid float values."""
        is_valid, value = config.validate_config_value("scan_interval", 0.5)
        assert is_valid is True
        assert value == 0.5
    
    def test_validate_config_value_invalid_float_too_low(self):
        """Test validation of float value below minimum."""
        is_valid, value = config.validate_config_value("scan_interval", 0.05)
        assert is_valid is False
        assert value == 0.6  # default
    
    def test_validate_config_value_invalid_float_too_high(self):
        """Test validation of float value above maximum."""
        is_valid, value = config.validate_config_value("scan_interval", 10.0)
        assert is_valid is False
        assert value == 0.6  # default
    
    def test_validate_config_value_invalid_type(self):
        """Test validation of wrong type."""
        is_valid, value = config.validate_config_value("scan_interval", "invalid")
        assert is_valid is False
        assert value == 0.6  # default
    
    def test_validate_config_value_valid_string(self):
        """Test validation of valid string values."""
        is_valid, value = config.validate_config_value("layout", "test.json")
        assert is_valid is True
        assert value == "test.json"
    
    def test_validate_config_value_valid_bool(self):
        """Test validation of valid boolean values."""
        is_valid, value = config.validate_config_value("row_column_scan", True)
        assert is_valid is True
        assert value is True
    
    def test_validate_config_value_invalid_bool(self):
        """Test validation of invalid boolean values."""
        is_valid, value = config.validate_config_value("row_column_scan", "true")
        assert is_valid is False
        assert value is False  # default
    
    def test_validate_config_value_valid_none(self):
        """Test validation of None for optional fields."""
        is_valid, value = config.validate_config_value("audio_device", None)
        assert is_valid is True
        assert value is None
    
    def test_validate_config_value_unknown_key(self):
        """Test validation of unknown configuration key."""
        is_valid, value = config.validate_config_value("unknown_key", "value")
        assert is_valid is False
        assert value is None


class TestConfigRepair:
    """Test configuration repair functionality."""
    
    def test_validate_and_repair_config_valid(self):
        """Test repair of valid configuration."""
        valid_config = {
            "scan_interval": 0.5,
            "layout": "test.json",
            "row_column_scan": True,
            "calibration_complete": False,
            "audio_device": "test_device",
            "fallback_mode": False,
        }
        
        repaired, was_repaired = config.validate_and_repair_config(valid_config)
        assert was_repaired is False
        assert repaired == valid_config
    
    def test_validate_and_repair_config_invalid_values(self):
        """Test repair of configuration with invalid values."""
        invalid_config = {
            "scan_interval": "invalid",  # Should be float
            "layout": 123,  # Should be string
            "row_column_scan": "true",  # Should be bool
            "calibration_complete": 1,  # Should be bool
            "audio_device": 456,  # Should be string or None
            "fallback_mode": "false",  # Should be bool
        }
        
        repaired, was_repaired = config.validate_and_repair_config(invalid_config)
        assert was_repaired is True
        assert repaired["scan_interval"] == 0.6
        assert repaired["layout"] == "qwerty_full.json"
        assert repaired["row_column_scan"] is False
        assert repaired["calibration_complete"] is False
        assert repaired["audio_device"] is None
        assert repaired["fallback_mode"] is False
    
    def test_validate_and_repair_config_missing_keys(self):
        """Test repair of configuration with missing keys."""
        incomplete_config = {
            "scan_interval": 0.5,
            "layout": "test.json",
        }
        
        repaired, was_repaired = config.validate_and_repair_config(incomplete_config)
        assert was_repaired is True
        assert "row_column_scan" in repaired
        assert "calibration_complete" in repaired
        assert "audio_device" in repaired
        assert "fallback_mode" in repaired
        assert repaired["row_column_scan"] is False
        assert repaired["calibration_complete"] is False
        assert repaired["audio_device"] is None
        assert repaired["fallback_mode"] is False
    
    def test_validate_and_repair_config_unknown_keys(self):
        """Test repair of configuration with unknown keys."""
        config_with_unknown = {
            "scan_interval": 0.5,
            "layout": "test.json",
            "row_column_scan": False,
            "calibration_complete": False,
            "audio_device": None,
            "fallback_mode": False,
            "unknown_key": "should_be_removed",
            "another_unknown": 123,
        }
        
        repaired, was_repaired = config.validate_and_repair_config(config_with_unknown)
        assert was_repaired is True
        assert "unknown_key" not in repaired
        assert "another_unknown" not in repaired
        assert len(repaired) == len(config.CONFIG_SCHEMA)
    
    def test_validate_and_repair_config_empty(self):
        """Test repair of empty configuration."""
        empty_config = {}
        
        repaired, was_repaired = config.validate_and_repair_config(empty_config)
        assert was_repaired is True
        assert repaired == config.DEFAULT_CONFIG


class TestConfigLoading:
    """Test configuration loading with validation."""
    
    def test_load_nonexistent_file(self, tmp_path, caplog):
        """Test loading non-existent configuration file."""
        nonexistent_path = tmp_path / "nonexistent.json"
        
        with caplog.at_level(logging.INFO):
            result = config.load(nonexistent_path)
        
        assert result == config.DEFAULT_CONFIG
        assert "Config file not found" in caplog.text
    
    def test_load_invalid_json(self, tmp_path, caplog):
        """Test loading configuration file with invalid JSON."""
        invalid_json_path = tmp_path / "invalid.json"
        invalid_json_path.write_text("{ invalid json", encoding="utf-8")
        
        with caplog.at_level(logging.ERROR):
            result = config.load(invalid_json_path)
        
        assert result == config.DEFAULT_CONFIG
        assert "Invalid JSON in config file" in caplog.text
    
    def test_load_valid_config(self, tmp_path):
        """Test loading valid configuration file."""
        valid_config = {
            "scan_interval": 0.8,
            "layout": "custom.json",
            "row_column_scan": True,
            "calibration_complete": True,
            "audio_device": "test_device",
            "fallback_mode": True,
        }
        
        config_path = tmp_path / "valid.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(valid_config, f)
        
        result = config.load(config_path)
        assert result == valid_config
    
    def test_load_config_with_repair(self, tmp_path, caplog):
        """Test loading configuration that needs repair."""
        invalid_config = {
            "scan_interval": "invalid",
            "layout": "test.json",
            "unknown_key": "value",
        }
        
        config_path = tmp_path / "repair.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(invalid_config, f)
        
        with caplog.at_level(logging.INFO):
            result = config.load(config_path)
        
        assert result["scan_interval"] == 0.6  # repaired to default
        assert result["layout"] == "test.json"  # kept valid value
        assert "unknown_key" not in result  # removed unknown key
        assert "Configuration was repaired" in caplog.text
        
        # Check that repaired config was saved back
        with open(config_path, "r", encoding="utf-8") as f:
            saved_config = json.load(f)
        assert saved_config == result
    
    def test_load_config_repair_save_failure(self, tmp_path, caplog):
        """Test loading configuration when repair save fails."""
        invalid_config = {"scan_interval": "invalid"}
        
        config_path = tmp_path / "repair_fail.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(invalid_config, f)
        
        # Mock save to raise an exception
        with patch.object(config, 'save', side_effect=Exception("Save failed")):
            with caplog.at_level(logging.WARNING):
                result = config.load(config_path)
        
        assert result["scan_interval"] == 0.6  # still repaired
        assert "Failed to save repaired config" in caplog.text


class TestLayoutValidation:
    """Test layout validation functionality."""
    
    @patch('pkg_resources.resource_exists')
    def test_validate_layout_exists_valid(self, mock_resource_exists):
        """Test validation of existing layout."""
        mock_resource_exists.return_value = True
        
        result = config.validate_layout_exists("test.json")
        assert result == "test.json"
        mock_resource_exists.assert_called_with("switch_interface", "resources/layouts/test.json")
    
    @patch('pkg_resources.resource_exists')
    def test_validate_layout_exists_fallback(self, mock_resource_exists, caplog):
        """Test fallback when layout doesn't exist."""
        def mock_exists(package, resource):
            if "nonexistent.json" in resource:
                return False
            if "qwerty_full.json" in resource:
                return True
            return False
        
        mock_resource_exists.side_effect = mock_exists
        
        with caplog.at_level(logging.WARNING):
            result = config.validate_layout_exists("nonexistent.json")
        
        assert result == "qwerty_full.json"
        assert "Layout 'nonexistent.json' not found, using fallback: qwerty_full.json" in caplog.text
    
    @patch('pkg_resources.resource_exists')
    def test_validate_layout_exists_no_fallback(self, mock_resource_exists, caplog):
        """Test when no fallback layouts exist."""
        mock_resource_exists.return_value = False
        
        with caplog.at_level(logging.ERROR):
            result = config.validate_layout_exists("nonexistent.json")
        
        assert result == "nonexistent.json"
        assert "No valid layout found" in caplog.text
    
    @patch('pkg_resources.resource_exists')
    def test_load_with_layout_validation_valid(self, mock_resource_exists, tmp_path):
        """Test loading config with valid layout."""
        mock_resource_exists.return_value = True
        
        valid_config = config.DEFAULT_CONFIG.copy()
        valid_config["layout"] = "test.json"
        
        config_path = tmp_path / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(valid_config, f)
        
        result = config.load_with_layout_validation(config_path)
        assert result["layout"] == "test.json"
    
    @patch('pkg_resources.resource_exists')
    def test_load_with_layout_validation_fallback(self, mock_resource_exists, tmp_path):
        """Test loading config with invalid layout that needs fallback."""
        def mock_exists(package, resource):
            if "invalid.json" in resource:
                return False
            if "qwerty_full.json" in resource:
                return True
            return False
        
        mock_resource_exists.side_effect = mock_exists
        
        invalid_config = config.DEFAULT_CONFIG.copy()
        invalid_config["layout"] = "invalid.json"
        
        config_path = tmp_path / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(invalid_config, f)
        
        result = config.load_with_layout_validation(config_path)
        assert result["layout"] == "qwerty_full.json"
        
        # Check that corrected config was saved
        with open(config_path, "r", encoding="utf-8") as f:
            saved_config = json.load(f)
        assert saved_config["layout"] == "qwerty_full.json"


class TestSafeDefaults:
    """Test safe defaults functionality."""
    
    def test_get_safe_defaults(self):
        """Test that safe defaults returns expected configuration."""
        defaults = config.get_safe_defaults()
        
        assert defaults == config.DEFAULT_CONFIG
        assert defaults["scan_interval"] == 0.6
        assert defaults["layout"] == "qwerty_full.json"
        assert defaults["row_column_scan"] is False
        assert defaults["calibration_complete"] is False
        assert defaults["audio_device"] is None
        assert defaults["fallback_mode"] is False
        assert defaults["scan_preset"] == "medium"
    
    def test_get_safe_defaults_is_copy(self):
        """Test that safe defaults returns a copy, not reference."""
        defaults1 = config.get_safe_defaults()
        defaults2 = config.get_safe_defaults()
        
        defaults1["scan_interval"] = 999
        assert defaults2["scan_interval"] == 0.6  # Should not be affected


class TestBeginnerConfigurations:
    """Test beginner-friendly configuration functions."""
    
    def test_get_beginner_config(self):
        """Test beginner configuration has appropriate settings."""
        beginner_config = config.get_beginner_config()
        
        assert beginner_config["scan_interval"] == 0.8  # Slower for beginners
        assert beginner_config["layout"] == "qwerty_full.json"
        assert beginner_config["row_column_scan"] is False  # Simpler scanning
        assert beginner_config["scan_preset"] == "slow"
    
    def test_get_accessible_config(self):
        """Test accessible configuration for users with motor difficulties."""
        accessible_config = config.get_accessible_config()
        
        assert accessible_config["scan_interval"] == 1.2  # Very slow
        assert accessible_config["layout"] == "simple_alphabet.json"
        assert accessible_config["scan_preset"] == "very_slow"
    
    def test_apply_scan_preset_valid(self):
        """Test applying valid scan preset."""
        base_config = config.DEFAULT_CONFIG.copy()
        updated_config = config.apply_scan_preset(base_config, "slow")
        
        assert updated_config["scan_interval"] == 0.8
        assert updated_config["scan_preset"] == "slow"
        # Original config should not be modified
        assert base_config["scan_interval"] == 0.6
    
    def test_apply_scan_preset_invalid(self):
        """Test applying invalid scan preset."""
        base_config = config.DEFAULT_CONFIG.copy()
        updated_config = config.apply_scan_preset(base_config, "invalid")
        
        # Should return unchanged config
        assert updated_config == base_config
    
    def test_get_scan_interval_valid_preset(self):
        """Test getting scan interval for valid preset."""
        assert config.get_scan_interval("slow") == 0.8
        assert config.get_scan_interval("medium") == 0.6
        assert config.get_scan_interval("very_slow") == 1.2
    
    def test_get_scan_interval_invalid_preset(self):
        """Test getting scan interval for invalid preset returns default."""
        assert config.get_scan_interval("invalid") == 0.6  # medium default


class TestScanPresetValidation:
    """Test scan preset validation."""
    
    def test_validate_scan_preset_valid(self):
        """Test validation of valid scan preset."""
        is_valid, value = config.validate_config_value("scan_preset", "slow")
        assert is_valid is True
        assert value == "slow"
    
    def test_validate_scan_preset_valid_case_insensitive(self):
        """Test validation handles case insensitive presets."""
        is_valid, value = config.validate_config_value("scan_preset", "SLOW")
        assert is_valid is True
        assert value == "slow"  # Should be normalized to lowercase
    
    def test_validate_scan_preset_invalid(self):
        """Test validation of invalid scan preset."""
        is_valid, value = config.validate_config_value("scan_preset", "invalid")
        assert is_valid is False
        assert value == "medium"  # default
    
    def test_validate_scan_preset_wrong_type(self):
        """Test validation of wrong type for scan preset."""
        is_valid, value = config.validate_config_value("scan_preset", 123)
        assert is_valid is False
        assert value == "medium"  # default