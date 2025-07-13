import types

from switch_interface.scan_engine import Scanner
from switch_interface.pc_control import PCController


class DummyRoot:
    def __init__(self):
        self.scheduled = []

    def after(self, ms, func):
        self.scheduled.append(func)
        return f"id{len(self.scheduled)}"

    def after_cancel(self, _id):
        self.scheduled.clear()


class DummyOSController:
    def __init__(self):
        self.events = []

    def press(self, k):
        self.events.append(("press", k))

    def release(self, k):
        self.events.append(("release", k))

    def type(self, text):
        self.events.append(("type", text))


class DummyKeyboard:
    def __init__(self, on_key):
        self.root = DummyRoot()
        self.highlight_index = 0
        self.highlight_row_index = None
        self.key_widgets = [
            (None, types.SimpleNamespace(label="a", action=None, mode="tap", dwell_mult=None)),
        ]
        self.row_start_indices = [0]
        self.row_indices = [0]
        self.on_key = on_key

    def advance_highlight(self):
        self.highlight_index = (self.highlight_index + 1) % len(self.key_widgets)

    def press_highlighted(self):
        _, key = self.key_widgets[self.highlight_index]
        self.on_key(key)

    def next_page(self):
        pass

    def prev_page(self):
        pass

    def row_start_for_index(self, index):
        return 0

    def highlight_row(self, row_idx):
        self.highlight_row_index = row_idx

    def _update_highlight(self):
        pass


def test_start_type_shutdown_cycle():
    oskb = DummyOSController()
    pc = PCController(kb=oskb)
    kb = DummyKeyboard(pc.on_key)
    scanner = Scanner(kb, dwell=0.01)

    scanner.start()
    assert kb.root.scheduled  # tick scheduled
    scanner.on_press()
    scanner.stop()

    assert oskb.events == [("type", "a")]
    assert kb.root.scheduled == []


def test_version_constant():
    from switch_interface import __version__

    assert __version__ == "0.1.0"
