import os
import subprocess
import sys
import textwrap
import venv
from pathlib import Path

INNO_TEMPLATE = textwrap.dedent(r"""
[Setup]
AppName=SwitchInterface
AppVersion={version}
AppPublisher=Open-Source AT
DefaultDirName={{localappdata}}\SwitchInterface
OutputBaseFilename=SwitchInterface-{version}
PrivilegesRequired=lowest
DefaultGroupName=SwitchInterface

[Files]
Source: "{exe}"; DestDir: "{{app}}"; Flags: ignoreversion

[Icons]
Name: "{{commondesktop}}\SwitchInterface"; Filename: "{{app}}\SwitchInterface.exe"
Name: "{{group}}\SwitchInterface"; Filename: "{{app}}\SwitchInterface.exe"
""")

def run(cmd):
    print("+", " ".join(map(str, cmd)))
    subprocess.check_call(cmd)

def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    build_dir = repo_root / "build"
    venv_dir = build_dir / "venv"
    if not venv_dir.exists():
        venv.create(venv_dir, with_pip=True)
    py = venv_dir / ("Scripts" if os.name == "nt" else "bin") / "python"

    run([py, "-m", "pip", "install", "pyinstaller==6.*"])

    exe_name = "SwitchInterface"
    icon = repo_root / "assets" / "app.ico"
    run([
        py,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--name",
        exe_name,
        f"--icon={icon}",
        str(repo_root / "switch_interface" / "__main__.py"),
    ])

    exe_path = repo_root / "dist" / f"{exe_name}.exe"
    cert_pfx = build_dir / "cert.pfx"
    run([
        "signtool",
        "sign",
        "/f",
        str(cert_pfx),
        "/p",
        os.environ.get("SIGN_PFX_PASS", ""),
        str(exe_path),
    ])

    ns = {}
    with open(repo_root / "switch_interface" / "__init__.py", "r", encoding="utf-8") as f:
        exec(f.read(), ns)
    version = ns.get("__version__")
    if not version:
        raise RuntimeError("Version not found")

    iss_content = INNO_TEMPLATE.format(version=version, exe=exe_path)
    iss_path = build_dir / "installer.iss"
    iss_path.write_text(iss_content, encoding="utf-8")

    run(["iscc", str(iss_path)])

if __name__ == "__main__":
    main()
