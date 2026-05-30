"""Patient CRUD service."""

import uuid
from typing import List, Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import Gender, Patient
from app.services.errors import (
    DatabaseError,
    PatientAlreadyExistsError,
    PatientNotFoundError,
)


def create_patient(
    db: Session,
    patient_id: str,
    dataset_uuid: uuid.UUID,
    category: Optional[str] = None,
    age: Optional[int] = None,
    gender: Optional[Gender] = None,
) -> Patient:
    existing = (
        db.query(Patient)
        .filter(Patient.patient_id == patient_id, Patient.dataset_uuid == dataset_uuid)
        .first()
    )
    if existing:
        raise PatientAlreadyExistsError(
            f"Patient '{patient_id}' already exists in this dataset."
        )
    patient = Patient(
        patient_uuid=uuid.uuid4(),
        patient_id=patient_id,
        dataset_uuid=dataset_uuid,
        category=category,
        age=age,
        gender=gender,
    )
    try:
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient
    except IntegrityError as exc:
        db.rollback()
        raise PatientAlreadyExistsError(str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise DatabaseError(str(exc)) from exc


def get_patient(db: Session, patient_uuid: uuid.UUID) -> Patient:
    patient = db.query(Patient).filter(Patient.patient_uuid == patient_uuid).first()
    if not patient:
        raise PatientNotFoundError(f"Patient {patient_uuid} not found.")
    return patient


def list_patients(db: Session, dataset_uuid: uuid.UUID) -> List[Patient]:
    return (
        db.query(Patient)
        .filter(Patient.dataset_uuid == dataset_uuid)
        .order_by(Patient.patient_id)
        .all()
    )


def update_patient(
    db: Session,
    patient_uuid: uuid.UUID,
    category: Optional[str] = None,
    age: Optional[int] = None,
    gender: Optional[Gender] = None,
) -> Patient:
    patient = get_patient(db, patient_uuid)
    if category is not None:
        patient.category = category
    if age is not None:
        patient.age = age
    if gender is not None:
        patient.gender = gender
    db.commit()
    db.refresh(patient)
    return patient
