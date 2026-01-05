# pylint: disable=missing-function-docstring,missing-module-docstring, unused-argument
# tests/image_set_evaluation_input_test.py
import uuid as uuid_lib
import pytest

from sqlalchemy.orm import Session as db_Session
from medfabric.api.credentials import register_doctor
from medfabric.api.image_set_evaluation_input import (
    add_evaluate_image_set,
    check_set_evaluation_exists,
)
from medfabric.db.orm_model import Doctors, ImageSet, Session, ImageSetUsability
from medfabric.api.patients import add_patient
from medfabric.api.image_set_input import add_image_set
from medfabric.api.sessions import create_session
from medfabric.api.errors import (
    UserNotFoundError,
    SessionNotFoundError,
    SessionInactiveError,
    SessionMismatchError,
    ImageSetNotFoundError,
    InvalidEvaluationError,
    EvaluationAlreadyExistsError,
)


@pytest.fixture
def doctor(db_session: db_Session) -> Doctors:
    """Create and return a test doctor."""
    return register_doctor(db_session, "doc1", "password123")


@pytest.fixture
def image_set(db_session: db_Session, dataset_uuid) -> ImageSet:
    """Create and return a test image set."""
    patient = add_patient(
        db_session,
        "patient_for_evaluation",
        category="oncology",
        age=50,
        data_set_uuid=dataset_uuid,
    )
    return add_image_set(
        db_session,
        "set1",
        5,
        folder_path="path/to/set1",
        patient_uuid=patient.patient_uuid,
        dataset_uuid=dataset_uuid,
    )


@pytest.fixture
def session(db_session: db_Session, doctor: Doctors) -> Session:
    """Create and return a test session for the doctor."""
    return create_session(db_session, doctor.uuid)


@pytest.mark.parametrize(
    ("ischemic_low_quality", "image_set_usability"),
    [
        (True, ImageSetUsability.IschemicAssessable),
        (False, ImageSetUsability.HemorrhagicPresent),
        (False, ImageSetUsability.Indeterminate),
        (False, ImageSetUsability.TrueIrrelevant),
    ],
)
def test_add_evaluate_image_set_success(
    db_session: db_Session,
    doctor: Doctors,
    image_set: ImageSet,
    session: Session,
    ischemic_low_quality: bool,
    image_set_usability: ImageSetUsability,
):
    evaluation = add_evaluate_image_set(
        db_session,
        doctor.uuid,
        image_set.uuid,
        session.session_uuid,
        image_set_usability=image_set_usability,
        ischemic_low_quality=ischemic_low_quality,
    )
    assert evaluation.doctor_uuid == doctor.uuid
    assert evaluation.image_set_uuid == image_set.uuid
    assert evaluation.session_uuid == session.session_uuid
    assert evaluation.image_set_usability == image_set_usability
    assert evaluation.ischemic_low_quality == ischemic_low_quality


@pytest.mark.parametrize(
    ("ischemic_low_quality", "image_set_usability"),
    [
        (False, ImageSetUsability.IschemicAssessable),
        (True, ImageSetUsability.HemorrhagicPresent),
        (True, ImageSetUsability.Indeterminate),
        (True, ImageSetUsability.TrueIrrelevant),
    ],
)
def test_add_evaluate_invalid_evaluation(
    db_session: db_Session,
    doctor: Doctors,
    image_set: ImageSet,
    session: Session,
    ischemic_low_quality: bool,
    image_set_usability: ImageSetUsability,
):
    with pytest.raises(InvalidEvaluationError):
        add_evaluate_image_set(
            db_session,
            doctor.uuid,
            image_set.uuid,
            session.session_uuid,
            image_set_usability=image_set_usability,
            ischemic_low_quality=ischemic_low_quality,
        )


def test_add_evaluate_image_set_doctor_not_found(
    db_session: db_Session, image_set: ImageSet, session: Session
):
    fake_doctor_id = uuid_lib.uuid4()
    with pytest.raises(UserNotFoundError):
        add_evaluate_image_set(
            db_session,
            fake_doctor_id,
            image_set.uuid,
            session.session_uuid,
            image_set_usability=ImageSetUsability.HemorrhagicPresent,
            ischemic_low_quality=False,
        )


