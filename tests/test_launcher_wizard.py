from switch_interface import config
from tests.test_calibration_ui import _setup_dummy_tk
import importlib
import sys
import types


def test_wizard_invoked_first_run(monkeypatch, tmp_path):
    DummyTk = _setup_dummy_tk(monkeypatch)
    DummyTk.mainloop = lambda self: None
    DummyTk.withdraw = lambda self: None
    sys.modules["tkinter"].BooleanVar = sys.modules["tkinter"].DoubleVar
    sys.modules["tkinter"].Checkbutton = lambda *a, **k: types.SimpleNamespace(
        pack=lambda *a, **k: None
    )
    sys.modules["tkinter"].RIGHT = "right"

    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "cfg.json")
    monkeypatch.setattr(
        config,
        "load_settings",
        lambda path=None: {"calibration_complete": False},
    )

    called = []

    class DummyWizard:
        def __init__(self, master=None):
            called.append("init")

        def show_modal(self):
            called.append("show")

    dummy_gui = types.SimpleNamespace(FirstRunWizard=DummyWizard)
    monkeypatch.setitem(sys.modules, "switch_interface.gui", dummy_gui)
    dummy_calib = types.SimpleNamespace(calibrate=lambda: None)
    monkeypatch.setitem(sys.modules, "switch_interface.calibration", dummy_calib)
    dummy_main = types.SimpleNamespace(keyboard_main=lambda *a, **k: None)
    monkeypatch.setitem(sys.modules, "switch_interface.__main__", dummy_main)

    import switch_interface.launcher as launcher
    importlib.reload(launcher)
    launcher.main()

    assert called == ["init", "show"]
