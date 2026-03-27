# pylint: disable=missing-function-docstring, missing-module-docstring, redefined-outer-name
# tests/image_evaluation_input_test.py
import uuid as uuid_lib
from typing import cast
import pytest
from sqlalchemy.orm import Session as db_Session
from medfabric.db.orm_model import (
    Region,
    RegionScore,
    ImageFormat,
    ImageEvaluation,
    Doctors,
    Session,
    Image,
    ImageSet,
)
from medfabric.api.credentials import register_doctor
from medfabric.api.patients import add_patient
from medfabric.api.image_input import add_image
from medfabric.api.image_set_input import add_image_set
from medfabric.api.image_evaluation_input import (
    add_evaluate_image,
    region_score_requirements,
    validate_evaluation_scores,
    check_image_evaluation_exists,
)
from medfabric.api.sessions import create_session
from medfabric.api.errors import (
    UserNotFoundError,
    ImageNotFoundError,
    SessionNotFoundError,
    SessionInactiveError,
    SessionMismatchError,
    InvalidEvaluationError,
    EvaluationAlreadyExistsError,
)


ASPECTS_FIELDS = [
    "c_left_score",
    "c_right_score",
    "ic_left_score",
    "ic_right_score",
    "l_left_score",
    "l_right_score",
    "i_left_score",
    "i_right_score",
    "m1_left_score",
    "m1_right_score",
    "m2_left_score",
    "m2_right_score",
    "m3_left_score",
    "m3_right_score",
    "m4_left_score",
    "m4_right_score",
    "m5_left_score",
    "m5_right_score",
    "m6_left_score",
    "m6_right_score",
]

ASPECTS_BASAL_FIELDS = [
    "c_left_score",
    "c_right_score",
    "ic_left_score",
    "ic_right_score",
    "l_left_score",
    "l_right_score",
    "i_left_score",
    "i_right_score",
    "m1_left_score",
    "m1_right_score",
    "m2_left_score",
    "m2_right_score",
    "m3_left_score",
    "m3_right_score",
]

ASPECTS_CORONA_FIELDS = [
    "m4_left_score",
    "m4_right_score",
    "m5_left_score",
    "m5_right_score",
    "m6_left_score",
    "m6_right_score",
]


def scores_none_region():
    return {name: RegionScore.Not_Applicable for name in ASPECTS_FIELDS}


def scores_basal_region():
    scores = scores_none_region()
    for name in ASPECTS_BASAL_FIELDS:
        scores[name] = RegionScore.Not_Affected
    return scores


def scores_corona_region():
    scores = scores_none_region()
    for name in ASPECTS_CORONA_FIELDS:
        scores[name] = RegionScore.Not_Affected
    return scores


@pytest.mark.parametrize(
    "region,scores",
    [
        (Region.None_, scores_none_region()),
        (Region.BasalGanglia, scores_basal_region()),
        (Region.BasalGanglia, scores_basal_region()),
        (Region.CoronaRadiata, scores_corona_region()),
    ],
)
def test_success_cases_region_enforcement(region, scores):
    # should not raise
    region_score_requirements(region, **scores)


@pytest.mark.parametrize(
    "region,scores",
    [
        (
            Region.None_,
            {
                **scores_none_region(),
                "c_left_score": RegionScore.Not_Affected,
            },
        ),
        (
            Region.BasalGanglia,
            {
                **scores_basal_region(),
                "c_left_score": RegionScore.Not_Applicable,
            },
        ),
        (
            Region.BasalGanglia,
            {
                **scores_basal_region(),
                "m4_left_score": RegionScore.Not_Affected,
            },
        ),
        (
            Region.CoronaRadiata,
            {
                **scores_corona_region(),
                "m4_right_score": None,
            },
        ),
    ],
)
def test_failure_cases_region_enforcement(region, scores):
    with pytest.raises(InvalidEvaluationError):
        region_score_requirements(region, **scores)


