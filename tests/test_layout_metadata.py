import json
import os
import tempfile
from pathlib import Path

import pytest

from switch_interface.kb_layout_io import (
    LayoutMetadata,
    load_keyboard,
    get_available_layouts,
    get_default_layout
)


def test_layout_metadata_from_dict():
    """Test creating LayoutMetadata from a dictionary."""
    metadata_dict = {
        "name": "Test Layout",
        "description": "A test layout",
        "difficulty": "intermediate",
        "features": ["test_feature"],
        "target_users": ["testers"],
        "scan_complexity": "medium"
    }
    
    metadata = LayoutMetadata.from_dict(metadata_dict)
    
    assert metadata.name == "Test Layout"
    assert metadata.description == "A test layout"
    assert metadata.difficulty == "intermediate"
    assert metadata.features == ["test_feature"]
    assert metadata.target_users == ["testers"]
    assert metadata.scan_complexity == "medium"


def test_load_keyboard_with_metadata():
    """Test loading a keyboard with metadata."""
    # Create a temporary layout file with metadata
    layout_data = {
        "metadata": {
            "name": "Test Layout",
            "description": "A test layout",
            "difficulty": "beginner",
            "features": ["test_feature"]
        },
        "pages": [
            {
                "rows": [
                    {
                        "keys": [
                            {"label": "a"}
                        ]
                    }
                ]
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as temp_file:
        json.dump(layout_data, temp_file)
        temp_path = temp_file.name
    
    try:
        # Load the keyboard with metadata
        keyboard, metadata = load_keyboard(temp_path)
        
        # Check that the keyboard was loaded correctly
        assert len(keyboard) == 1  # One page
        assert len(keyboard[0]) == 1  # One row
        assert len(keyboard[0][0]) == 1  # One key
        assert keyboard[0][0][0].label == "a"
        
        # Check that the metadata was loaded correctly
        assert metadata is not None
        assert metadata.name == "Test Layout"
        assert metadata.description == "A test layout"
        assert metadata.difficulty == "beginner"
        assert metadata.features == ["test_feature"]
    finally:
        # Clean up the temporary file
        os.unlink(temp_path)


def test_get_available_layouts():
    """Test getting available layouts with metadata."""
    layouts = get_available_layouts()
    
    # Check that we have at least the two layouts we created
    assert len(layouts) >= 2
    
    # Check that our layouts are in the list
    layout_names = [layout[0] for layout in layouts]
    assert "qwerty_full.json" in layout_names
    assert "simple_alphabet.json" in layout_names
    
    # Check that the metadata is loaded correctly
    for name, metadata in layouts:
        if name == "qwerty_full.json":
            assert metadata is not None
            assert metadata.name == "Complete QWERTY Layout"
            assert "numbers" in metadata.features
            assert "punctuation" in metadata.features
            assert metadata.difficulty == "intermediate"
        
        if name == "simple_alphabet.json":
            assert metadata is not None
            assert metadata.name == "Simple Alphabet Layout"
            assert "alphabetical_order" in metadata.features
            assert "predictive_text" in metadata.features
            assert metadata.difficulty == "beginner"


def test_get_default_layout():
    """Test getting the default layout."""
    default_layout = get_default_layout()
    
    # The default should be qwerty_full.json
    assert default_layout == "qwerty_full.json"