import os
import subprocess
import sys
from pathlib import Path


def test_module_uses_launcher():
    code = (
        "import os, sys, types, runpy\n"
        "os.environ['SI_TEST_MODE'] = '1'\n"
        "sys.modules['sounddevice'] = types.SimpleNamespace()\n"
        "runpy.run_module('switch_interface', run_name='__main__')\n"
    )
    result = subprocess.run(
        [sys.executable, "-"],
        input=code,
        text=True,
        capture_output=True,
    )
    assert result.stdout.strip() == "launcher-main-invoked"


def test_console_script_uses_launcher():
    script = Path(sys.executable).parent / "switch-interface"
    code = (
        "import os, sys, types, runpy, pathlib\n"
        "os.environ['SI_TEST_MODE'] = '1'\n"
        "sys.modules['sounddevice'] = types.SimpleNamespace()\n"
        f"runpy.run_path(str(pathlib.Path('{script}')), run_name='__main__')\n"
    )
    result = subprocess.run(
        [sys.executable, "-"],
        input=code,
        text=True,
        capture_output=True,
    )
    assert result.stdout.strip() == "launcher-main-invoked"
