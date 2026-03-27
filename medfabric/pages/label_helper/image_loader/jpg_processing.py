from pathlib import Path
from PIL import Image


def load_jpg_image(file_path: Path) -> Image.Image:
    """
    Load a JPG/PNG image from disk.

    Args:
        file_path (Path): Path to the JPG or PNG file.

    Returns:
        Image.Image: The loaded image (original mode).
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

    return Image.open(file_path)


def jpg_image(file_path: Path) -> Image.Image:
    """
    Render a JPG/PNG image to Streamlit.

    Args:
        file_path (Path): Path to the JPG or PNG file.
    """
    image = load_jpg_image(file_path)
    return image
