# pylint: disable=missing-function-docstring, missing-module-docstring
# tests/get_evaluated_sets_test.py
from typing import List
import pytest
from sqlalchemy.orm import Session as db_Session
from medfabric.db.orm_model import (
    Doctors,
    Session,
    ImageSet,
    Image,
    Region,
)
from medfabric.api.sessions import create_session
from medfabric.api.credentials import register_doctor
from medfabric.api.image_set_input import add_image_set
from medfabric.api.image_input import add_image
from medfabric.api.patients import add_patient
from medfabric.api.image_set_evaluation_input import add_evaluate_image_set
from medfabric.api.image_evaluation_input import add_evaluate_image
from medfabric.api.get_evaluated_sets import get_doctor_image_sets
from medfabric.db.orm_model import ImageSetUsability


# Doctor 1 evaluate set 0 and 1
# Doctor 2 evaluate images in set 0 and 1
# Doctor 3 evaluate set 1 and images in set 2
@pytest.fixture
def doctor(db_session: db_Session) -> List[Doctors]:
    doc1 = register_doctor(db_session, "doc1", "password123")
    doc2 = register_doctor(db_session, "doc2", "password456")
    doc3 = register_doctor(db_session, "doc3", "password789")
    return [doc1, doc2, doc3]


@pytest.fixture
def sessions(db_session: db_Session, doctor: List[Doctors]) -> List[Session]:
    sess1 = create_session(db_session, doctor[0].uuid)
    sess2 = create_session(db_session, doctor[1].uuid)
    sess3 = create_session(db_session, doctor[2].uuid)
    return [sess1, sess2, sess3]


@pytest.fixture
def image_sets(db_session: db_Session, dataset_uuid) -> List[ImageSet]:
    patient = add_patient(
        db_session,
        "patient_for_sets",
        category="oncology",
        age=50,
        data_set_uuid=dataset_uuid,
    )
    set1 = add_image_set(
        db_session,
        "set1",
        3,
        folder_path="path/to/set1",
        dataset_uuid=dataset_uuid,
        patient_uuid=patient.patient_uuid,
    )
    set2 = add_image_set(
        db_session,
        "set2",
        2,
        folder_path="path/to/set2",
        dataset_uuid=dataset_uuid,
        patient_uuid=patient.patient_uuid,
    )
    set3 = add_image_set(
        db_session,
        "set3",
        4,
        folder_path="path/to/set3",
        dataset_uuid=dataset_uuid,
        patient_uuid=patient.patient_uuid,
    )
    print(
        "Created image sets:",
        set1.image_set_name,
        set2.image_set_name,
        set3.image_set_name,
    )
    return [set1, set2, set3]


# Warning: because images are not params of the test functions,
# this fixture will run for every test function in this file.
# This is intentional to ensure the database is populated correctly.
@pytest.fixture(autouse=True)
def images(db_session: db_Session, image_sets: List[ImageSet]) -> List[List[Image]]:
    all_imgs = []
    print("Adding images to sets...")
    for image_set in image_sets:
        imgs = []
        for i in range(image_set.num_images):
            print(f"Adding image {i} to set {image_set.image_set_name}")
            img = add_image(
                db_session,
                image_set_uuid=image_set.uuid,
                image_name=f"image_{i}_{image_set.uuid}.dcm",
                slice_index=i,
            )
            print("Added image:", img.image_name, img.uuid)
            imgs.append(img)
        all_imgs.append(imgs)
    return all_imgs


