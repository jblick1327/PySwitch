import subprocess


def test_no_circular_imports():
    subprocess.run(["pipdeptree", "-w", "fail"], check=True, capture_output=True)

