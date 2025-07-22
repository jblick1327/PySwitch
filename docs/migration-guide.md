# Migration Guide for Existing Users

This guide helps existing users of Switch Interface upgrade to version 1.2.0, which builds upon the UX improvements introduced in v1.1.0 with additional refinements, bug fixes, and enhanced documentation.

## What's New in v1.2.0

The latest version includes several improvements that build upon the UX enhancements introduced in v1.1.0:

- Enhanced documentation with more detailed troubleshooting guides
- Improved installer package with better cross-platform support
- Fixed issues with configuration migration from v1.0.0
- Addressed edge cases in audio device fallback mechanism
- Refined error messages for better user experience

## Upgrading from v1.1.0

If you're upgrading from v1.1.0, the process is straightforward:

1. Download the latest version from the official website or repository.
2. Run the installer and follow the on-screen instructions.
3. Your existing configuration will be preserved.

No additional steps are required as v1.2.0 is fully compatible with v1.1.0 configurations.

## Upgrading from v1.0.0

### Step 1: Backup Your Configuration

Before upgrading, it's recommended to backup your existing configuration:

1. Locate your configuration file:
   - Windows: `%APPDATA%\switch_interface\config.json`
   - macOS: `~/Library/Application Support/switch_interface/config.json`
   - Linux: `~/.config/switch_interface/config.json`

2. Make a copy of this file to a safe location.

### Step 2: Install the New Version

1. Download the latest version from the official website or repository.
2. Run the installer and follow the on-screen instructions.
3. If prompted to replace existing files, choose "Yes".

### Step 3: Configuration Compatibility

Your existing configuration will be automatically migrated to the new format. The application will:

- Convert old parameter names to new ones (e.g., `scan_time` → `scan_interval`)
- Add any missing parameters with sensible defaults
- Validate and repair any corrupted settings

If you experience any issues with your configuration after upgrading:

1. Launch the application with the `--reset-config` flag to create a fresh configuration.
2. Manually transfer your preferred settings from your backup.

### Step 4: Layout Compatibility

Custom layouts created in v1.0.0 will continue to work in v1.1.0. However, you may want to try the new built-in layouts:

- `qwerty_full.json`: A comprehensive QWERTY layout with all essential keys
- `simple_alphabet.json`: A beginner-friendly alphabetical layout

To switch to a new layout:

1. Launch the application.
2. Click on "Settings" in the launcher.
3. Select "Keyboard Layout" and choose one of the new layouts.

### Step 5: Audio Device Configuration

The new version includes improved audio device management with automatic fallback. If you previously had issues with audio device detection:

1. Launch the application.
2. If prompted about audio device issues, follow the on-screen instructions.
3. The application will automatically try alternative devices if your primary device fails.

## Troubleshooting

If you encounter any issues after upgrading:

1. Check the [troubleshooting documentation](troubleshooting.md) for common issues and solutions.
2. Try running the application in safe mode by launching with the `--safe-mode` flag.
3. If problems persist, you can revert to your backup configuration file.

## New Features to Try

After upgrading, we recommend exploring these new features:

1. **Enhanced Setup Wizard**: If you're setting up on a new device, the improved wizard provides clearer guidance.
2. **Skip Calibration Option**: If you have trouble with calibration, you can now skip it and use sensible defaults.
3. **New Keyboard Layouts**: Try the new comprehensive QWERTY layout for a better typing experience.
4. **Improved Error Messages**: The application now provides more helpful error messages with specific troubleshooting steps.

## Feedback

We welcome your feedback on the new version. Please report any issues or suggestions through our official support channels.