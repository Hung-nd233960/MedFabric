"""Image (slice) endpoints — list slices and render DICOM as PNG."""

import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import Image, ImageSet
from app.db.schemas import ImageRead
from app.deps import get_current_doctor
from app.services.errors import ImageNotFoundError, ImageSetNotFoundError, InvalidDicomFileError
from app.services.image_loader.dicom_processing import render_dicom_as_png

router = APIRouter(prefix="/images", tags=["images"])

# Default CT brain window
_DEFAULT_WL = 35
_DEFAULT_WW = 100


@router.get("/by-image-set/{image_set_uuid}", response_model=List[ImageRead])
def list_images_for_set(
    image_set_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    _=Depends(get_current_doctor),
):
    img_set = db.query(ImageSet).filter(ImageSet.uuid == image_set_uuid).first()
    if not img_set:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ImageSet not found")
    return img_set.images


@router.get("/{image_uuid}/render")
def render_image(
    image_uuid: uuid.UUID,
    wl: Optional[int] = Query(default=None, description="Window level (Hounsfield)"),
    ww: Optional[int] = Query(default=None, description="Window width"),
    db: Session = Depends(get_db),
    _=Depends(get_current_doctor),
):
    """Render a DICOM slice as PNG with the given window settings."""
    img = db.query(Image).filter(Image.uuid == image_uuid).first()
    if not img:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    img_set = db.query(ImageSet).filter(ImageSet.uuid == img.image_set_uuid).first()
    if not img_set:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ImageSet not found")

    # Resolve window: query param > image set default > hardcoded brain window
    center = wl if wl is not None else (img_set.image_window_level or _DEFAULT_WL)
    width = ww if ww is not None else (img_set.image_window_width or _DEFAULT_WW)

    folder = Path(img_set.folder_path)
    file_path = folder / img.image_name
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DICOM file not found on disk")

    try:
        png_bytes = render_dicom_as_png(file_path, center=float(center), width=float(width))
    except InvalidDicomFileError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return Response(content=png_bytes, media_type="image/png")
