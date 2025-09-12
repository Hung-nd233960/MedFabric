from enum import Enum
from typing import Dict, List, Tuple, Union
from pathlib import Path
from PIL import Image
from PIL import ImageEnhance
import numpy as np
import pydicom
from pydicom.dataset import FileDataset
import streamlit as st


class ImageType(Enum):
    DICOM = "DICOM"
    JPG_PNG = "JPG/PNG"


def apply_brightness_contrast_dcm(
    image: np.ndarray, brightness: int = 0, contrast: float = 1.0
) -> np.ndarray:
    """
    Apply brightness and contrast adjustment.

    Args:
        image: Grayscale image as numpy array.
        brightness: Value to add after scaling.
        contrast: Multiplicative factor for scaling.

    Returns:
        Adjusted image as uint8 numpy array.
    """
    img: np.ndarray = image.astype(np.float32)
    img = img * contrast + brightness
    img = np.clip(img, 0, 255)
    return img.astype(np.uint8)


def apply_brightness_contrast_jpg(
    image: Image.Image, brightness: int = 0, contrast: float = 1.0
) -> Image.Image:
    """
    Apply brightness and contrast adjustment for JPG/PNG images.

    Args:
        image: PIL Image.
        brightness: Value to add after scaling.
        contrast: Multiplicative factor for scaling.
    Returns:
        Adjusted image as PIL Image.
    """

    enhancer_contrast = ImageEnhance.Contrast(image)
    img = enhancer_contrast.enhance(contrast)

    enhancer_brightness = ImageEnhance.Brightness(img)
    img = enhancer_brightness.enhance(1 + brightness / 100.0)

    return img


# def apply_filter(image: np.ndarray, filter_type: str) -> np.ndarray:
#    """
#    Apply an image filter.
#
#    Args:
#        image: Grayscale or RGB image as numpy array.
#        filter_type: One of "Gaussian Blur", "Sharpen", "Edge Detection", "Original".
#
#    Returns:
#        Filtered image as numpy array.
#    """
#    if filter_type == "Gaussian Blur":
#        return cv2.GaussianBlur(image, (5, 5), 0)
#    elif filter_type == "Sharpen":
#        kernel: np.ndarray = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
#        return cv2.filter2D(image, -1, kernel)
#    elif filter_type == "Edge Detection":
#        return cv2.Canny(image, 100, 200)
#    else:
#        return image


def get_filter_explanation(filter_type: str) -> str:
    """
    Get a human-readable explanation of a filter.

    Args:
        filter_type: Filter name.

    Returns:
        Explanation string.
    """
    explanations: Dict[str, str] = {
        "Original": "No filter applied; view the raw image.",
        "Gaussian Blur": "Smooths the image to reduce noise and detail, useful for preprocessing.",
        "Sharpen": "Enhances edges and details to make structures more distinct.",
        "Edge Detection": "Detects boundaries using Canny algorithm, highlighting edges.",
    }
    return explanations.get(filter_type, "")


def dicom_to_dict_str(dicom: FileDataset) -> Dict[str, str]:
    """
    Convert DICOM metadata to a JSON-formatted string.

    Args:
        dicom: DICOM dataset.

    Returns:
        dicom_dict: Dictionary of DICOM tags and values.
    """
    dicom_dict: Dict[str, str] = {}
    for elem in dicom:
        if elem.VR != "SQ":  # skip sequences for simplicity
            tag_name: str = elem.keyword if elem.keyword else str(elem.tag)
            dicom_dict[tag_name] = str(elem.value)
    return dicom_dict


# def zoom_image(image: np.ndarray, zoom_factor: float) -> np.ndarray:
#    """
#    Apply zoom by cropping and resizing.
#
#    Args:
#        image: Grayscale image.
#        zoom_factor: Zoom multiplier (>1 means zoom in).
#
#    Returns:
#        Zoomed image as numpy array.
#    """
#    h, w = image.shape
#    new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
#    top: int = (h - new_h) // 2
#    left: int = (w - new_w) // 2
#    cropped: np.ndarray = image[top : top + new_h, left : left + new_w]
#    zoomed: np.ndarray = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
#    return zoomed


