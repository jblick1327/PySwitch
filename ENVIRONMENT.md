# Environment Notes

- **Windows exclusive mode**: On Windows the microphone is opened in WASAPI exclusive mode when possible. If exclusive access fails, the program automatically falls back to the default shared mode.
- **Log file location**: All console output is mirrored to `~/.switch_interface.log` by default. Pass a custom path to `switch_interface.logging.setup` to store logs elsewhere.
- **No microphone detected**: If no input device is available, the GUI opens the calibration menu so you can select a device from a drop-down list.
