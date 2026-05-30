"""Loads about.toml from the project root once at startup; tracks startup time."""

import tomllib
import logging
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

logger = logging.getLogger(__name__)

_ABOUT_PATH = Path(__file__).parent.parent.parent / "about.toml"
_STARTUP_TIME: datetime | None = None


class AboutInfo(TypedDict, total=False):
    name: str
    version: str
    description: str
    creator: str
    institution: str
    contact_email: str
    project_url: str


def set_startup_time() -> None:
    global _STARTUP_TIME  # pylint: disable=global-statement
    _STARTUP_TIME = datetime.now(timezone.utc)


def get_startup_time() -> datetime | None:
    return _STARTUP_TIME


@lru_cache(maxsize=1)
def get_about() -> AboutInfo:
    if not _ABOUT_PATH.exists():
        logger.warning(
            "about.toml not found at %s — About endpoint will return empty data",
            _ABOUT_PATH,
        )
        return AboutInfo()
    with open(_ABOUT_PATH, "rb") as f:
        data = tomllib.load(f)
    info: AboutInfo = data.get("about", {})
    logger.info(
        "about.toml loaded — %s %s, creator: %s",
        info.get("name", "?"),
        info.get("version", "?"),
        info.get("creator", "?"),
    )
    return info
