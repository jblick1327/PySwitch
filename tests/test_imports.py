import subprocess
import sys

import pytest


def test_no_circular_imports():
    pytest.importorskip("pipdeptree")
    subprocess.run(
        [sys.executable, "-m", "pipdeptree", "-w", "fail"],
        check=True,
        capture_output=True,
    )