@pytest.fixture(autouse=True)
def set_evaluations(
    db_session: db_Session,
    doctor: List[Doctors],
    sessions: List[Session],
    image_sets: List[ImageSet],
):
    print("Adding image set evaluations...")
    # Doctor 1 evaluate set 0 and 1
    eval1 = add_evaluate_image_set(
        db_session,
        doctor_uuid=doctor[0].uuid,
        image_set_uuid=image_sets[0].uuid,
        session_uuid=sessions[0].session_uuid,
        image_set_usability=ImageSetUsability.HemorrhagicPresent,
        ischemic_low_quality=False,
    )
    eval2 = add_evaluate_image_set(
        db_session,
        doctor_uuid=doctor[0].uuid,
        image_set_uuid=image_sets[1].uuid,
        session_uuid=sessions[0].session_uuid,
        image_set_usability=ImageSetUsability.Indeterminate,
        ischemic_low_quality=False,
    )
    # Doctor 3 evaluate set 2
    eval3 = add_evaluate_image_set(
        db_session,
        doctor_uuid=doctor[2].uuid,
        image_set_uuid=image_sets[1].uuid,
        session_uuid=sessions[2].session_uuid,
        image_set_usability=ImageSetUsability.HemorrhagicPresent,
        ischemic_low_quality=False,
    )
    return [eval1, eval2, eval3]


@pytest.fixture(autouse=True)
def image_evaluations(
    db_session: db_Session,
    doctor: List[Doctors],
    sessions: List[Session],
    images: List[List[Image]],
):
    eval1 = []
    eval2 = []
    eval3 = []
    for img in images[0]:  # Doctor 2 evaluate images in set 0 and 1
        eval_ = add_evaluate_image(
            db_session,
            doctor_uuid=doctor[1].uuid,
            image_uuid=img.uuid,
            session_uuid=sessions[1].session_uuid,
            region=Region.None_,
            basal_score_cortex_left=None,
            basal_score_cortex_right=None,
            basal_score_central_left=None,
            basal_score_central_right=None,
            corona_score_left=None,
            corona_score_right=None,
            notes=None,
        )
        eval1.append(eval_)
    for img in images[1]:
        eval_ = add_evaluate_image(
            db_session,
            doctor_uuid=doctor[1].uuid,
            image_uuid=img.uuid,
            session_uuid=sessions[1].session_uuid,
            region=Region.BasalCentral,
            basal_score_cortex_left=1,
            basal_score_cortex_right=3,
            basal_score_central_left=2,
            basal_score_central_right=2,
            corona_score_left=None,
            corona_score_right=None,
            notes=None,
        )
        eval2.append(eval_)
    for img in images[2]:  # Doctor 3 evaluate images in set 2
        eval_ = add_evaluate_image(
            db_session,
            doctor_uuid=doctor[2].uuid,
            image_uuid=img.uuid,
            session_uuid=sessions[2].session_uuid,
            region=Region.CoronaRadiata,
            basal_score_cortex_left=None,
            basal_score_cortex_right=None,
            basal_score_central_left=None,
            basal_score_central_right=None,
            corona_score_left=2,
            corona_score_right=3,
            notes=None,
        )
        eval3.append(eval_)
    return [eval1, eval2, eval3]


def test_get_doctor_image_sets(
    db_session: db_Session,
    doctor: List[Doctors],
    image_sets: List[ImageSet],
):

    # Doctor 1 has evaluated one set

    sets_doc1 = get_doctor_image_sets(db_session, doctor[0].uuid)
    assert len(sets_doc1) == 2
    assert image_sets[0].uuid in sets_doc1
    assert image_sets[1].uuid in sets_doc1


def test_get_doctor_images(
    db_session: db_Session,
    doctor: List[Doctors],
    image_sets: List[ImageSet],
):
    # Doctor 2 has evaluated images in two sets
    sets_doc2 = get_doctor_image_sets(db_session, doctor[1].uuid)
    assert len(sets_doc2) == 2
    assert image_sets[0].uuid in sets_doc2
    assert image_sets[1].uuid in sets_doc2


def test_get_doctor_mixed(
    db_session: db_Session,
    doctor: List[Doctors],
    image_sets: List[ImageSet],
):
    sets_doc3 = get_doctor_image_sets(db_session, doctor[2].uuid)
    assert len(sets_doc3) == 2
    assert image_sets[1].uuid in sets_doc3
    assert image_sets[2].uuid in sets_doc3
