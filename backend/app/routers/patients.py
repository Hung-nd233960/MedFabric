"""Patient endpoints (admin-only write, authenticated read)."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.schemas import PatientCreate, PatientRead, PatientUpdate
from app.deps import get_current_admin, get_current_doctor
from app.services.errors import (
    PatientAlreadyExistsError,
    PatientNotFoundError,
)
from app.services.patients import (
    create_patient,
    get_patient,
    list_patients,
    update_patient,
)

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/by-dataset/{dataset_uuid}", response_model=List[PatientRead])
def list_by_dataset(
    dataset_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    _=Depends(get_current_doctor),
):
    return list_patients(db, dataset_uuid)


@router.post("/", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_new_patient(
    body: PatientCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    try:
        return create_patient(
            db,
            patient_id=body.patient_id,
            dataset_uuid=body.dataset_uuid,
            category=body.category,
            age=body.age,
            gender=body.gender,
        )
    except PatientAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{patient_uuid}", response_model=PatientRead)
def get_one_patient(
    patient_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    _=Depends(get_current_doctor),
):
    try:
        return get_patient(db, patient_uuid)
    except PatientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/{patient_uuid}", response_model=PatientRead)
def update_one_patient(
    patient_uuid: uuid.UUID,
    body: PatientUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    try:
        return update_patient(
            db,
            patient_uuid,
            category=body.category,
            age=body.age,
            gender=body.gender,
        )
    except PatientNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
