# Switch Interface Troubleshooting Guide

This guide provides solutions for common issues you might encounter when using the Switch Interface application. If you're experiencing problems, follow the troubleshooting steps below to resolve them.

## Audio Device Issues

### No Microphone Detected

**Symptoms:**
- "No microphone or audio input device was detected" error message
- Calibration fails to start
- Application cannot detect your switch inputs

**Solutions:**
1. **Check physical connections**
   - Ensure your microphone or headset is properly connected to your computer
   - Try a different USB port if using a USB microphone
   - Check that cables are not damaged or loose

2. **Check system audio settings**
   - Windows: Open Sound settings from Control Panel or right-click the speaker icon in the taskbar
   - Verify your microphone is listed and not disabled
   - Set your preferred microphone as the default recording device

3. **Check application permissions**
   - Windows: Go to Settings > Privacy > Microphone
   - Ensure microphone access is enabled for apps
   - Allow Switch Interface to access your microphone

4. **Try alternative audio devices**
   - Connect a different microphone or headset if available
   - Built-in laptop microphones can work as a fallback option
   - Some webcams include built-in microphones that can be used

5. **Restart your computer**
   - Sometimes audio devices need a system restart to be properly recognized

### Exclusive Mode Access Denied

**Symptoms:**
- "Could not get exclusive access to your audio device" error message
- Application starts but cannot detect switch inputs
- Calibration fails with access errors

**Solutions:**
1. **Close other applications using your microphone**
   - Video conferencing apps (Zoom, Teams, Skype)
   - Voice recording software
   - Voice assistants (Cortana, Google Assistant)
   - Browser tabs with microphone access

2. **Use shared mode**
   - The application will automatically try to use shared mode
   - You can force shared mode by setting the environment variable:
     ```
     SWITCH_EXCLUSIVEMODE=0
     ```

3. **Check for background applications**
   - Some applications may be using your microphone in the background
   - Check Task Manager for applications that might be using audio input

### Calibration Problems

**Symptoms:**
- Calibration fails to detect switch inputs
- Inconsistent switch detection
- Too many false positives or missed activations

**Solutions:**
1. **Adjust microphone position**
   - Position the microphone closer to the switch
   - Reduce background noise sources
   - Ensure the switch makes a clear, audible sound

2. **Try different sensitivity settings**
   - Use the sensitivity slider in the calibration screen
   - Higher sensitivity detects quieter sounds but may cause false activations
   - Lower sensitivity reduces false activations but may miss quiet switches

3. **Skip calibration if needed**
   - Click "Skip Calibration" to use default settings
   - You can recalibrate later from the launcher

4. **Check switch hardware**
   - Ensure your physical switch is working correctly
   - Some switches may need maintenance or replacement if they're not making consistent sounds

## Hardware Setup and Connection

### Switch Hardware Setup

**Types of Switches:**
1. **Sound-based switches**
   - Mechanical switches that make an audible click
   - Bubble wrap or similar materials that make noise when pressed
   - Any device that produces a consistent sound

2. **Microphone placement**
   - Position the microphone within 1-3 feet of the switch
   - Avoid placing near sources of background noise
   - Secure the microphone to prevent movement

3. **DIY switch options**
   - Simple button or switch connected to a small box that makes noise
   - Bubble wrap in a small container
   - Any mechanism that produces a consistent sound when activated

### Computer Setup

1. **System requirements**
   - Windows 10 or newer
   - Working microphone or audio input device
   - 4GB RAM minimum (8GB recommended)
   - 100MB free disk space

2. **Audio device configuration**
   - Set your recording device to 44.1kHz, 16-bit in Windows sound settings
   - Disable audio enhancements if available
   - Set microphone boost to an appropriate level if your switch is quiet

3. **USB connections**
   - Use USB 2.0 or 3.0 ports directly on your computer (not through a hub if possible)
   - Some USB hubs may cause audio device detection issues
   - Try different USB ports if a device is not recognized

## Error Message Reference

### Audio Errors

