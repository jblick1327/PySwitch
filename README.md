# Switch Interface v1.2.0

Switch Interface is a lightweight and simple scanning keyboard for one-switch input. It highlights keys on a virtual keyboard while listening to microphone input to detect switch presses. Predictive word and letter suggestions speed up typing.

This version (v1.2.0) builds upon the UX improvements in v1.1.0, with additional refinements and bug fixes. See the [release notes](docs/release-notes-v1.2.0.md) for details.
<!-- TODO: add keyboard screenshot here -->

## Requirements

- Python 3.11 or newer

## Setup

Install runtime dependencies:

```bash
pip install -r requirements.txt
```

For development (tests and linting) install the additional tools:

```bash
pip install -r dev-requirements.txt
```

The CI workflow performs the same two commands before running `ruff`, `mypy`, and `pytest`.

See [ENVIRONMENT.md](ENVIRONMENT.md) for platform-specific PortAudio setup and
examples of environment variables such as `SWITCH_EXCLUSIVEMODE`.

## Getting Started

For detailed setup instructions, see our [Getting Started Guide](docs/getting-started.md).

Clone the repository and install the dependencies in editable mode:

```bash
git clone https://github.com/jblick1327/switch_interface.git
cd switch_interface
pip install -e .[dev]
```

Launch the on-screen keyboard with the default layout:

```bash
switch-interface
```

Press `Ctrl+C` in the console or close the window to exit.

## Download

Download the latest `switch-interface.exe` from the [Releases](https://github.com/jblick1327/switch_interface/releases) page and run it directly. No additional installation is required.

### Development

Install the project in editable mode if you want to run from source:

```bash
pip install -e .
```

If no microphone is detected when launching the GUI, the application will automatically try alternative audio devices. If no working device is found, an error will direct you to the calibration menu where you can choose an input device from a dropdown.
<!-- TODO: add wizard GIF here -->

On Windows the microphone is opened in WASAPI exclusive mode when possible. If exclusive access fails, the program automatically falls back to shared mode. Set the `SWITCH_EXCLUSIVEMODE` environment variable to `0` to force shared mode.

### Layout files

Layouts live in `switch_interface/resources/layouts/`. Each JSON file defines `pages` containing rows of `keys`. Keys can specify a label and an action. 

The application comes with several built-in layouts:
- `qwerty_full.json` - Complete QWERTY layout with all essential keys
- `simple_alphabet.json` - Beginner-friendly alphabetical layout
- `pred_test.json` - Layout with predictive text capabilities

The layouts include special `predict_word` and `predict_letter` keys that pull suggestions from the built‑in predictive text engine.

See [docs/layouts.md](docs/layouts.md) for a detailed explanation of the format and examples.

You can point `--layout` to any file in this format or set the `LAYOUT_PATH` environment variable.

## Logging

All console output is also written to `~/.switch_interface.log` by default. You
may pass a custom file path to :func:`switch_interface.logging.setup` if you
need to store logs elsewhere.

## Testing

Run the unit tests after installing the project:

```bash
pytest
```

## Documentation

- [Getting Started Guide](docs/getting-started.md) - Step-by-step instructions for new users
- [Layouts Documentation](docs/layouts.md) - Information about keyboard layouts
- [Migration Guide](docs/migration-guide.md) - Guide for existing users upgrading from previous versions
- [Release Notes](docs/release-notes-v1.2.0.md) - Details about the latest release

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute to this project.

**TODO**: Replace the placeholder GIF/PNG in `docs/` with real media before opening a PR.
