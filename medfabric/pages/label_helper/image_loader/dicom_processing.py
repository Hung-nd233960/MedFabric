"""DICOM processing helper functions."""

from typing import Dict, Tuple
from pathlib import Path
import numpy as np
from PIL import Image
import pydicom
from pydicom.errors import InvalidDicomError
from pydicom.dataset import FileDataset
from medfabric.api.errors import InvalidDicomFileError


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


### IN PROGRESS

# def load_dicom_folder(
#     folder_path: Path,
# ) -> Tuple[List[np.ndarray], List[Tuple[FileDataset, str]]]:
#     """
#     Load and normalize multiple DICOM files from disk paths or Streamlit uploads.

#     Args:
#         folder_path (Path): Path to the folder containing DICOM files.
#     Returns:
#         images: List of normalized uint8 numpy arrays (2D grayscale).
#         dicoms: List of (dicom, name) tuples.
#     """
#     dicoms: List[Tuple[FileDataset, str]] = []
#     images: List[np.ndarray] = []

#     for file_path in folder_path.iterdir():
#         if file_path.is_dir():
#             continue
#         if file_path.suffix.lower() not in {".dcm", "", ".dicom"}:
#             continue
#         if file_path.is_file():
#             try:
#                 dicom = pydicom.dcmread(file_path)
#                 dicoms.append((dicom, file_path.name))
#             except InvalidDicomError as e:
#                 print(f"Error reading DICOM file {file_path}: {e}")

#     def sort_key(x: Tuple[FileDataset, str]) -> float:
#         dicom: FileDataset = x[0]
#         return (
#             getattr(dicom, "InstanceNumber", None)
#             or getattr(dicom, "SliceLocation", None)
#             or 0
#         )

#     dicoms.sort(key=sort_key)

#     for dicom, _ in dicoms:
#         slope = getattr(dicom, "RescaleSlope", 1)
#         intercept = getattr(dicom, "RescaleIntercept", 0)
#         img = dicom.pixel_array.astype(np.int16) * slope + intercept

#     return images, dicoms


def load_raw_dicom_image(file_path: Path) -> Tuple[FileDataset, np.ndarray]:
    """
    Load a DICOM file and convert pixel data to Hounsfield Units (HU).
    Args:
        file_path (Path): Path to the DICOM file.
    Returns:
        Tuple[FileDataset, np.ndarray]: The DICOM dataset and the image in HU.
    """
    try:
        dcm_obj = pydicom.dcmread(file_path)
    except InvalidDicomError as e:
        raise InvalidDicomFileError(f"Invalid DICOM file: {file_path}") from e

    img = dcm_obj.pixel_array.astype(np.int16)

    # RescaleSlope và RescaleIntercept
    slope = getattr(dcm_obj, "RescaleSlope", 1)
    intercept = getattr(dcm_obj, "RescaleIntercept", 0)
    hu = img * slope + intercept
    return dcm_obj, hu


def apply_window(img: np.ndarray, center: float, width: float) -> Image.Image:
    """
    Apply windowing to a HU image, return image that is visible.
    Args:
        img (np.ndarray): Image in Hounsfield Units.
        center (int): Window center.
        width (int): Window width.
    Returns:
        Image.Image: The windowed image as a PIL Image.
    """
    low = center - width // 2
    high = center + width // 2
    windowed = np.clip(img, low, high)
    windowed = ((windowed - low) / (high - low) * 255).astype(np.uint8)
    image = Image.fromarray(windowed)
    return image


def dicom_image(file_path: Path, center: float, width: float) -> Image.Image:
    """
    Load a DICOM file and convert pixel data to a windowed PIL Image.

    Args:
        file_path (Path): Path to the DICOM file.
        center (float): Window center.
        width (float): Window width.

    Returns:
        Image.Image: The windowed image as a PIL Image.
    """
    _, hu = load_raw_dicom_image(file_path)
    windowed_image = apply_window(hu, center, width)
    return windowed_image


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
