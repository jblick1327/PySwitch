from __future__ import annotations

import contextlib
import sys
import threading
import types

import pytest


fake_sounddevice = types.ModuleType("sounddevice")


class _FakePortAudioError(Exception):
    pass


def _fake_query_devices(device=None, kind=None):  # type: ignore[no-untyped-def]
    device_info = {
        "name": "Fake Device",
        "index": 0,
        "max_input_channels": 1,
        "hostapi": 0,
        "default_samplerate": 44100,
    }
    if device is None and kind is None:
        return [device_info]
    return device_info


fake_sounddevice.PortAudioError = _FakePortAudioError
fake_sounddevice.InputStream = object
fake_sounddevice.check_input_settings = lambda *args, **kwargs: None  # type: ignore[no-untyped-def]
fake_sounddevice.query_devices = _fake_query_devices
fake_sounddevice.default = types.SimpleNamespace(device=(0, 0))

sys.modules.setdefault("sounddevice", fake_sounddevice)

from switch_interface import listener


def test_listen_background_thread_does_not_set_signal(monkeypatch: pytest.MonkeyPatch) -> None:
    control = listener.ListenerControl()
    started = threading.Event()
    stopped = threading.Event()

    @contextlib.contextmanager
    def fake_open_input(*args, **kwargs):  # type: ignore[no-untyped-def]
        started.set()
        yield None
        stopped.set()

    monkeypatch.setattr(listener, "open_input", fake_open_input)

    exceptions: list[BaseException] = []

    def run_listener() -> None:
        try:
            listener.listen(lambda: None, enable_fallback=False, control=control)
        except BaseException as exc:  # pragma: no cover - defensive capture
            exceptions.append(exc)

    thread = threading.Thread(target=run_listener)
    thread.start()

    try:
        assert started.wait(timeout=1), "listener did not attempt to open input stream"
        control.stop()
        assert stopped.wait(timeout=1), "listener did not exit input stream"
    finally:
        control.stop()
        thread.join(timeout=1)

    assert not thread.is_alive(), "listener thread did not terminate"
    assert not exceptions, f"listener raised unexpected exceptions: {exceptions!r}"
