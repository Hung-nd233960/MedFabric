# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
# tests/patient_test.py
import pytest
import uuid as uuid_lib
from sqlalchemy.orm import Session
from medfabric.api.patients import add_patient, check_patient_exists_by_id
from medfabric.api.errors import (
    PatientAlreadyExistsError,
    PatientInvalidDataError,
)
from medfabric.db.orm_model import Gender


@pytest.fixture
def test_add_patient_success_minimal(db_session: Session, dataset_uuid):
    patient = add_patient(db_session, "p001", data_set_uuid=dataset_uuid)
    assert patient.patient_id == "p001"
    assert patient.category is None
    assert patient.age is None
    assert patient.gender is None
    assert (
        check_patient_exists_by_id(db_session, "p001", data_set_uuid=dataset_uuid)
        is True
    )


@pytest.mark.parametrize(
    "category, age, gender",
    [
        ("oncology", None, None),
        (None, 45, None),
        (None, None, Gender.Male),
        ("cardiology", 60, Gender.Female),
    ],
)
def test_add_patient_success_variations(
    db_session: Session, category, age, gender, dataset_uuid
):
    pid = f"p_{category}_{age}_{gender}".replace(" ", "_")
    patient = add_patient(
        db_session,
        pid,
        category=category,
        age=age,
        gender=gender,
        data_set_uuid=dataset_uuid,
    )
    assert patient.patient_id == pid
    assert patient.category == category
    assert patient.age == age
    assert patient.gender == gender


def test_add_patient_full_data(db_session: Session, dataset_uuid):
    uuid = uuid_lib.uuid4()
    patient = add_patient(
        db_session,
        "p003",
        category="neurology",
        age=30,
        gender=None,
        data_set_uuid=dataset_uuid,
        patient_uuid=uuid,
    )
    assert patient.patient_id == "p003"
    assert patient.category == "neurology"
    assert patient.age == 30
    assert patient.gender is None
    assert patient.patient_uuid == uuid


def test_add_patient_empty_id(db_session: Session, dataset_uuid):
    with pytest.raises(PatientInvalidDataError):
        add_patient(db_session, "", data_set_uuid=dataset_uuid)


def test_add_patient_already_exists(db_session: Session, dataset_uuid):
    add_patient(db_session, "p002", data_set_uuid=dataset_uuid)
    with pytest.raises(PatientAlreadyExistsError):
        add_patient(db_session, "p002", data_set_uuid=dataset_uuid)


def test_check_patient_exists_true_false(db_session: Session, dataset_uuid):
    assert (
        check_patient_exists_by_id(
            db_session, "doesnotexist", data_set_uuid=dataset_uuid
        )
        is False
    )
    add_patient(db_session, "p010", data_set_uuid=dataset_uuid)
    assert (
        check_patient_exists_by_id(db_session, "p010", data_set_uuid=dataset_uuid)
        is True
    )
