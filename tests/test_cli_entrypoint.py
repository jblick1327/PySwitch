import subprocess
import sys


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "switch_interface", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "switch-accessible virtual keyboard" in result.stdout
