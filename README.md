# Switch Interface

Switch Interface is a lightweight and simple scanning keyboard for one-switch input. It highlights keys on a virtual keyboard while listening to microphone input to detect switch presses. Predictive word and letter suggestions speed up typing.
<!-- TODO: add keyboard screenshot here -->

## Requirements

- Python 3.11 or newer
- Runtime dependencies (`pynput` and `wordfreq`) are installed automatically via `pip install -e .`.

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
exclusive access fails, the program falls back to the default shared mode.

### Layout files

Layouts live in `switch_interface/resources/layouts/`. Each JSON file defines `pages` containing rows of `keys`. Keys can specify a label and an action. The `pred_test.json` layout includes special `predict_word` and `predict_letter` keys that pull suggestions from the built‑in predictive text engine.

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