@pytest.mark.parametrize(
    "scores",
    [
        scores_none_region(),
        scores_basal_region(),
        scores_corona_region(),
        {
            **scores_basal_region(),
            "c_left_score": RegionScore.Affected,
            "m2_right_score": RegionScore.Not_In_This_Slice,
        },
    ],
)
def test_success_cases_score_validation(scores):
    # should not raise
    validate_evaluation_scores(**scores)


@pytest.mark.parametrize(
    "scores",
    [
        {**scores_basal_region(), "c_left_score": "bad_value"},
        {**scores_corona_region(), "m6_right_score": 1},
    ],
)
def test_failure_cases_score_validation(scores):
    with pytest.raises(InvalidEvaluationError):
        validate_evaluation_scores(**scores)


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
        image_format=ImageFormat.DICOM,
        image_window_level=40,
        image_window_width=80,
        folder_path="path/to/set1",
        dataset_uuid=dataset_uuid,
        patient_uuid=patient.patient_uuid,
    )


@pytest.fixture
def session(db_session: db_Session, doctor: Doctors) -> Session:
    """Create and return a test session for the doctor."""
    return create_session(db_session, doctor.uuid)


@pytest.fixture
def image(db_session: db_Session, image_set: ImageSet) -> Image:
    """Create and return a test image in the given image set."""
    return add_image(
        db_session, image_name="img1", image_set_uuid=image_set.uuid, slice_index=1
    )


def test_add_evaluate_image_success(
    db_session: db_Session, doctor: Doctors, image: Image, session: Session
):
    scores = scores_basal_region()
    scores["c_left_score"] = RegionScore.Affected
    scores["c_right_score"] = RegionScore.Not_Affected
    evaluation = add_evaluate_image(
        db_session,
        doctor.uuid,
        image.uuid,
        session.session_uuid,
        region=Region.BasalGanglia,
        **scores,
        notes="Test evaluation",
    )
    assert evaluation.doctor_uuid == doctor.uuid
    assert evaluation.image_uuid == image.uuid
    assert evaluation.session_uuid == session.session_uuid
    assert evaluation.region == Region.BasalGanglia
    assert evaluation.c_left_score == RegionScore.Affected
    assert evaluation.c_right_score == RegionScore.Not_Affected
    assert evaluation.m4_left_score == RegionScore.Not_Applicable
    assert evaluation.m4_right_score == RegionScore.Not_Applicable
    assert evaluation.notes == "Test evaluation"


def test_add_evaluate_image_doctor_not_found(
    db_session: db_Session, image: Image, session: Session
):
    fake_doctor_uuid = uuid_lib.uuid4()
    with pytest.raises(UserNotFoundError):
        add_evaluate_image(
            db_session,
            fake_doctor_uuid,
            image.uuid,
            session.session_uuid,
            region=Region.BasalGanglia,
            **scores_basal_region(),
            notes="Test evaluation",
        )


def test_add_evaluate_image_image_not_found(
    db_session: db_Session, doctor: Doctors, session: Session
):
    fake_image_name = uuid_lib.uuid4()
    with pytest.raises(ImageNotFoundError):
        add_evaluate_image(
            db_session,
            doctor.uuid,
            fake_image_name,
            session.session_uuid,
            region=Region.BasalGanglia,
            **scores_basal_region(),
            notes="Test evaluation",
        )


def test_add_evaluate_image_session_not_found(
    db_session: db_Session, doctor: Doctors, image: Image
):
    fake_session_uuid = uuid_lib.uuid4()
    with pytest.raises(SessionNotFoundError):
        add_evaluate_image(
            db_session,
            doctor.uuid,
            image.uuid,
            fake_session_uuid,
            region=Region.BasalGanglia,
            **scores_basal_region(),
            notes="Test evaluation",
        )


def test_add_evaluate_image_session_inactive(
    db_session: db_Session, doctor: Doctors, image: Image
):
    sess = create_session(db_session, doctor.uuid)
    # Manually set session to inactive
    sess.is_active = False
    db_session.commit()
    with pytest.raises(SessionInactiveError):
        invalid_scores = scores_none_region()
        invalid_scores["c_left_score"] = RegionScore.Affected
        add_evaluate_image(
            db_session,
            doctor.uuid,
            image.uuid,
            sess.session_uuid,
            region=Region.BasalGanglia,
            **invalid_scores,
            notes="Test evaluation",
        )


