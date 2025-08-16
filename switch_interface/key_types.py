from enum import Enum, auto


# Authoritative list of Actions. Any new key must be added here.
class Action(str, Enum):
    def _generate_next_value_(name, *_):
        return name

    # physical keys, directly corresponding to pynput actions
    alt = auto()
    alt_l = auto()
    alt_r = auto()
    alt_gr = auto()
    backspace = auto()
    caps_lock = auto()
    cmd = auto()
    cmd_l = auto()
    cmd_r = auto()
    ctrl = auto()
    ctrl_l = auto()
    ctrl_r = auto()
    delete = auto()
    down = auto()
    end = auto()
    enter = auto()
    esc = auto()
    f1 = auto()
    f2 = auto()
    f3 = auto()
    f4 = auto()
    f5 = auto()
    f6 = auto()
    f7 = auto()
    f8 = auto()
    f9 = auto()
    f10 = auto()
    f11 = auto()
    f12 = auto()
    f13 = auto()
    f14 = auto()
    f15 = auto()
    f16 = auto()
    f17 = auto()
    f18 = auto()
    f19 = auto()
    f20 = auto()
    home = auto()
    left = auto()
    page_down = auto()
    page_up = auto()
    right = auto()
    shift = auto()
    shift_l = auto()
    shift_r = auto()
    space = auto()
    tab = auto()
    up = auto()
    media_play_pause = auto()
    media_volume_mute = auto()
    media_volume_down = auto()
    media_volume_up = auto()
    media_previous = auto()
    media_next = auto()
    insert = auto()
    menu = auto()
    num_lock = auto()
    pause = auto()
    print_screen = auto()
    scroll_lock = auto()

    # virtual functions, user defined, etc
    page_next = auto()  # switch to next keyboard page
    page_prev = auto()  # switch to previous keyboard page
    reset_scan_row = auto()  # move scanner back to first key in row
    predict_word = auto()  # predictive text (common‑word) key placeholder
    predict_letter = auto()  # predictive text (common-letter) key placeholder

    # Common punctuation and symbols
    period = auto()
    comma = auto()
    question = auto()
    exclamation = auto()
    apostrophe = auto()
    colon = auto()
    semicolon = auto()
    quote = auto()
    hyphen = auto()
    underscore = auto()
    left_paren = auto()
    right_paren = auto()
    left_bracket = auto()
    right_bracket = auto()
    left_brace = auto()
    right_brace = auto()
    less_than = auto()
    greater_than = auto()
    forward_slash = auto()
    backslash = auto()
    at_sign = auto()
    hash = auto()
    dollar = auto()
    percent = auto()
    caret = auto()
    ampersand = auto()
    asterisk = auto()
    plus = auto()
    equals = auto()
    pipe = auto()

    # Common actions
    copy = auto()
    paste = auto()
    cut = auto()
    undo = auto()
    redo = auto()
    select_all = auto()
    escape = auto()

    # Navigation
    next_page = auto()  # Alias for page_next for clarity
    prev_page = auto()  # Alias for page_prev for clarity

    # UI elements
    header = auto()  # Non-interactive header/label
    help = auto()  # Show help information

    _VIRTUAL_ACTIONS = {
        "page_next",
        "page_prev",
        "reset_scan_row",
        "predict_word",
        "predict_letter",
        "next_page",
        "prev_page",
        "header",
        "help",
    }

    def is_virtual(self) -> bool:
        """Return ``True`` if this action should not emit an OS key event."""
        return self.name in self._VIRTUAL_ACTIONS

    def to_os_key(self):
        """Return the matching :class:`pynput.keyboard.Key` or ``None``."""
        if self.is_virtual():
            return None

        from pynput.keyboard import Key as OSKey

        try:
            return getattr(OSKey, self.value)
        except AttributeError:
            return None