| Error Message | Likely Cause | Solution |
|---------------|--------------|----------|
| "No microphone or audio input device was detected" | No microphone connected or recognized | Connect a microphone and check system sound settings |
| "Could not get exclusive access to your audio device" | Another application is using the microphone | Close other applications or use shared mode |
| "Permission denied when trying to access your microphone" | System privacy settings blocking access | Check Windows Privacy settings for microphone access |
| "Audio device disconnected" | Physical connection issue or driver problem | Reconnect device or restart computer |

### Configuration Errors

| Error Message | Likely Cause | Solution |
|---------------|--------------|----------|
| "Could not save or load configuration settings" | Permission issues or disk problems | Run as administrator or check folder permissions |
| "Your configuration file appears to be corrupted" | Unexpected shutdown or disk errors | Application will reset to default settings |
| "Invalid configuration value" | Manual edits to config file with incorrect values | Application will use default values |

### Layout Errors

| Error Message | Likely Cause | Solution |
|---------------|--------------|----------|
| "The selected keyboard layout could not be found" | Missing or moved layout file | Application will use a default layout |
| "The keyboard layout file appears to be corrupted" | Invalid JSON format in layout file | Try selecting a different layout |
| "Layout validation failed" | Custom layout with incorrect structure | Check layout file format against documentation |

### Startup Errors

| Error Message | Likely Cause | Solution |
|---------------|--------------|----------|
| "A required component could not be loaded" | Missing files or incomplete installation | Reinstall the application |
| "The application does not have permission to start properly" | Permission issues | Run as administrator |
| "The application could not start properly" | Various system issues | Restart computer or reinstall application |

## Environment-Specific Setup

### Windows Setup

1. **Audio device setup**
   - Right-click the speaker icon in the taskbar and select "Sound settings"
   - Go to "Sound Control Panel" > "Recording" tab
   - Right-click your microphone and select "Properties"
   - On the "Advanced" tab, set format to "2 channel, 16 bit, 44100 Hz (CD Quality)"
   - On the "Levels" tab, adjust microphone volume to 75-100%

2. **Permission settings**
   - Go to Windows Settings > Privacy > Microphone
   - Ensure "Allow apps to access your microphone" is turned on
   - If running from a restricted folder, you may need to run as administrator

3. **Firewall settings**
   - No internet connection is required for basic functionality
   - If using predictive text features that require network access:
     - Allow Switch Interface through Windows Firewall if prompted

### Portable Usage (USB Drive)

1. **Preparation**
   - Copy the entire application folder to your USB drive
   - No installation is required

2. **Running from USB**
   - Double-click the executable to run
   - First-time setup will create configuration on the host computer
   - Audio devices will need to be reconfigured on each new computer

3. **Limitations**
   - Performance may be slower when running from USB
   - Configuration is stored on the host computer, not the USB drive
   - Some computers may restrict running applications from USB drives

## Advanced Troubleshooting

### Safe Mode

If you encounter persistent issues, you can start the application in Safe Mode:

1. When an error occurs, click the "Safe Mode" button in the error dialog
2. Safe Mode uses:
   - A simplified keyboard layout
   - Slower scanning speed
   - Shared audio mode
   - Minimal functionality to ensure basic operation

### Command Line Options

Advanced users can troubleshoot using command line options:

```
switch-interface --layout simple_alphabet.json --dwell 1.0 --shared-audio
```

Common options:
- `--layout [filename]`: Specify keyboard layout
- `--dwell [seconds]`: Set scanning speed (higher is slower)
- `--row-column`: Use row-column scanning instead of linear
- `--shared-audio`: Force shared audio mode
- `--debug`: Enable debug logging

### Log Files

Log files can help identify issues:

1. **Location**: Logs are stored in the user's temp directory:
   - Windows: `%TEMP%\switch_interface\logs\`

2. **Reviewing logs**:
   - Check the most recent log file for error messages
   - Look for lines marked ERROR or WARNING
   - Include relevant log sections when seeking support

## Getting Additional Help

If you continue to experience issues after trying these troubleshooting steps:

1. **Check documentation**:
   - Review the Getting Started guide
   - Check for updated troubleshooting information online

2. **Contact support**:
   - Email: support@switch-interface.org
   - Include a description of your issue
   - Attach log files if possible
   - Mention troubleshooting steps you've already tried