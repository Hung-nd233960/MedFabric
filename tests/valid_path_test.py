# pylint: disable = missing-module-docstring, missing-function-docstring
# tests/valid_path_test.py
import pytest
from medfabric.api.errors import InvalidImageSetError
from medfabric.api.utils.normalize_folder_path import normalize_folder_path


@pytest.mark.parametrize(
    "input_path, expected",
    [
        # ✅ Normal cases
        ("folder", "folder"),
        ("folder/subfolder", "folder/subfolder"),
        ("./folder", "folder"),
        ("./folder/./sub", "folder/sub"),
        ("folder\\sub", "folder/sub"),  # Windows backslash
        ("folder with spaces", "folder with spaces"),
        ("  folder  ", "folder"),  # Strip whitespace
        (None, None),
        ("", None),
        # ✅ Safe canonicalization
        ("folder//sub///deep", "folder/sub/deep"),
        ("./folder//", "folder"),
    ],
)
def test_valid_paths(input_path, expected):
    assert normalize_folder_path(input_path) == expected


@pytest.mark.parametrize(
    "bad_path",
    [
        "/absolute/path",  # Absolute paths not allowed
        "../escape",  # Parent traversal
        "folder/../secret",  # Hidden traversal
        "folder/\x00evil",  # Null byte
        "bad|name",  # Invalid char
        "name:with:colon",  # Invalid char
    ],
)
def test_invalid_paths(bad_path):
    with pytest.raises(InvalidImageSetError):
        normalize_folder_path(bad_path)
