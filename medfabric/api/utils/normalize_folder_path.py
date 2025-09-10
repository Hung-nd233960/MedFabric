# pylint: disable = missing-module-docstring, missing-function-docstring
# /medfabric/api/utils/normalize_folder_path.py
from typing import Optional
from pathlib import PurePosixPath
import re
from medfabric.api.errors import InvalidImageSetError


def normalize_folder_path(folder_path: str) -> Optional[str]:
    if not folder_path:
        return None
    folder_path = folder_path.strip()
    if "\x00" in folder_path:
        raise InvalidImageSetError("Folder path contains null byte.")

    normalized = folder_path.replace("\\", "/")

    if normalized.startswith("./"):
        normalized = normalized[2:]

    # Strip whitespace and null bytes

    # Normalize to POSIX style
    p = PurePosixPath(normalized)

    # Disallow absolute paths (security)
    if p.is_absolute():
        raise InvalidImageSetError("Folder path must be relative.")

    # Disallow parent traversal
    if any(part == ".." for part in p.parts):
        raise InvalidImageSetError("Folder path must not contain '..' components.")

    # Validate allowed characters for each part
    allowed = re.compile(r"^[A-Za-z0-9._\- ]*$")
    for part in p.parts:
        if part in ("", "."):
            continue
        if not allowed.fullmatch(part):
            raise InvalidImageSetError(
                f"Invalid characters in folder path component: {part}"
            )

    # Return canonical normalized string (no leading './')
    return str(p)
