from __future__ import annotations

import json
import os
from pathlib import Path

from appdirs import user_config_dir

CONFIG_DIR = Path(user_config_dir("switch_interface"))
CONFIG_FILE = CONFIG_DIR / "config.json"

SCAN_PRESETS = {
    "slow": 0.7,
    "medium": 0.45,
    "fast": 0.25,
}


def exists(path: Path = CONFIG_FILE) -> bool:
    return Path(path).exists()


def load(path: Path = CONFIG_FILE) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save(cfg: dict, path: Path = CONFIG_FILE) -> None:
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f)


def get_scan_interval(preset: str) -> float:
    return SCAN_PRESETS[preset.lower()]
