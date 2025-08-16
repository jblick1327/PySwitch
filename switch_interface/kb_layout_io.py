import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import List, Optional

from jsonschema import ValidationError, validate

from .kb_layout import Key, Keyboard, KeyboardPage, KeyboardRow

DEFAULT_LAYOUT = (
    "qwerty_full.json"  # Updated default to the comprehensive QWERTY layout
)


@dataclass
class LayoutMetadata:
    """Metadata for keyboard layouts to describe their features and intended use."""

    name: str
    description: str
    difficulty: str  # "beginner", "intermediate", "advanced"
    features: List[str]  # ["predictive_text", "numbers", "punctuation", etc.]
    target_users: Optional[List[str]] = None
    scan_complexity: Optional[str] = None  # "low", "medium", "high"

    @classmethod
    def from_dict(cls, data: dict) -> "LayoutMetadata":
        """Create a LayoutMetadata instance from a dictionary."""
        return cls(
            name=data.get("name", "Unnamed Layout"),
            description=data.get("description", ""),
            difficulty=data.get("difficulty", "intermediate"),
            features=data.get("features", []),
            target_users=data.get("target_users"),
            scan_complexity=data.get("scan_complexity"),
        )


_SCHEMA = {
    "type": "object",
    "properties": {
        "metadata": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "difficulty": {
                    "type": "string",
                    "enum": ["beginner", "intermediate", "advanced"],
                },
                "features": {"type": "array", "items": {"type": "string"}},
                "target_users": {"type": "array", "items": {"type": "string"}},
                "scan_complexity": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
            },
            "required": ["name", "description", "difficulty", "features"],
        },
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
        },
    },
    "required": ["pages"],
}


def _validate_layout(data: dict) -> None:
    try:
        validate(data, _SCHEMA)
    except ValidationError as exc:
        raise ValueError(f"Invalid keyboard layout: {exc.message}") from None


def load_keyboard(path: str | None = None) -> tuple[Keyboard, Optional[LayoutMetadata]]:
    """Load a :class:`Keyboard` definition from ``path`` or package data.

    Returns:
        A tuple containing the Keyboard object and its metadata (if available)
    """
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

    # Extract metadata if available
    metadata = None
    if "metadata" in blueprint:
        metadata = LayoutMetadata.from_dict(blueprint["metadata"])

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

    return Keyboard(page_objects), metadata


def get_available_layouts() -> List[tuple[str, Optional[LayoutMetadata]]]:
    """Get a list of all available layouts with their metadata.

    Returns:
        A list of tuples containing the layout filename and its metadata
    """
    layouts = []
    layout_dir = resources.files("switch_interface.resources.layouts")

    for file_path in layout_dir.iterdir():
        if file_path.name.endswith(".json"):
            try:
                with file_path.open("r") as file:
                    data = json.load(file)

                metadata = None
                if "metadata" in data:
                    metadata = LayoutMetadata.from_dict(data["metadata"])

                layouts.append((file_path.name, metadata))
            except (json.JSONDecodeError, ValueError):
                # Skip invalid layout files
                continue

    return layouts


def get_default_layout() -> str:
    """Return the best default layout for new users based on preferred order."""
    preferred_order = [
        "qwerty_full.json",  # Complete QWERTY with all features
        "simple_alphabet.json",  # Simple alphabetical for beginners
        "pred_test.json",  # Fallback to existing layouts
        "basic_test.json",
    ]

    available_layouts = [layout[0] for layout in get_available_layouts()]

    # Return first available layout from preferred list
    for layout in preferred_order:
        if layout in available_layouts:
            return layout

    # If none of the preferred layouts are available, return the first available
    return available_layouts[0] if available_layouts else DEFAULT_LAYOUT
