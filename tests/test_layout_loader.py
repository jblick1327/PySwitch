import json
from importlib import resources

import pytest

from switch_interface.kb_layout_io import load_keyboard


def test_default_load():
    kb = load_keyboard()
    assert len(kb) > 0


def test_load_keyboard_missing_fields(tmp_path):
    bad_layout = {"pages": [{"rows": [{}]}]}
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(bad_layout))
    with pytest.raises(ValueError) as exc:
        load_keyboard(str(p))
    assert "keys" in str(exc.value)


def test_load_keyboard_valid_path():
    path = (
        resources.files("switch_interface.resources.layouts")
        .joinpath("pred_test.json")
    )
    kb = load_keyboard(str(path))
    assert len(kb) > 0
