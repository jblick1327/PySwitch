import os
import subprocess
import sys
from importlib import metadata


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
    eps = metadata.entry_points(group="console_scripts")
    ep = next(ep for ep in eps if ep.name == "switch-interface")
    assert ep.value == "switch_interface.launcher:main"

    code = (
        "import os, sys, types, runpy\n"
        "os.environ['SI_TEST_MODE'] = '1'\n"
        "sys.modules['sounddevice'] = types.SimpleNamespace()\n"
        "runpy.run_module('switch_interface.launcher', run_name='__main__')\n"
    )
    result = subprocess.run(
        [sys.executable, "-"],
        input=code,
        text=True,
        capture_output=True,
    )
    assert result.stdout.strip() == "launcher-main-invoked"
