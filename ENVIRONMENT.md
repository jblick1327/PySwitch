# Environment Notes

- **Windows exclusive mode**: On Windows the microphone is opened in WASAPI exclusive mode when possible. If exclusive access fails, the program automatically falls back to the default shared mode.
- **Log file location**: All console output is mirrored to `~/.switch_interface.log` by default. Pass a custom path to `switch_interface.logging.setup` to store logs elsewhere.
- **No microphone detected**: If no input device is available, the GUI opens the calibration menu so you can select a device from a drop-down list.

## PortAudio installation

Switch Interface depends on the `sounddevice` package which requires PortAudio.  
If `pip install -r requirements.txt` fails because PortAudio is missing, follow the instructions for your platform below.

### Windows

The prebuilt wheels already include the PortAudio library, so normally no extra
steps are required. If you build from source, install the development files from
[PortAudio's downloads](http://www.portaudio.com/download.html).

### macOS

Install PortAudio with Homebrew or MacPorts before installing the Python
dependencies:

```bash
brew install portaudio  # Homebrew
# or
sudo port install portaudio  # MacPorts
```

### Linux

Install PortAudio and the development headers from your package manager. On
Debian or Ubuntu based distributions run:

```bash
sudo apt-get install libportaudio2 portaudio19-dev
```

Other distributions provide similarly named packages through their package
managers. Add your user to the `audio` group if recording fails due to
permissions.

## Environment variables

Several options can be configured through environment variables before starting
the program:

- `SWITCH_EXCLUSIVEMODE` – set to `0` to force shared mode on Windows. Leaving
  it unset or setting `1` keeps the default exclusive mode.
- `LAYOUT_PATH` – path to a custom keyboard layout JSON file.

### Setting variables

On **Windows Command Prompt**:

```cmd
set SWITCH_EXCLUSIVEMODE=0
```

On **PowerShell**:

```powershell
$env:SWITCH_EXCLUSIVEMODE=0
```

On **macOS/Linux**:

```bash
export SWITCH_EXCLUSIVEMODE=0
```

Run `switch-interface` from the same terminal after setting the variables so the
program picks them up.
