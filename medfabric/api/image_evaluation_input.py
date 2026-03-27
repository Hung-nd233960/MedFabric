# pylint: disable=too-many-arguments,too-many-locals, missing-module-docstring
# medfabric/api/image_evaluation_input.py
import uuid as uuid_lib
from typing import Optional
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from medfabric.db.orm_model import ImageEvaluation, Region, RegionScore
from medfabric.db.pydantic_model import ImageEvaluationCreate
from medfabric.api.errors import (
    UserNotFoundError,
    ImageNotFoundError,
    DatabaseError,
    SessionNotFoundError,
    SessionMismatchError,
    SessionInactiveError,
    InvalidEvaluationError,
    EvaluationAlreadyExistsError,
)
from medfabric.api.sessions import doctor_exists, get_session
from medfabric.api.image_input import (
    check_image_exists_by_uuid,
    get_set_id_from_image_id,
)
from medfabric.api.image_set_evaluation_input import (
    check_set_evaluation_exists,
)


ASPECTS_SCORE_FIELDS = [
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


def add_evaluate_image(
    session: Session,
    doctor_uuid: uuid_lib.UUID,
    image_uuid: uuid_lib.UUID,
    session_uuid: uuid_lib.UUID,
    region: Region,
    c_left_score: RegionScore,
    c_right_score: RegionScore,
    ic_left_score: RegionScore,
    ic_right_score: RegionScore,
    l_left_score: RegionScore,
    l_right_score: RegionScore,
    i_left_score: RegionScore,
    i_right_score: RegionScore,
    m1_left_score: RegionScore,
    m1_right_score: RegionScore,
    m2_left_score: RegionScore,
    m2_right_score: RegionScore,
    m3_left_score: RegionScore,
    m3_right_score: RegionScore,
    m4_left_score: RegionScore,
    m4_right_score: RegionScore,
    m5_left_score: RegionScore,
    m5_right_score: RegionScore,
    m6_left_score: RegionScore,
    m6_right_score: RegionScore,
    notes: Optional[str] = None,
) -> ImageEvaluation:
    """
    Evaluates a single image by a doctor.
    """
    try:
        image_eval_validate = ImageEvaluationCreate(
            doctor_uuid=doctor_uuid,
            image_uuid=image_uuid,
            session_uuid=session_uuid,
            region=region,
            c_left_score=c_left_score,
            c_right_score=c_right_score,
            ic_left_score=ic_left_score,
            ic_right_score=ic_right_score,
            l_left_score=l_left_score,
            l_right_score=l_right_score,
            i_left_score=i_left_score,
            i_right_score=i_right_score,
            m1_left_score=m1_left_score,
            m1_right_score=m1_right_score,
            m2_left_score=m2_left_score,
            m2_right_score=m2_right_score,
            m3_left_score=m3_left_score,
            m3_right_score=m3_right_score,
            m4_left_score=m4_left_score,
            m4_right_score=m4_right_score,
            m5_left_score=m5_left_score,
            m5_right_score=m5_right_score,
            m6_left_score=m6_left_score,
            m6_right_score=m6_right_score,
            notes=notes,
        )
        doctor_uuid_ = image_eval_validate.doctor_uuid
        image_uuid_ = image_eval_validate.image_uuid
        session_uuid_ = image_eval_validate.session_uuid
        region_ = image_eval_validate.region
        notes_ = image_eval_validate.notes
        scores_ = {
            field: getattr(image_eval_validate, field) for field in ASPECTS_SCORE_FIELDS
        }

    except ValidationError as e:
        raise InvalidEvaluationError(f"Invalid evaluation data: {e}") from e

    # --- Entity existence checks ---
    if not doctor_exists(session, doctor_uuid_):
        raise UserNotFoundError("Doctor with the given UUID does not exist.")

    if not check_image_exists_by_uuid(session, image_uuid_):
        raise ImageNotFoundError("Image with the given UUID does not exist.")

    session_result = get_session(session, session_uuid_)
    if not session_result:
        raise SessionNotFoundError("Session with the given ID does not exist.")

    if session_result.doctor_uuid != doctor_uuid_:
        raise SessionMismatchError("The session does not belong to the given doctor.")

    if not session_result.is_active:
        raise SessionInactiveError("The session is not active.")
    image_set_uuid_ = get_set_id_from_image_id(session, image_uuid_)
    if not image_set_uuid_:
        raise ImageNotFoundError("Image with the given UUID does not exist.")
    # --- Duplicate evaluation checks ---
    if check_set_evaluation_exists(
        session, doctor_uuid_, image_set_uuid_, session_uuid_
    ):
        raise EvaluationAlreadyExistsError(
            "An evaluation for this image set by the doctor in the given session already exists."
        )

    if check_image_evaluation_exists(session, doctor_uuid_, image_uuid_, session_uuid_):
        raise EvaluationAlreadyExistsError(
            "An evaluation for this image by the doctor in the given session already exists."
        )

    # --- Validate region and score consistency ---
    region_score_requirements(
        region_,
        **scores_,
    )

    validate_evaluation_scores(**scores_)

    # --- Create evaluation ---
    evaluation = ImageEvaluation(
        doctor_uuid=doctor_uuid_,
        image_uuid=image_uuid_,
        session_uuid=session_uuid_,
        region=region_,
        **scores_,
        notes=notes_,
    )

    try:
        session.add(evaluation)
        session.commit()
        return evaluation
    except SQLAlchemyError as e:
        session.rollback()
        raise DatabaseError(f"Failed to add image evaluation: {e}") from e


def check_image_evaluation_exists(
    session: Session,
    doctor_uuid: uuid_lib.UUID,
    image_uuid: uuid_lib.UUID,
    session_uuid: uuid_lib.UUID,
) -> bool:
    """
    Checks if an image evaluation exists for the given doctor, image, and session.

    Args:
        session (Session): SQLAlchemy session.
        doctor_uuid (uuid.UUID): ID of the doctor.
        image_uuid (uuid.UUID): ID of the image.
        session_uuid (uuid.UUID): ID of the session.

    Returns:
        bool: True if the evaluation exists, False otherwise.
    """
    return (
        session.query(ImageEvaluation)
        .filter_by(
            doctor_uuid=doctor_uuid, image_uuid=image_uuid, session_uuid=session_uuid
        )
        .first()
        is not None
    )


class VerificationMode(Enum):
    STRICT = "strict"
    LENIENT = "lenient"


def validate_evaluation_scores(mode=VerificationMode.STRICT, **kwargs) -> bool:
    """
    Validates that provided scores are RegionScore values.

    Returns:
        True if all scores valid.
        False if invalid (in LENIENT mode).
    Raises:
        InvalidEvaluationError in STRICT mode when validation fails.
    """
    for name in ASPECTS_SCORE_FIELDS:
        value = kwargs.get(name)
        if not isinstance(value, RegionScore):
            if mode is VerificationMode.STRICT:
                raise InvalidEvaluationError(
                    f"{name} must be a RegionScore value, got {value}."
                )
            return False
    return True


def region_score_requirements(
    region: Region,
    mode=VerificationMode.STRICT,
    **kwargs,
) -> bool:
    """Validates that the provided scores align with the specified region.

    Returns:
        True if valid.
        False if invalid (in LENIENT mode).
    Raises:
        InvalidEvaluationError in STRICT mode when validation fails.
    """
    scores = {field: kwargs.get(field) for field in ASPECTS_SCORE_FIELDS}

    def _fail(message: str) -> bool:
        if mode is VerificationMode.STRICT:
            raise InvalidEvaluationError(message)
        return False

    if region == Region.None_:
        for field_name, value in scores.items():
            if value != RegionScore.Not_Applicable:
                return _fail(
                    f"{field_name} must be RegionScore.Not_Applicable for region '{region.name}'."
                )
        return True

    if region == Region.BasalGanglia:
        required_fields = ASPECTS_BASAL_FIELDS
        not_applicable_fields = ASPECTS_CORONA_FIELDS
    elif region == Region.CoronaRadiata:
        required_fields = ASPECTS_CORONA_FIELDS
        not_applicable_fields = ASPECTS_BASAL_FIELDS
    else:
        return _fail(f"Unsupported region '{region}'.")

    for field_name in required_fields:
        value = scores[field_name]
        if value is None:
            return _fail(
                f"{field_name} must be provided for region '{region.name}'."
            )
        if value == RegionScore.Not_Applicable:
            return _fail(
                f"{field_name} cannot be RegionScore.Not_Applicable for region '{region.name}'."
            )

    for field_name in not_applicable_fields:
        value = scores[field_name]
        if value != RegionScore.Not_Applicable:
            return _fail(
                f"{field_name} must be RegionScore.Not_Applicable for region '{region.name}'."
            )

    return True