def test_add_evaluate_image_set_session_not_found(
    db_session: db_Session, doctor: Doctors, image_set: ImageSet
):
    fake_session_uuid = uuid_lib.uuid4()
    with pytest.raises(SessionNotFoundError):
        add_evaluate_image_set(
            db_session,
            doctor.uuid,
            image_set.uuid,
            fake_session_uuid,
            image_set_usability=ImageSetUsability.HemorrhagicPresent,
            ischemic_low_quality=False,
        )


def test_add_evaluate_image_set_session_inactive(
    db_session: db_Session, doctor: Doctors, image_set: ImageSet
):
    sess = create_session(db_session, doctor.uuid)
    # Manually set session to inactive
    sess.is_active = False
    db_session.commit()
    with pytest.raises(SessionInactiveError):
        add_evaluate_image_set(
            db_session,
            doctor.uuid,
            image_set.uuid,
            sess.session_uuid,
            image_set_usability=ImageSetUsability.HemorrhagicPresent,
            ischemic_low_quality=False,
        )


def test_add_evaluate_image_set_session_mismatch(
    db_session: db_Session, doctor: Doctors, image_set: ImageSet
):
    other_doctor = register_doctor(db_session, "doc2", "password456")
    sess = create_session(db_session, other_doctor.uuid)
    with pytest.raises(SessionMismatchError):
        add_evaluate_image_set(
            db_session,
            doctor.uuid,
            image_set.uuid,
            sess.session_uuid,
            image_set_usability=ImageSetUsability.HemorrhagicPresent,
            ischemic_low_quality=False,
        )


def test_add_evaluate_image_set_image_set_not_found(
    db_session: db_Session, doctor: Doctors, session: Session
):
    with pytest.raises(ImageSetNotFoundError):
        add_evaluate_image_set(
            db_session,
            doctor.uuid,
            uuid_lib.uuid4(),
            session.session_uuid,
            image_set_usability=ImageSetUsability.HemorrhagicPresent,
            ischemic_low_quality=False,
        )


def test_add_evaluate_image_set_invalid_evaluation(
    db_session: db_Session, doctor: Doctors, image_set: ImageSet, session: Session
):
    with pytest.raises(InvalidEvaluationError):
        add_evaluate_image_set(
            db_session,
            doctor.uuid,
            image_set.uuid,
            session.session_uuid,
            image_set_usability=ImageSetUsability.IschemicAssessable,
            ischemic_low_quality=False,
        )


def test_add_evaluate_image_set_duplicate_evaluation(
    db_session: db_Session, doctor: Doctors, image_set: ImageSet, session: Session
):
    add_evaluate_image_set(
        db_session,
        doctor.uuid,
        image_set.uuid,
        session.session_uuid,
        image_set_usability=ImageSetUsability.HemorrhagicPresent,
        ischemic_low_quality=False,
    )
    with pytest.raises(EvaluationAlreadyExistsError):
        add_evaluate_image_set(
            db_session,
            doctor.uuid,
            image_set.uuid,
            session.session_uuid,
            image_set_usability=ImageSetUsability.Indeterminate,
            ischemic_low_quality=False,
        )


def test_check_evaluation_exists(
    db_session: db_Session, doctor: Doctors, image_set: ImageSet, session: Session
):
    assert not check_set_evaluation_exists(
        db_session,
        doctor.uuid,
        image_set.uuid,
        session.session_uuid,
    )
    add_evaluate_image_set(
        db_session,
        doctor.uuid,
        image_set.uuid,
        session.session_uuid,
        image_set_usability=ImageSetUsability.HemorrhagicPresent,
        ischemic_low_quality=False,
    )
    assert check_set_evaluation_exists(
        db_session,
        doctor.uuid,
        image_set.uuid,
        session.session_uuid,
    )


def test_add_evaluate_image_set_duplicate_does_not_break_existing(
    db_session: db_Session, doctor: Doctors, image_set: ImageSet, session: Session
):
    add_evaluate_image_set(
        db_session,
        doctor.uuid,
        image_set.uuid,
        session.session_uuid,
        image_set_usability=ImageSetUsability.HemorrhagicPresent,
        ischemic_low_quality=False,
    )
    with pytest.raises(EvaluationAlreadyExistsError):
        add_evaluate_image_set(
            db_session,
            doctor.uuid,
            image_set.uuid,
            session.session_uuid,
            image_set_usability=ImageSetUsability.Indeterminate,
            ischemic_low_quality=False,
        )
    # Make sure the first evaluation still exists in DB
    assert check_set_evaluation_exists(
        db_session, doctor.uuid, image_set.uuid, session.session_uuid
    )
