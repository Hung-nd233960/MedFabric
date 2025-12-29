# pylint: disable=too-many-arguments,too-many-locals, missing-module-docstring
# medfabric/api/image_evaluation_input.py
import uuid as uuid_lib
from typing import Optional
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from medfabric.db.orm_model import ImageEvaluation, Region
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
from medfabric.api.config import SCORE_LIMITS


def add_evaluate_image(
    session: Session,
    doctor_uuid: uuid_lib.UUID,
    image_uuid: uuid_lib.UUID,
    session_uuid: uuid_lib.UUID,
    region: Region = Region.None_,
    basal_score_central_left: Optional[int] = None,
    basal_score_central_right: Optional[int] = None,
    basal_score_cortex_left: Optional[int] = None,
    basal_score_cortex_right: Optional[int] = None,
    corona_score_left: Optional[int] = None,
    corona_score_right: Optional[int] = None,
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
            basal_score_central_left=basal_score_central_left,
            basal_score_central_right=basal_score_central_right,
            basal_score_cortex_left=basal_score_cortex_left,
            basal_score_cortex_right=basal_score_cortex_right,
            corona_score_left=corona_score_left,
            corona_score_right=corona_score_right,
            notes=notes,
        )
        doctor_uuid_ = image_eval_validate.doctor_uuid
        image_uuid_ = image_eval_validate.image_uuid
        session_uuid_ = image_eval_validate.session_uuid
        region_ = image_eval_validate.region
        basal_score_central_left_ = image_eval_validate.basal_score_central_left
        basal_score_central_right_ = image_eval_validate.basal_score_central_right
        basal_score_cortex_left_ = image_eval_validate.basal_score_cortex_left
        basal_score_cortex_right_ = image_eval_validate.basal_score_cortex_right
        corona_score_left_ = image_eval_validate.corona_score_left
        corona_score_right_ = image_eval_validate.corona_score_right
        notes_ = image_eval_validate.notes

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
        basal_score_central_left_,
        basal_score_central_right_,
        basal_score_cortex_left_,
        basal_score_cortex_right_,
        corona_score_left_,
        corona_score_right_,
    )

    # Check score ranges
    validate_evaluation_scores(
        basal_score_central_left=basal_score_central_left_,
        basal_score_central_right=basal_score_central_right_,
        basal_score_cortex_left=basal_score_cortex_left_,
        basal_score_cortex_right=basal_score_cortex_right_,
        corona_score_left=corona_score_left_,
        corona_score_right=corona_score_right_,
    )

    # --- Create evaluation ---
    evaluation = ImageEvaluation(
        doctor_uuid=doctor_uuid_,
        image_uuid=image_uuid_,
        session_uuid=session_uuid_,
        region=region_,
        basal_score_central_left=basal_score_central_left_,
        basal_score_central_right=basal_score_central_right_,
        basal_score_cortex_left=basal_score_cortex_left_,
        basal_score_cortex_right=basal_score_cortex_right_,
        corona_score_left=corona_score_left_,
        corona_score_right=corona_score_right_,
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
    Validates that the provided scores are within acceptable ranges.

    Returns:
        True if all scores valid.
        False if invalid (in LENIENT mode).
    Raises:
        InvalidEvaluationError in STRICT mode when validation fails.
    """
    for name, max_val in SCORE_LIMITS.items():
        value = kwargs.get(name)
        if value is not None and not 0 <= value <= max_val:
            if mode is VerificationMode.STRICT:
                raise InvalidEvaluationError(
                    f"{name} must be between 0 and {max_val}, got {value}."
                )
            return False
    return True


def region_score_requirements(
    region: Region,
    basal_score_central_left: Optional[int],
    basal_score_central_right: Optional[int],
    basal_score_cortex_left: Optional[int],
    basal_score_cortex_right: Optional[int],
    corona_score_left: Optional[int],
    corona_score_right: Optional[int],
    mode=VerificationMode.STRICT,
) -> bool:
    """Validates that the provided scores align with the specified region.

    Returns:
        True if valid.
        False if invalid (in LENIENT mode).
    Raises:
        InvalidEvaluationError in STRICT mode when validation fails.
    """
    scores = {
        "basal_score_central_left": basal_score_central_left,
        "basal_score_central_right": basal_score_central_right,
        "basal_score_cortex_left": basal_score_cortex_left,
        "basal_score_cortex_right": basal_score_cortex_right,
        "corona_score_left": corona_score_left,
        "corona_score_right": corona_score_right,
    }
    region_score_requirements = {
        Region.None_: {
            "required": [],
            "forbidden": list(scores.keys()),
        },
        Region.BasalCentral: {
            "required": [
                "basal_score_central_left",
                "basal_score_central_right",
                "basal_score_cortex_left",
                "basal_score_cortex_right",
            ],
            "forbidden": ["corona_score_left", "corona_score_right"],
        },
        Region.BasalCortex: {
            "required": ["basal_score_cortex_left", "basal_score_cortex_right"],
            "forbidden": ["corona_score_left", "corona_score_right"],
        },
        Region.CoronaRadiata: {
            "required": ["corona_score_left", "corona_score_right"],
            "forbidden": [
                "basal_score_central_left",
                "basal_score_central_right",
                "basal_score_cortex_left",
                "basal_score_cortex_right",
            ],
        },
    }
    reqs = region_score_requirements[region]

    # Check required fields
    for field in reqs["required"]:
        if scores[field] is None:
            if mode is VerificationMode.STRICT:
                raise InvalidEvaluationError(
                    f"{field} must be provided for region '{region.name}'."
                )
            return False

    # Check forbidden fields
    for field in reqs["forbidden"]:
        if scores[field] is not None:
            if mode is VerificationMode.STRICT:
                raise InvalidEvaluationError(
                    f"{field} must not be provided for region '{region.name}'."
                )
            return False

    return True
