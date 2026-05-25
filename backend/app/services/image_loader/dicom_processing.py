"""DICOM processing helpers (ported from medfabric.pages.label_helper.image_loader)."""

import io
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pydicom
from PIL import Image
from pydicom.dataset import FileDataset
from pydicom.errors import InvalidDicomError

from app.services.errors import InvalidDicomFileError


def load_raw_dicom_image(file_path: Path) -> Tuple[FileDataset, np.ndarray]:
    """Load DICOM and convert pixel array to Hounsfield Units."""
    try:
        dcm = pydicom.dcmread(str(file_path))
    except InvalidDicomError as exc:
        raise InvalidDicomFileError(f"Invalid DICOM file: {file_path}") from exc

    img = dcm.pixel_array.astype(np.float32)
    slope = float(getattr(dcm, "RescaleSlope", 1))
    intercept = float(getattr(dcm, "RescaleIntercept", 0))
    hu = img * slope + intercept
    return dcm, hu


def apply_window(hu: np.ndarray, center: float, width: float) -> Image.Image:
    """Apply windowing to HU array and return a PIL grayscale image."""
    low = center - width / 2
    high = center + width / 2
    windowed = np.clip(hu, low, high)
    windowed = ((windowed - low) / (high - low) * 255).astype(np.uint8)
    return Image.fromarray(windowed).convert("L")


def render_dicom_as_png(file_path: Path, center: float, width: float) -> bytes:
    """Render a DICOM slice with the given window settings and return PNG bytes."""
    _, hu = load_raw_dicom_image(file_path)
    img = apply_window(hu, center, width)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def extract_dicom_window(file_path: Path) -> Tuple[Optional[int], Optional[int]]:
    """Read WindowCenter / WindowWidth from DICOM header without loading pixel data."""
    try:
        dcm = pydicom.dcmread(str(file_path), stop_before_pixels=True)
        wl = getattr(dcm, "WindowCenter", None)
        ww = getattr(dcm, "WindowWidth", None)
        if wl is not None:
            wl = int(wl) if not hasattr(wl, "__iter__") else int(wl[0])
        if ww is not None:
            ww = int(ww) if not hasattr(ww, "__iter__") else int(ww[0])
        return wl, ww
    except Exception:
        return None, None


def dicom_to_metadata(file_path: Path) -> Dict[str, str]:
    """Extract a searchable subset of DICOM metadata."""
    try:
        dcm = pydicom.dcmread(str(file_path), stop_before_pixels=True)
    except InvalidDicomError as exc:
        raise InvalidDicomFileError(f"Invalid DICOM file: {file_path}") from exc
    keys = [
        "PatientName", "PatientID", "StudyDate", "Modality",
        "SliceThickness", "PixelSpacing", "WindowCenter", "WindowWidth",
    ]
    return {k: str(getattr(dcm, k, "")) for k in keys}
