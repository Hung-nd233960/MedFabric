from typing import Dict, List, Tuple
from pathlib import Path
import cv2
import numpy as np
import pydicom
from pydicom.dataset import FileDataset


def apply_brightness_contrast(
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


def apply_filter(image: np.ndarray, filter_type: str) -> np.ndarray:
    """
    Apply an image filter.

    Args:
        image: Grayscale or RGB image as numpy array.
        filter_type: One of "Gaussian Blur", "Sharpen", "Edge Detection", "Original".

    Returns:
        Filtered image as numpy array.
    """
    if filter_type == "Gaussian Blur":
        return cv2.GaussianBlur(image, (5, 5), 0)
    elif filter_type == "Sharpen":
        kernel: np.ndarray = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        return cv2.filter2D(image, -1, kernel)
    elif filter_type == "Edge Detection":
        return cv2.Canny(image, 100, 200)
    else:
        return image


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


def zoom_image(image: np.ndarray, zoom_factor: float) -> np.ndarray:
    """
    Apply zoom by cropping and resizing.

    Args:
        image: Grayscale image.
        zoom_factor: Zoom multiplier (>1 means zoom in).

    Returns:
        Zoomed image as numpy array.
    """
    h, w = image.shape
    new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
    top: int = (h - new_h) // 2
    left: int = (w - new_w) // 2
    cropped: np.ndarray = image[top : top + new_h, left : left + new_w]
    zoomed: np.ndarray = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
    return zoomed


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


def load_dicom_image(file_path: Path) -> Tuple[np.ndarray, FileDataset]:
    """
    Load a DICOM file from disk and normalize its pixel array to 0-255.

    Args:
        file_path: Path to the DICOM file.

    Returns:
        image: Normalized image as a uint8 numpy array (2D grayscale).
        dicom: The full pydicom FileDataset.
    """
    dicom: FileDataset = pydicom.dcmread(file_path)
    image: np.ndarray = dicom.pixel_array.astype(np.float32)
    image -= np.min(image)
    if np.max(image) != 0:
        image /= np.max(image)
    image *= 255.0
    return image.astype(np.uint8), dicom


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
