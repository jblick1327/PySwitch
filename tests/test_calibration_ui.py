import importlib
import sys
import types

import pytest


def _setup_dummy_tk(monkeypatch):
    class DummyVar:
        def __init__(self, master=None, value=None):
            self._value = value

        def get(self):
            return self._value

        def set(self, v):
            self._value = v

    class DummyCanvas:
        def __init__(self, master=None, width=0, height=0, bg=None):
            self.master = master
            master.canvas = self

        def pack(self, *args, **kwargs):
            pass

        def create_line(self, *args, **kwargs):
            pass

        def delete(self, tag):
            pass

    class DummyScale:
        def __init__(self, *args, **kwargs):
            pass

        def pack(self, *args, **kwargs):
            pass

    class DummyFrame:
        def __init__(self, master=None):
            self.master = master

        def pack(self, *args, **kwargs):
            pass

    class DummyButton:
        def __init__(self, master=None, text=None, command=None):
            self.command = command
            master.button = self
            if hasattr(master, "master") and master.master is not None:
                master.master.button = self

        def pack(self, *args, **kwargs):
            pass

        def invoke(self):
            if self.command:
                self.command()

    class DummyLabel:
        def __init__(self, master=None, text=None):
            self.master = master

        def pack(self, *args, **kwargs):
            pass

        def config(self, **kwargs):
            pass

    class DummyOptionMenu:
        def __init__(self, master=None, var=None, *values):
            self.master = master
            self.menu = types.SimpleNamespace(
                delete=lambda *a: None, add_command=lambda *a, **k: None
            )

        def pack(self, *args, **kwargs):
            pass

        def __getitem__(self, key):
            if key == "menu":
                return self.menu
            raise KeyError(key)

        def destroy(self):
            pass

    class DummyTk:
        instance = None

        def __init__(self):
            DummyTk.instance = self
            self._bg = "default"

        def title(self, title):
            self.title = title

        def protocol(self, name, cb):
            self.cb = cb

        def after(self, ms, func):
            return "id"

        def configure(self, **kwargs):
            if "bg" in kwargs:
                self._bg = kwargs["bg"]

        def cget(self, key):
            if key == "bg":
                return self._bg
            raise KeyError(key)

        def mainloop(self):
            if hasattr(self, "button"):
                self.button.invoke()

        def destroy(self):
            pass

    tk_mod = types.SimpleNamespace(
        Tk=DummyTk,
        Canvas=DummyCanvas,
        Scale=DummyScale,
        Frame=DummyFrame,
        Button=DummyButton,
        Label=DummyLabel,
        OptionMenu=DummyOptionMenu,
        DoubleVar=DummyVar,
        StringVar=DummyVar,
        IntVar=DummyVar,
        HORIZONTAL="horizontal",
        LEFT="left",
        X="x",
        messagebox=types.SimpleNamespace(showerror=lambda *a, **k: None),
    )
    monkeypatch.setitem(sys.modules, "tkinter", tk_mod)
    return DummyTk


def _setup_dummy_sd(monkeypatch):
    calls = []

    class DummyStream:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def start(self):
            pass

        def stop(self):
            pass

        def close(self):
            pass

    def check_input_settings(device=None, samplerate=None, blocksize=None, **kw):
        return None

    sd_mod = types.SimpleNamespace(
        InputStream=lambda **kw: DummyStream(**kw),
        PortAudioError=Exception,
        query_devices=lambda: [
            {"name": "Mic1", "max_input_channels": 1},
            {"name": "Mic2", "max_input_channels": 1},
        ],
        check_input_settings=check_input_settings,
        default=types.SimpleNamespace(hostapi=0),
        query_hostapis=lambda idx: {"name": "Windows WASAPI"},
    )
    monkeypatch.setitem(sys.modules, "sounddevice", sd_mod)
    import switch_interface.audio.stream as stream
    import switch_interface.audio.backends.wasapi as wasapi
    importlib.reload(stream)
    importlib.reload(wasapi)
    stream.rescan_backends()
    return calls


def test_calibrate_canvas_and_stream(monkeypatch):
    DummyTk = _setup_dummy_tk(monkeypatch)
    calls = _setup_dummy_sd(monkeypatch)
    monkeypatch.setattr(
        "switch_interface.audio.backends.wasapi.get_extra_settings",
        lambda: None,
    )
    import switch_interface.calibration as calibration

    importlib.reload(calibration)
    res = calibration.calibrate(calibration.DetectorConfig())
    assert isinstance(res, calibration.DetectorConfig)
    assert DummyTk.instance.canvas is not None
    assert len(calls) == 1


def test_sample_rates_filtered(monkeypatch):
    DummyTk = _setup_dummy_tk(monkeypatch)
    calls = _setup_dummy_sd(monkeypatch)

    tk_mod = sys.modules["tkinter"]
    orig_menu = tk_mod.OptionMenu

    captured: list[tuple] = []

    class CaptureMenu(orig_menu):
        def __init__(self, master=None, var=None, *values):
            captured.append(values)
            super().__init__(master, var, *values)

    monkeypatch.setattr(tk_mod, "OptionMenu", CaptureMenu)

    def check_input_settings(device=None, samplerate=None, blocksize=None, **kw):
        if samplerate in (44100, 48000):
            return None
        raise Exception("bad rate")

    sd_mod = sys.modules["sounddevice"]
    monkeypatch.setattr(sd_mod, "check_input_settings", check_input_settings)

    monkeypatch.setattr(
        "switch_interface.audio.backends.wasapi.get_extra_settings", lambda: None
    )

    import switch_interface.calibration as calibration

    importlib.reload(calibration)
    res = calibration.calibrate(calibration.DetectorConfig())
    assert isinstance(res, calibration.DetectorConfig)
    assert {"44100", "48000"} <= set(captured[0])
    assert len(calls) == 1


def test_block_sizes_filtered(monkeypatch):
    DummyTk = _setup_dummy_tk(monkeypatch)
    calls = _setup_dummy_sd(monkeypatch)

    tk_mod = sys.modules["tkinter"]
    orig_menu = tk_mod.OptionMenu

    captured: list[tuple] = []

    class CaptureMenu(orig_menu):
        def __init__(self, master=None, var=None, *values):
            captured.append(values)
            super().__init__(master, var, *values)

    monkeypatch.setattr(tk_mod, "OptionMenu", CaptureMenu)

    def check_input_settings(device=None, samplerate=None, blocksize=None, **kw):
        if blocksize in (256, 512):
            return None
        raise Exception("bad block")

    sd_mod = sys.modules["sounddevice"]
    monkeypatch.setattr(sd_mod, "check_input_settings", check_input_settings)

    monkeypatch.setattr(
        "switch_interface.audio.backends.wasapi.get_extra_settings", lambda: None
    )

    import switch_interface.calibration as calibration

    importlib.reload(calibration)
    res = calibration.calibrate(calibration.DetectorConfig())
    assert isinstance(res, calibration.DetectorConfig)
    assert {"256", "512"} <= set(captured[1])
    assert len(calls) == 1
