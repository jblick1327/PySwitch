from switch_interface.compat import listen
from switch_interface.calibration import DetectorConfig


def test_legacy_listen_config(monkeypatch):
    captured = {}

    def dummy_listen(on_press, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("switch_interface.listener.listen", dummy_listen)
    cfg = DetectorConfig(
        upper_offset=-0.3,
        lower_offset=-0.7,
        samplerate=12,
        blocksize=5,
        debounce_ms=77,
        device="mic",
    )
    listen(lambda: None, cfg)
    assert captured == {
        "upper_offset": -0.3,
        "lower_offset": -0.7,
        "samplerate": 12,
        "blocksize": 5,
        "debounce_ms": 77,
        "device": "mic",
    }
