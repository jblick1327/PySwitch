# Getting Started with Switch Interface

## Quick Start

1. **Download and Run**
   - Download `switch-interface.exe` from [Releases](https://github.com/jblick1327/switch_interface/releases)
   - Double-click to run - no installation required

2. **First Launch**
   - The setup wizard will guide you through:
     - Selecting your microphone/input device
     - Calibrating switch detection
     - Choosing scanning speed
   - If you encounter issues, you can skip calibration and use defaults

3. **Using the Keyboard**
   - Keys highlight automatically in sequence
   - Activate your switch (microphone input) when the desired key is highlighted
   - Use predictive text suggestions to speed up typing

## Troubleshooting

### No Microphone Detected
- Ensure your microphone is connected and working
- Try running the calibration from the main menu
- Check Windows audio settings to ensure the device is enabled

### Switch Not Responding
- Adjust sensitivity in the calibration menu
- Try different microphone positions
- Check that your switch is making audible sound

### Scanning Too Fast/Slow
- Adjust the dwell time slider in the launcher
- Use presets: Slow (700ms), Medium (450ms), Fast (250ms)

## Layout Options

- **QWERTY Full**: Complete keyboard with all essential keys including numbers, punctuation, and common actions
- **Simple Alphabet**: Beginner-friendly alphabetical layout with predictive text support
- **Numeric Pad**: Numbers and basic math symbols
- **Media Controls**: Play, pause, volume controls

The application will automatically select the most appropriate layout based on your experience level. New users will see simpler layouts, while experienced users can access more comprehensive options.

## Advanced Usage

### Custom Layouts
See [layouts.md](layouts.md) for creating your own keyboard layouts.

### Environment Variables
- `LAYOUT_PATH`: Path to custom layout file
- `SWITCH_EXCLUSIVEMODE=0`: Force shared audio mode on Windows

### Command Line
```bash
switch-interface --layout custom.json --dwell 0.8 --row-column
```