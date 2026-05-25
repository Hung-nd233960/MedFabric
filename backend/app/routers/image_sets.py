"""ImageSet endpoints."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import AnnotationSession, ImageSet
from app.db.schemas import ImageSetCreate, ImageSetRead, ImageSetUpdate, ImageSetWithProgress
from app.deps import get_current_admin, get_current_doctor
from app.db.models import Doctors
from app.services.errors import (
    ImageSetAlreadyExistsError,
    ImageSetNotFoundError,
    InvalidImageSetPathError,
)
from app.services.image_sets import (
    get_image_set,
    list_image_sets,
    register_image_set,
    update_image_set,
)

router = APIRouter(prefix="/image-sets", tags=["image-sets"])


@router.get("/by-dataset/{dataset_uuid}", response_model=List[ImageSetWithProgress])
def list_for_dataset(
    dataset_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    """Returns image sets with per-doctor evaluated flag and total evaluator count."""
    image_sets = list_image_sets(db, dataset_uuid)

    # Build progress maps in one query each to avoid N+1
    submitted_by_me = {
        row.image_set_uuid
        for row in db.query(AnnotationSession.image_set_uuid)
        .filter(
            AnnotationSession.doctor_uuid == doctor.uuid,
            AnnotationSession.submitted_at.isnot(None),
        )
        .all()
    }

    evaluator_counts = dict(
        db.query(
            AnnotationSession.image_set_uuid,
            func.count(func.distinct(AnnotationSession.doctor_uuid)),
        )
        .filter(AnnotationSession.submitted_at.isnot(None))
        .group_by(AnnotationSession.image_set_uuid)
        .all()
    )

    result = []
    for img_set in image_sets:
        result.append(
            ImageSetWithProgress(
                uuid=img_set.uuid,
                dataset_uuid=img_set.dataset_uuid,
                patient_uuid=img_set.patient_uuid,
                image_set_name=img_set.image_set_name,
                image_format=img_set.image_format,
                image_window_level=img_set.image_window_level,
                image_window_width=img_set.image_window_width,
                num_images=img_set.num_images,
                description=img_set.description,
                icd_code=img_set.icd_code,
                is_active=img_set.is_active,
                evaluated_by_me=img_set.uuid in submitted_by_me,
                total_evaluators=evaluator_counts.get(img_set.uuid, 0),
            )
        )
    return result


@router.post("/", response_model=ImageSetRead, status_code=status.HTTP_201_CREATED)
def register_new_image_set(
    body: ImageSetCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    try:
        return register_image_set(
            db,
            patient_uuid=body.patient_uuid,
            dataset_uuid=body.dataset_uuid,
            image_set_name=body.image_set_name,
            folder_path=body.folder_path,
            image_format=body.image_format,
            image_window_level=body.image_window_level,
            image_window_width=body.image_window_width,
            description=body.description,
            icd_code=body.icd_code,
        )
    except InvalidImageSetPathError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except ImageSetAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{image_set_uuid}", response_model=ImageSetRead)
def get_one_image_set(
    image_set_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    _=Depends(get_current_doctor),
):
    try:
        return get_image_set(db, image_set_uuid)
    except ImageSetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/{image_set_uuid}", response_model=ImageSetRead)
def update_one_image_set(
    image_set_uuid: uuid.UUID,
    body: ImageSetUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    try:
        return update_image_set(
            db,
            image_set_uuid,
            image_window_level=body.image_window_level,
            image_window_width=body.image_window_width,
            description=body.description,
            icd_code=body.icd_code,
            is_active=body.is_active,
        )
    except ImageSetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
