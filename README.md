# Switch Interface

Switch Interface is a lightweight and simple scanning keyboard for one-switch input. It highlights keys on a virtual keyboard while listening to microphone input to detect switch presses. Predictive word and letter suggestions speed up typing.
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

If no microphone is detected when launching the GUI, an error will direct you to
the calibration menu where you can choose an input device from a dropdown.
<!-- TODO: add wizard GIF here -->

On Windows the microphone is opened in WASAPI exclusive mode when possible. If
exclusive access fails, the program falls back to the default shared mode. Set
the `SWITCH_EXCLUSIVEMODE` environment variable to `0` to force shared mode.

### Layout files

Layouts live in `switch_interface/resources/layouts/`. Each JSON file defines `pages` containing rows of `keys`. Keys can specify a label and an action. The `pred_test.json` layout includes special `predict_word` and `predict_letter` keys that pull suggestions from the built‑in predictive text engine.

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

## Contributing

**TODO**: Replace the placeholder GIF/PNG in `docs/` with real media before opening a PR.
