"""Dataset endpoints (admin-only write, authenticated read)."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
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
    return list_datasets(db, active_only=active_only)


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
