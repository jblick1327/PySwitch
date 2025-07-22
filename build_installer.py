#!/usr/bin/env python3
"""
Build script for creating the Switch Interface installer package.
This script creates a Windows executable installer using PyInstaller.
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

def clean_build_dir():
    """Clean the build directory."""
    print("Cleaning build directory...")
    build_dir = Path("build")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(exist_ok=True)
    return build_dir

def get_version():
    """Get the version from pyproject.toml."""
    with open("pyproject.toml", "r") as f:
        for line in f:
            if line.strip().startswith("version"):
                version = line.split("=")[1].strip().strip('"\'')
                return version
    raise ValueError("Version not found in pyproject.toml")

def build_windows_installer(version):
    """Build the Windows installer using PyInstaller."""
    print(f"Building Windows installer for version {version}...")
    
    # Run PyInstaller
    subprocess.run([
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", f"switch-interface-{version}-win64",
        "--icon", "switch_interface/resources/icon.ico",
        "--add-data", "switch_interface/resources;switch_interface/resources",
        "switch_interface/launcher.py"
    ], check=True)
    
    # Move the executable to the build directory
    dist_dir = Path("dist")
    build_dir = Path("build")
    
    exe_file = dist_dir / f"switch-interface-{version}-win64.exe"
    target_file = build_dir / f"switch-interface-{version}-win64.exe"
    
    if exe_file.exists():
        shutil.copy(exe_file, target_file)
        print(f"Installer created: {target_file}")
        return target_file
    else:
        print(f"Error: Executable not found at {exe_file}")
        return None

def build_macos_installer(version):
    """Build the macOS installer."""
    print(f"Building macOS installer for version {version}...")
    # Implementation for macOS would go here
    print("macOS installer build not implemented yet")
    return None

def build_linux_installer(version):
    """Build the Linux installer."""
    print(f"Building Linux installer for version {version}...")
    # Implementation for Linux would go here
    print("Linux installer build not implemented yet")
    return None

def main():
    """Main function to build the installer package."""
    # Clean build directory
    build_dir = clean_build_dir()
    
    # Get version
    try:
        version = get_version()
        print(f"Building installer for Switch Interface v{version}")
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    
    # Build installer based on platform
    system = platform.system()
    if system == "Windows":
        installer_path = build_windows_installer(version)
    elif system == "Darwin":
        installer_path = build_macos_installer(version)
    elif system == "Linux":
        installer_path = build_linux_installer(version)
    else:
        print(f"Error: Unsupported platform: {system}")
        return 1
    
    if installer_path and installer_path.exists():
        print("\nInstaller build completed successfully!")
        print(f"Installer path: {installer_path}")
        
        # Test the installer
        print("\nRunning installer tests...")
        test_result = subprocess.run([
            "python", "test_installer_package.py", str(installer_path)
        ]).returncode
        
        if test_result == 0:
            print("\nInstaller tests passed!")
            return 0
        else:
            print("\nInstaller tests failed!")
            return 1
    else:
        print("\nInstaller build failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())