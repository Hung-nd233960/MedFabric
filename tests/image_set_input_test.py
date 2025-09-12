# pylint: disable=missing-function-docstring,missing-module-docstring
# tests/image_set_input.py
import pytest
import uuid as uuid_lib
from medfabric.db.orm_model import ImageSet
from medfabric.api.errors import (
    PatientNotFoundError,
    #    ImageSetAlreadyExistsError,
    InvalidImageSetError,
)
from medfabric.api.image_set_input import add_image_set
from medfabric.api.patients import add_patient


def test_add_image_set_success(db_session, dataset_uuid):
    # Add a patient first
    patient = add_patient(
        db_session,
        "patient123",
        category="oncology",
        age=50,
        data_set_uuid=dataset_uuid,
    )
    # Call the function
    image_set = add_image_set(
        session=db_session,
        image_set_name="set1",
        patient_uuid=patient.patient_uuid,
        folder_path="data/patient123/set1",
        num_images=5,
        description="Test scan",
        dataset_uuid=dataset_uuid,
    )

    assert image_set.image_set_name == "set1"
    assert image_set.num_images == 5
    assert image_set.patient_uuid == patient.patient_uuid
    assert image_set.folder_path == "data/patient123/set1"
    assert image_set.description == "Test scan"


def test_empty_image_set_id(db_session, dataset_uuid):
    patient = add_patient(
        db_session,
        "patient_empty_id",
        category="oncology",
        age=50,
        data_set_uuid=dataset_uuid,
    )
    with pytest.raises(InvalidImageSetError):
        add_image_set(
            db_session,
            "",
            patient_uuid=patient.patient_uuid,
            num_images=3,
            dataset_uuid=dataset_uuid,
            folder_path="path/to/set",
        )


def test_add_image_set_patient_not_found(db_session, dataset_uuid):
    with pytest.raises(PatientNotFoundError):
        add_image_set(
            db_session,
            "set2",
            4,
            patient_uuid=uuid_lib.uuid4(),
            dataset_uuid=dataset_uuid,
            folder_path="path/to/set2",
        )


def test_add_image_set_invalid_num_images(db_session, dataset_uuid):
    patient = add_patient(
        db_session,
        "patient_invalid_images",
        category="oncology",
        age=50,
        data_set_uuid=dataset_uuid,
    )
    with pytest.raises(InvalidImageSetError):
        add_image_set(
            db_session,
            "set3",
            0,
            dataset_uuid=dataset_uuid,
            patient_uuid=patient.patient_uuid,
            folder_path="path/to/set3",
        )  # zero images


def test_get_image_set_success(db_session, dataset_uuid):
    # Add a patient first
    patient = add_patient(
        db_session,
        "patient456",
        category="cardiology",
        age=60,
        data_set_uuid=dataset_uuid,
    )
    # Add an image set
    add_image_set(
        session=db_session,
        image_set_name="set2",
        patient_uuid=patient.patient_uuid,
        num_images=10,
        description="Heart scan",
        dataset_uuid=dataset_uuid,
        folder_path="data/patient456/set2",
    )

    # Retrieve the image set
    image_set = db_session.query(ImageSet).filter_by(image_set_name="set2").first()
    assert image_set is not None
    assert image_set.image_set_name == "set2"
    assert image_set.num_images == 10
    assert image_set.patient_uuid == patient.patient_uuid
    assert image_set.description == "Heart scan"


def test_get_image_set_not_found(db_session):
    image_set = (
        db_session.query(ImageSet).filter_by(image_set_name="nonexistent").first()
    )
    assert image_set is None


# def test_add_image_set_already_exists(db_session):
#    existing = ImageSet(
#        image_set_id="set1",
#        patient_id=None,
#        num_images=3,
#        folder_path="/data/none/set1",
#    )
#    db_session.add(existing)
#    db_session.commit()
#
#    with pytest.raises(ImageSetAlreadyExistsError):
#        add_image_set(db_session, "set1", 5)
