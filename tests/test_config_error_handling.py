import logging
import types
import sys
from switch_interface import config, calibration


def test_config_load_bad_json(tmp_path, monkeypatch, caplog):
    path = tmp_path / "cfg.json"
    path.write_text("{ bad json", encoding="utf-8")
    called = {}

    def _showerror(title, message, **kwargs):
        called["title"] = title
        called["message"] = message

    monkeypatch.setattr(
        config, "messagebox", types.SimpleNamespace(showerror=_showerror)
    )
    with caplog.at_level(logging.ERROR, logger=config.__name__):
        result = config.load(path=path)
    assert result == {}
    assert "Failed to load config" in caplog.text
    assert "delete" in called["message"].lower()
    assert str(path) in called["message"]


def test_calibration_load_bad_json(tmp_path, monkeypatch, caplog):
    sys.modules.setdefault("sounddevice", types.SimpleNamespace())
    path = tmp_path / "detector.json"
    path.write_text("{ bad json", encoding="utf-8")
    called = {}

    def _showerror(title, message, **kwargs):
        called["title"] = title
        called["message"] = message

    monkeypatch.setattr(
        calibration, "messagebox", types.SimpleNamespace(showerror=_showerror)
    )
    with caplog.at_level(logging.ERROR, logger=calibration.__name__):
        cfg = calibration.load_config(path=str(path))
    assert cfg == calibration.DetectorConfig()
    assert "Failed to load calibration config" in caplog.text
    assert "delete" in called["message"].lower()
    assert str(path) in called["message"]
