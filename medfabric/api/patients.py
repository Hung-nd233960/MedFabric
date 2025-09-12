# pylint: disable=missing-function-docstring,missing-module-docstring
# medfabric/api/patients.py
from typing import Optional
import uuid as uuid_lib
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from medfabric.db.orm_model import Patient, Gender
from medfabric.db.pydantic_model import PatientRead, PatientCreate
from medfabric.api.data_sets import check_data_set_exists_by_uuid
from medfabric.api.errors import (
    PatientAlreadyExistsError,
    PatientInvalidDataError,
    DatabaseError,
)


def check_patient_exists_by_uuid(
    session: Session, patient_uuid: uuid_lib.UUID, data_set_uuid: uuid_lib.UUID
) -> bool:
    """
    Check if a patient with the given ID exists.

    Args:
        session (Session): SQLAlchemy DB session
        patient_uuid (uuid.UUID): ID of the patient to check
        data_set_uuid (uuid.UUID): UUID of the data set the patient belongs to

    Returns:
        True if exists, False otherwise
    """
    return (
        session.query(Patient)
        .filter_by(patient_uuid=patient_uuid, dataset_uuid=data_set_uuid)
        .one_or_none()
        is not None
    )


def check_patient_exists_by_id(
    session: Session, patient_id: str, data_set_uuid: uuid_lib.UUID
) -> bool:
    """
    Check if a patient with the given ID exists.

    Args:
        session (Session): SQLAlchemy DB session
        patient_id (str): ID of the patient to check
        data_set_uuid (uuid.UUID): UUID of the data set the patient belongs to

    Returns:
        True if exists, False otherwise
    """
    return (
        session.query(Patient)
        .filter_by(patient_id=patient_id, dataset_uuid=data_set_uuid)
        .one_or_none()
        is not None
    )


def add_patient(
    session: Session,
    patient_id: str,
    data_set_uuid: uuid_lib.UUID,
    patient_uuid: Optional[uuid_lib.UUID] = None,
    category: Optional[str] = None,
    age: Optional[int] = None,
    gender: Optional[Gender] = None,
) -> Patient:
    """
    Add a new patient to the database.

    Args:
        session (Session): SQLAlchemy DB session.
        patient_id (str): Unique ID for the patient.
        data_set_uuid (uuid.UUID): UUID of the data set the patient belongs to.
        patient_uuid (Optional[uuid.UUID]): UUID for the patient. If None, a new UUID will be generated.
        category (Optional[str]): Category of the patient.
        age (Optional[int]): Age of the patient.
        gender (Optional[Gender]): Gender of the patient.
    Returns:
        Patient: The created patient object.
    """
    try:
        add_patient_validator = PatientCreate(
            patient_id=patient_id,
            age=age,
            category=category,
            gender=gender,
            dataset_uuid=data_set_uuid,
            patient_uuid=patient_uuid,
        )
        data_set_uuid_ = add_patient_validator.dataset_uuid
        patient_id_ = add_patient_validator.patient_id
        category_ = add_patient_validator.category
        age_ = add_patient_validator.age
        gender_ = add_patient_validator.gender
        patient_uuid_ = add_patient_validator.patient_uuid
    except ValidationError as exc:
        raise PatientInvalidDataError(f"Invalid patient data: {exc}") from exc
    if not check_data_set_exists_by_uuid(session, data_set_uuid_):
        raise PatientInvalidDataError(f"Data set UUID does not exist: {data_set_uuid_}")
    if not patient_id_ or not patient_id_.strip():
        raise PatientInvalidDataError("Patient ID cannot be empty.")
    if check_patient_exists_by_id(session, patient_id_, data_set_uuid_):
        raise PatientAlreadyExistsError(
            f"Patient with ID {patient_id_} already exists."
        )
    if patient_uuid_ is not None:
        if check_patient_exists_by_uuid(session, patient_uuid_, data_set_uuid_):
            raise PatientAlreadyExistsError(
                f"Patient with UUID {patient_uuid_} already exists."
            )

    patient = Patient(
        patient_id=patient_id_,
        category=category_,
        age=age_,
        gender=gender_,
        dataset_uuid=data_set_uuid_,
        patient_uuid=patient_uuid_,
    )
    try:
        session.add(patient)
        session.commit()
        return patient
    except SQLAlchemyError as exc:
        session.rollback()
        raise DatabaseError(f"Failed to add patient: {exc}") from exc


def get_patient_by_id_and_dataset_uuid(
    session: Session, patient_id: str, data_set_uuid: uuid_lib.UUID
) -> Optional[PatientRead]:
    """
    Retrieve a patient by their ID.

    Args:
        session (Session): SQLAlchemy DB session
        patient_id (str): ID of the patient to retrieve
        data_set_uuid (uuid.UUID): UUID of the data set the patient belongs to

    Returns:
        PatientRead if found, None otherwise
    """
    patient_obj = (
        session.query(Patient)
        .filter_by(patient_id=patient_id, dataset_uuid=data_set_uuid)
        .one_or_none()
    )
    if patient_obj:
        return PatientRead.model_validate(patient_obj)
    return None


def get_patient_by_uuid(
    session: Session, patient_uuid: uuid_lib.UUID
) -> Optional[PatientRead]:
    """
    Retrieve a patient by their UUID.

    Args:
        session (Session): SQLAlchemy DB session
        patient_uuid (uuid.UUID): UUID of the patient to retrieve

    Returns:
        PatientRead if found, None otherwise
    """
    patient_obj = (
        session.query(Patient).filter_by(patient_uuid=patient_uuid).one_or_none()
    )
    if patient_obj:
        return PatientRead.model_validate(patient_obj)
    return None
