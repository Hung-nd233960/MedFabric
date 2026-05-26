"""Dataset endpoints (admin-only write, authenticated read)."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import AnnotationSession, Doctors, ImageSet
from app.db.schemas import DataSetCreate, DataSetRead, DataSetUpdate
from app.deps import get_current_admin, get_current_doctor
from app.services.datasets import create_dataset, get_dataset, list_datasets, update_dataset
from app.services.errors import DataSetAlreadyExistsError, DataSetNotFoundError, InvalidDataSetError

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("/", response_model=List[DataSetRead])
def list_all_datasets(
    active_only: bool = True,
    db: Session = Depends(get_db),
    _=Depends(get_current_doctor),
):
    datasets = list_datasets(db, active_only=active_only)
    result = []
    for ds in datasets:
        total = (
            db.query(func.count(ImageSet.uuid))
            .filter(ImageSet.dataset_uuid == ds.dataset_uuid)
            .scalar() or 0
        )
        global_prog = (
            db.query(func.count(func.distinct(AnnotationSession.image_set_uuid)))
            .join(ImageSet, AnnotationSession.image_set_uuid == ImageSet.uuid)
            .join(Doctors, AnnotationSession.doctor_uuid == Doctors.uuid)
            .filter(
                ImageSet.dataset_uuid == ds.dataset_uuid,
                AnnotationSession.submitted_at.isnot(None),
                Doctors.is_test.is_(False),
            )
            .scalar() or 0
        )
        result.append(DataSetRead(
            dataset_uuid=ds.dataset_uuid,
            name=ds.name,
            description=ds.description,
            is_active=ds.is_active,
            created_at=ds.created_at,
            total_image_sets=total,
            global_progress=global_prog,
        ))
    return result


@router.post("/", response_model=DataSetRead, status_code=status.HTTP_201_CREATED)
def create_new_dataset(
    body: DataSetCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    try:
        return create_dataset(db, name=body.name, description=body.description)
    except DataSetAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except InvalidDataSetError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/{dataset_uuid}", response_model=DataSetRead)
def get_one_dataset(
    dataset_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    _=Depends(get_current_doctor),
):
    try:
        return get_dataset(db, dataset_uuid)
    except DataSetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/{dataset_uuid}", response_model=DataSetRead)
def update_one_dataset(
    dataset_uuid: uuid.UUID,
    body: DataSetUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    try:
        return update_dataset(
            db,
            dataset_uuid,
            description=body.description,
            is_active=body.is_active,
        )
    except DataSetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
