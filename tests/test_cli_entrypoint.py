import os
import subprocess
import sys
from pathlib import Path


def test_module_uses_launcher():
    code = (
        "import sys, types, runpy\n"
        "sys.modules['sounddevice'] = types.SimpleNamespace()\n"
        "import switch_interface.launcher as l\n"
        "l.main = lambda: print('launcher-main-invoked')\n"
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
        "import sys, types, runpy, pathlib\n"
        "sys.modules['sounddevice'] = types.SimpleNamespace()\n"
        "import switch_interface.launcher as l\n"
        "l.main = lambda: print('launcher-main-invoked')\n"
        f"runpy.run_path(str(pathlib.Path('{script}')), run_name='__main__')\n"
    )
    result = subprocess.run(
        [sys.executable, "-"],
        input=code,
        text=True,
        capture_output=True,
    )
    assert result.stdout.strip() == "launcher-main-invoked"
