import json
from importlib import resources

from jsonschema import ValidationError, validate

from .kb_layout import Key, Keyboard, KeyboardPage, KeyboardRow

DEFAULT_LAYOUT = "pred_test.json"


_SCHEMA = {
    "type": "object",
    "properties": {
        "pages": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "rows": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "properties": {
                                "keys": {
                                    "type": "array",
                                    "minItems": 1,
                                    "items": {"type": "object", "required": ["label"]},
                                }
                            },
                            "required": ["keys"],
                        },
                    }
                },
                "required": ["rows"],
            },
        }
    },
    "required": ["pages"],
}


def _validate_layout(data: dict) -> None:
    try:
        validate(data, _SCHEMA)
    except ValidationError as exc:
        raise ValueError(f"Invalid keyboard layout: {exc.message}") from None


def load_keyboard(path: str | None = None) -> Keyboard:
    """Load a :class:`Keyboard` definition from ``path`` or package data."""
    if path:
        with open(path, "r") as file:
            blueprint = json.load(file)
    else:
        with (
            resources.files("switch_interface.resources.layouts")
            .joinpath(DEFAULT_LAYOUT)
            .open("r") as file
        ):
            blueprint = json.load(file)

    _validate_layout(blueprint)

    page_objects = []
    try:
        for page in blueprint["pages"]:
            row_objects = []
            for row in page["rows"]:
                key_objects = []
                for key in row["keys"]:
                    key_objects.append(
                        Key(
                            key["label"],
                            key.get("action"),
                            key.get("mode", "tap"),
                            key.get("dwell") or key.get("dwell_mult"),
                        )
                    )
                row_objects.append(
                    KeyboardRow(
                        key_objects,
                        stretch=row.get("stretch", True),
                    )
                )
            page_objects.append(KeyboardPage(row_objects))
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Malformed keyboard layout: {exc}") from None

    return Keyboard(page_objects)
