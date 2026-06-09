"""DICOM processing helpers (ported from medfabric.pages.label_helper.image_loader)."""

import io
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pydicom
from PIL import Image
from pydicom.dataset import FileDataset
from pydicom.errors import InvalidDicomError

from app.db.models import Gender
from app.services.errors import InvalidDicomFileError

# PatientAge (0010,1010) is formatted as nnnX where X is D/W/M/Y, e.g. "054Y".
_AGE_RE = re.compile(r"^(\d{1,3})\s*([DWMY])?$", re.IGNORECASE)
_AGE_UNIT_DIVISOR = {"Y": 1.0, "M": 12.0, "W": 52.0, "D": 365.0}

# PatientSex (0010,0040): M / F / O (Other/Unknown).
_SEX_MAP = {"M": Gender.Male, "F": Gender.Female, "O": Gender.Other}


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
        "PatientName",
        "PatientID",
        "StudyDate",
        "Modality",
        "SliceThickness",
        "PixelSpacing",
        "WindowCenter",
        "WindowWidth",
    ]
    return {k: str(getattr(dcm, k, "")) for k in keys}


def _parse_dicom_age(raw_age, birth_date, study_date) -> Optional[int]:
    """Resolve patient age in whole years from DICOM tags.

    Prefers the PatientAge tag (e.g. "054Y", also handles D/W/M units); falls
    back to PatientBirthDate vs StudyDate when PatientAge is absent/unparseable.
    """
    if raw_age:
        m = _AGE_RE.match(str(raw_age).strip())
        if m:
            value = int(m.group(1))
            unit = (m.group(2) or "Y").upper()
            years = int(value / _AGE_UNIT_DIVISOR.get(unit, 1.0))
            if 0 <= years <= 150:
                return years

    if birth_date and study_date:
        bd, sd = str(birth_date).strip(), str(study_date).strip()
        if len(bd) == 8 and len(sd) == 8 and bd.isdigit() and sd.isdigit():
            years = (int(sd) - int(bd)) // 10000
            if 0 <= years <= 150:
                return years
    return None


def extract_patient_demographics(
    file_path: Path,
) -> Tuple[Optional[int], Optional[Gender]]:
    """Read patient age (years) and sex from a DICOM header.

    Returns ``(age, gender)`` with either element ``None`` when the source tags
    are missing or unparseable. Never raises on malformed DICOM — demographic
    backfill is best-effort and must not block image-set registration.
    """
    try:
        dcm = pydicom.dcmread(str(file_path), stop_before_pixels=True, force=True)
    except Exception:
        return None, None

    age = _parse_dicom_age(
        getattr(dcm, "PatientAge", None),
        getattr(dcm, "PatientBirthDate", None),
        getattr(dcm, "StudyDate", None),
    )

    sex_raw = str(getattr(dcm, "PatientSex", "") or "").strip().upper()
    gender = _SEX_MAP.get(sex_raw)

    return age, gender