def test_add_evaluate_image_session_mismatch(
    db_session: db_Session, doctor: Doctors, image: Image
):
    other_doctor = register_doctor(db_session, "doc2", "password456")
    sess = create_session(db_session, other_doctor.uuid)
    with pytest.raises(SessionMismatchError):
        add_evaluate_image(
            db_session,
            doctor.uuid,
            image.uuid,
            sess.session_uuid,
            region=Region.BasalGanglia,
            **scores_basal_region(),
            notes="Test evaluation",
        )


def test_add_evaluate_image_invalid_region(
    db_session: db_Session, doctor: Doctors, image: Image, session: Session
):
    with pytest.raises(InvalidEvaluationError):
        add_evaluate_image(
            db_session,
            doctor.uuid,
            image.uuid,
            session.session_uuid,
            region=cast(Region, "InvalidRegion"),  # invalid region
            **scores_basal_region(),
            notes="Test evaluation",
        )


def test_add_evaluate_image_invalid_scores(
    db_session: db_Session, doctor: Doctors, image: Image, session: Session
):
    with pytest.raises(InvalidEvaluationError):
        bad_scores = {**scores_basal_region(), "c_left_score": "invalid"}
        add_evaluate_image(
            db_session,
            doctor.uuid,
            image.uuid,
            session.session_uuid,
            region=Region.BasalGanglia,
            **bad_scores,
            notes="Test evaluation",
        )


def test_add_evaluate_image_duplicate_evaluation(
    db_session: db_Session, doctor: Doctors, image: Image, session: Session
):
    add_evaluate_image(
        db_session,
        doctor.uuid,
        image.uuid,
        session.session_uuid,
        region=Region.BasalGanglia,
        **scores_basal_region(),
        notes="First evaluation",
    )
    with pytest.raises(EvaluationAlreadyExistsError):
        add_evaluate_image(
            db_session,
            doctor.uuid,
            image.uuid,
            session.session_uuid,
            region=Region.BasalGanglia,
            **scores_basal_region(),
            notes="Duplicate evaluation",
        )


def test_check_image_evaluation_exists(
    db_session: db_Session, doctor: Doctors, image: Image, session: Session
):
    assert not check_image_evaluation_exists(
        db_session,
        doctor.uuid,
        image.uuid,
        session.session_uuid,
    )
    add_evaluate_image(
        db_session,
        doctor.uuid,
        image.uuid,
        session.session_uuid,
        region=Region.BasalGanglia,
        **scores_basal_region(),
        notes="Test evaluation",
    )
    assert check_image_evaluation_exists(
        db_session,
        doctor.uuid,
        image.uuid,
        session.session_uuid,
    )


def test_add_evaluate_image_duplicate_does_not_break_existing(
    db_session: db_Session, doctor: Doctors, image: Image, session: Session
):
    add_evaluate_image(
        db_session,
        doctor.uuid,
        image.uuid,
        session.session_uuid,
        region=Region.BasalGanglia,
        **scores_basal_region(),
        notes="First evaluation",
    )
    with pytest.raises(EvaluationAlreadyExistsError):
        add_evaluate_image(
            db_session,
            doctor.uuid,
            image.uuid,
            session.session_uuid,
            region=Region.BasalGanglia,
            **scores_basal_region(),
            notes="Duplicate evaluation",
        )
    # Ensure the original evaluation still exists and is unchanged
    evaluations = (
        db_session.query(ImageEvaluation)
        .filter_by(
            doctor_uuid=doctor.uuid,
            image_uuid=image.uuid,
            session_uuid=session.session_uuid,
        )
        .all()
    )
    assert len(evaluations) == 1
    evaluation_ = evaluations[0]
    assert evaluation_.c_left_score == RegionScore.Not_Affected
    assert evaluation_.c_right_score == RegionScore.Not_Affected
    assert evaluation_.notes == "First evaluation"
