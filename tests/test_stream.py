import contextlib
import logging
import types

import switch_interface.audio.stream as stream
from switch_interface.listener import check_device


class DummyBackend(stream.InputBackend):
    def __init__(self, name, priority):
        self.name = name
        self.priority = priority

    def matches_hostapi(self, info):
        return False

    @contextlib.contextmanager
    def open(self, **kwargs):
        yield self.name

    def __repr__(self):
        return f"DummyBackend({self.name})"


def _setup(monkeypatch):
    sd_mod = types.SimpleNamespace(
        query_hostapis=lambda idx: {"name": "None"},
        default=types.SimpleNamespace(hostapi=0),
        PortAudioError=Exception,
    )
    monkeypatch.setattr(stream, "sd", sd_mod)

    b1 = DummyBackend("one", 10)
    b2 = DummyBackend("two", 1)
    monkeypatch.setattr(stream, "_BACKENDS", [b1, b2])
    monkeypatch.setattr(stream, "_BACKENDS_LOADED", True)
    return b1, b2


def test_select_backend_fallback(monkeypatch, caplog):
    _, b2 = _setup(monkeypatch)
    with caplog.at_level(logging.WARNING):
        chosen = stream._select_backend(None)
    assert chosen is b2
    assert "No matching audio back-end" in caplog.text


def test_check_device_uses_fallback(monkeypatch):
    _, b2 = _setup(monkeypatch)
    calls = []

    @contextlib.contextmanager
    def open_b(self, **kwargs):
        calls.append(True)
        yield "x"

    b2.open = types.MethodType(open_b, b2)
    check_device(samplerate=1, blocksize=1)
    assert calls
