import os
import shutil
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Provide a dummy pynput backend so imports don't fail under CI
if "pynput.keyboard" not in sys.modules:

    class _DummyKey:
        shift = "shift"
        caps_lock = "caps_lock"

    class _DummyController:
        def press(self, k):
            pass

        def release(self, k):
            pass

        def type(self, t):
            pass

    dummy = SimpleNamespace(Key=_DummyKey, Controller=_DummyController)
    sys.modules["pynput"] = SimpleNamespace(keyboard=dummy)
    sys.modules["pynput.keyboard"] = dummy


@pytest.fixture
def local_tmp_dir():
    """Provide a writable, repo-local temp directory per test."""
    base = Path(__file__).resolve().parent.parent / ".tmp" / "test-artifacts"
    base.mkdir(parents=True, exist_ok=True)
    temp_dir = base / uuid.uuid4().hex
    temp_dir.mkdir()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
