# medfabric/config.py
import tomllib
from pathlib import Path
from typing import Any


CONFIG_PATH = Path.cwd() / "config.toml"


def load_config() -> dict[str, Any]:
    """Load the full config.toml as a dict."""
    with CONFIG_PATH.open("rb") as f:
        return tomllib.load(f)


def get_paths() -> dict[str, str]:
    """Return paths from [path] section."""
    return load_config().get("path", {})


def get_image_adjustments() -> dict[str, Any]:
    """Return image adjustment defaults from [image_adjustments] section."""
    return load_config().get("image_adjustments", {})


PATHS = get_paths()
DEFAULT_IMAGE_ADJUSTMENT = get_image_adjustments()
DATA_PATH = PATHS.get("data", "/data")


DEFAULT_BRIGHTNESS = DEFAULT_IMAGE_ADJUSTMENT.get("default_brightness", 0)
DEFAULT_CONTRAST = DEFAULT_IMAGE_ADJUSTMENT.get("default_contrast", 1.0)
DEFAULT_FILTER = DEFAULT_IMAGE_ADJUSTMENT.get("default_filter", "None")
DEFAULT_WINDOW_WIDTH = 100
DEFAULT_WINDOW_LEVEL = 35
