"""ImageSet registration and management service."""

import uuid
from pathlib import Path
from typing import List, Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Image, ImageFormat, ImageSet
from app.services.errors import (
    DatabaseError,
    ImageSetAlreadyExistsError,
    ImageSetNotFoundError,
    InvalidImageSetPathError,
)

settings = get_settings()

_DICOM_EXTENSIONS = {".dcm", ".dicom", ""}


def _scan_folder(folder_path: Path) -> List[Path]:
    """Return sorted list of image files from a folder (flat or one-level nested)."""
    files: List[Path] = []
    for p in sorted(folder_path.iterdir()):
        if p.is_file() and p.suffix.lower() in _DICOM_EXTENSIONS:
            files.append(p)
    return files


def _auto_window_from_dicom(folder_path: Path):
    """Read WL/WW from the first DICOM file in the folder. Returns (wl, ww) or (None, None)."""
    try:
        import pydicom

        for p in sorted(folder_path.iterdir()):
            if p.is_file() and p.suffix.lower() in _DICOM_EXTENSIONS:
                dcm = pydicom.dcmread(str(p), stop_before_pixels=True)
                wl = getattr(dcm, "WindowCenter", None)
                ww = getattr(dcm, "WindowWidth", None)
                if wl is not None and ww is not None:
                    wl = int(wl) if not hasattr(wl, "__iter__") else int(wl[0])
                    ww = int(ww) if not hasattr(ww, "__iter__") else int(ww[0])
                    return wl, ww
    except Exception:
        pass
    return None, None


def register_image_set(
    db: Session,
    patient_uuid: uuid.UUID,
    dataset_uuid: uuid.UUID,
    image_set_name: str,
    folder_path: str,
    image_format: ImageFormat = ImageFormat.DICOM,
    image_window_level: Optional[int] = None,
    image_window_width: Optional[int] = None,
    description: Optional[str] = None,
    icd_code: Optional[str] = None,
) -> ImageSet:
    abs_path = Path(folder_path)
    if not abs_path.is_absolute():
        abs_path = settings.dataset_root / folder_path
    if not abs_path.exists() or not abs_path.is_dir():
        raise InvalidImageSetPathError(f"Folder not found: {abs_path}")

    image_files = _scan_folder(abs_path)
    if not image_files:
        raise InvalidImageSetPathError(f"No image files found in: {abs_path}")

    # Auto-read window params if not supplied
    if image_window_level is None or image_window_width is None:
        auto_wl, auto_ww = _auto_window_from_dicom(abs_path)
        if image_window_level is None:
            image_window_level = auto_wl
        if image_window_width is None:
            image_window_width = auto_ww

    image_set = ImageSet(
        uuid=uuid.uuid4(),
        dataset_uuid=dataset_uuid,
        patient_uuid=patient_uuid,
        image_set_name=image_set_name,
        image_format=image_format,
        image_window_level=image_window_level,
        image_window_width=image_window_width,
        num_images=len(image_files),
        folder_path=str(abs_path),
        description=description,
        icd_code=icd_code,
    )

    try:
        db.add(image_set)
        db.flush()  # get PK before inserting images

        for idx, fp in enumerate(image_files):
            image = Image(
                uuid=uuid.uuid4(),
                image_name=fp.name,
                image_set_uuid=image_set.uuid,
                slice_index=idx,
            )
            db.add(image)

        db.commit()
        db.refresh(image_set)
        return image_set

    except IntegrityError as exc:
        db.rollback()
        raise ImageSetAlreadyExistsError(
            f"ImageSet '{image_set_name}' already exists for this patient."
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise DatabaseError(str(exc)) from exc


def get_image_set(db: Session, image_set_uuid: uuid.UUID) -> ImageSet:
    img_set = db.query(ImageSet).filter(ImageSet.uuid == image_set_uuid).first()
    if not img_set:
        raise ImageSetNotFoundError(f"ImageSet {image_set_uuid} not found.")
    return img_set


def list_image_sets(
    db: Session,
    dataset_uuid: uuid.UUID,
    active_only: bool = True,
) -> List[ImageSet]:
    q = db.query(ImageSet).filter(ImageSet.dataset_uuid == dataset_uuid)
    if active_only:
        q = q.filter(ImageSet.is_active.is_(True))
    return q.order_by(ImageSet.image_set_name).all()


def update_image_set(
    db: Session,
    image_set_uuid: uuid.UUID,
    image_window_level: Optional[int] = None,
    image_window_width: Optional[int] = None,
    description: Optional[str] = None,
    icd_code: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> ImageSet:
    img_set = get_image_set(db, image_set_uuid)
    if image_window_level is not None:
        img_set.image_window_level = image_window_level
    if image_window_width is not None:
        img_set.image_window_width = image_window_width
    if description is not None:
        img_set.description = description
    if icd_code is not None:
        img_set.icd_code = icd_code
    if is_active is not None:
        img_set.is_active = is_active
    db.commit()
    db.refresh(img_set)
    return img_set