def load_multi_dicom(
    uploaded_files: List[str],
) -> Tuple[List[np.ndarray], List[Tuple[FileDataset, str]]]:
    """
    Load and normalize multiple DICOM files from disk paths or Streamlit uploads.

    Args:
        uploaded_files (List[str]): List of file paths or UploadedFile objects.

    Returns:
        images: List of normalized uint8 numpy arrays (2D grayscale).
        dicoms: List of (dicom, name) tuples.
    """
    dicoms: List[Tuple[FileDataset, str]] = []

    for file_obj in uploaded_files:
        if isinstance(file_obj, str):  # local file path
            dicom: FileDataset = pydicom.dcmread(file_obj)
            dicoms.append((dicom, file_obj))

    def sort_key(x: Tuple[FileDataset, str]) -> float:
        dicom: FileDataset = x[0]
        return (
            getattr(dicom, "InstanceNumber", None)
            or getattr(dicom, "SliceLocation", None)
            or 0
        )

    dicoms.sort(key=sort_key)

    images: List[np.ndarray] = []
    for dicom, _ in dicoms:
        img: np.ndarray = dicom.pixel_array.astype(np.float32)
        img -= np.min(img)
        if np.max(img) != 0:
            img /= np.max(img)
        img *= 255.0
        images.append(img.astype(np.uint8))

    return images, dicoms


def load_dicom_image(file_path: Path) -> np.ndarray:
    """
    Load a DICOM file from disk and normalize its pixel array to 0-255.

    Args:
        file_path: Path to the DICOM file.

    Returns:
        image: Normalized image as a uint8 numpy array (2D grayscale).
    """
    dicom: FileDataset = pydicom.dcmread(file_path)
    image: np.ndarray = dicom.pixel_array.astype(np.float32)
    image -= np.min(image)
    if np.max(image) != 0:
        image /= np.max(image)
    image *= 255.0
    return image.astype(np.uint8)


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


def load_image(file_path: Path) -> Tuple[ImageType, Union[np.ndarray, Image.Image]]:
    """
    Load an image from disk, supporting DICOM and JPG/PNG formats.

    Args:
        file_path (Path): Path to the image file.

    Returns:
        Tuple[str, Union[np.ndarray, Image.Image]]: A tuple containing:
            - The format of the image ("DICOM" or "JPG/PNG").
            - The loaded image as a numpy array (for DICOM) or PIL Image (for JPG/PNG).
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    image: Union[np.ndarray, Image.Image]
    if file_path.suffix.lower() in {".dcm", ".dicom"}:
        image = load_dicom_image(file_path)
        return ImageType.DICOM, image
    if file_path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
        image = load_jpg_image(file_path)
        return ImageType.JPG_PNG, image
    raise ValueError(f"Unsupported file type: {file_path.suffix}")


def render_image_to_st(
    path: Path,
    current_set_index: int,
    current_image_index: int,
    num_images: int,
    brightness: int = 0,
    contrast: float = 1.0,
) -> None:
    """
    Load and render an image to Streamlit with brightness/contrast adjustments."""

    type_, image = load_image(path)
    processed_image: Union[np.ndarray, Image.Image]
    if type_ == ImageType.DICOM and isinstance(image, np.ndarray):
        processed_image = apply_brightness_contrast_dcm(
            image,
            brightness,
            contrast,
        )
    elif type_ == ImageType.JPG_PNG and isinstance(image, Image.Image):
        processed_image = apply_brightness_contrast_jpg(
            image,
            brightness,
            contrast,
        )
    else:
        raise ValueError("Unsupported image type")
    st.image(
        processed_image,
        caption=(
            f"Set {current_set_index + 1} | "
            f"Image {current_image_index + 1} of "
            f"{num_images}"
        ),
        width="stretch",
        clamp=False,
    )


def extract_searchable_info(dicom: FileDataset) -> Dict[str, str]:
    """
    Extract key DICOM fields for search/display.

    Args:
        dicom: FileDataset.

    Returns:
        Dictionary with selected patient/study info.
    """
    return {
        "PatientName": str(getattr(dicom, "PatientName", "")),
        "PatientID": str(getattr(dicom, "PatientID", "")),
        "StudyDate": str(getattr(dicom, "StudyDate", "")),
        "Modality": str(getattr(dicom, "Modality", "")),
        "SliceThickness": str(getattr(dicom, "SliceThickness", "")),
        "PixelSpacing": str(getattr(dicom, "PixelSpacing", "")),
    }
