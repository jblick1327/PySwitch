import logging
import time
import sys
import types

import switch_interface.__main__ as cli


def test_launch_continues_when_device_check_hangs(monkeypatch, caplog):
    events = []

    class DummyRoot:
        def after(self, ms, func):
            return "id"

        def after_cancel(self, _id):
            pass

        def mainloop(self):
            events.append("mainloop")

    class DummyVK:
        def __init__(self, *a, **k):
            events.append("init")
            self.root = DummyRoot()

        def run(self):
            events.append("run")

    class DummyScanner:
        def __init__(self, *a, **k):
            pass

        def start(self):
            events.append("start")

    class DummyPC:
        def __init__(self):
            self.on_key = lambda *a, **k: None
            self.state = None

    vk_mod = types.SimpleNamespace(VirtualKeyboard=DummyVK)
    monkeypatch.setitem(sys.modules, "switch_interface.kb_gui", vk_mod)
    monkeypatch.setattr("switch_interface.scan_engine.Scanner", DummyScanner)
    monkeypatch.setattr("switch_interface.pc_control.PCController", DummyPC)
    monkeypatch.setattr("switch_interface.kb_layout_io.load_keyboard", lambda p: "kb")
    monkeypatch.setattr("switch_interface.detection.listen", lambda *a, **k: None)
    monkeypatch.setattr(
        "switch_interface.listener.check_device", lambda *a, **k: time.sleep(5)
    )

    calib_mod = types.SimpleNamespace(
        calibrate=lambda c: c,
        load_config=lambda: types.SimpleNamespace(
            samplerate=1, blocksize=1, device=None
        ),
        save_config=lambda c: None,
    )
    monkeypatch.setitem(sys.modules, "switch_interface.calibration", calib_mod)

    class DummyEvent:
        def set(self):
            pass

        def wait(self, timeout=None):
            return False

    class DummyThread:
        def __init__(self, target=None, args=None, daemon=None):
            self.target = target
            self.args = args or ()

        def start(self):
            pass

    monkeypatch.setattr(cli.threading, "Event", DummyEvent)
    monkeypatch.setattr(cli.threading, "Thread", DummyThread)

    with caplog.at_level(logging.WARNING):
        cli.keyboard_main([])

    assert "init" in events
    assert "run" in events
    assert "timed out" in caplog.text
