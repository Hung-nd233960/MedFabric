"""API functions for evaluating image sets."""

# medfabric/api/image_set_evaluation_input.py
import uuid as uuid_lib
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import ValidationError
from medfabric.db.orm_model import ImageSetEvaluation
from medfabric.db.pydantic_model import ImageSetEvaluationCreate
from medfabric.api.errors import (
    UserNotFoundError,
    SessionNotFoundError,
    SessionInactiveError,
    SessionMismatchError,
    DatabaseError,
    ImageSetNotFoundError,
    InvalidEvaluationError,
    EvaluationAlreadyExistsError,
)
from medfabric.api.sessions import doctor_exists, get_session
from medfabric.api.image_set_input import check_image_set_exists


def check_set_evaluation_exists(
    session: Session,
    doctor_uuid: uuid_lib.UUID,
    image_set_uuid: uuid_lib.UUID,
    session_uuid: uuid_lib.UUID,
) -> bool:
    """
    Check if an evaluation exists for the given doctor, image set, and session.

    Args:
        session (Session): SQLAlchemy DB session
        doctor_uuid (uuid.UUID): ID of the doctor
        image_set_uuid (uuid.UUID): ID of the image set
        session_uuid (uuid.UUID): ID of the session

    Returns:
        True if exists, False otherwise
    """
    return (
        session.query(ImageSetEvaluation)
        .filter_by(
            doctor_uuid=doctor_uuid,
            image_set_uuid=image_set_uuid,
            session_uuid=session_uuid,
        )
        .first()
        is not None
    )


def add_evaluate_image_set(
    session: Session,
    doctor_uuid: uuid_lib.UUID,
    image_set_uuid: uuid_lib.UUID,
    session_uuid: uuid_lib.UUID,
    is_low_quality: bool = False,
    is_irrelevant: bool = False,
) -> ImageSetEvaluation:
    """
    Evaluates an image set by a doctor.

    Args:
        session (Session): SQLAlchemy session.
        doctor_uuid (uuid.UUID): ID of the doctor evaluating the image set.
        image_set_uuid (uuid.UUID): ID of the image set being evaluated.
        session_uuid (uuid.UUID): ID of the session during which the evaluation is made.
        is_low_quality (bool): Indicates if the image set is of low quality.
        is_irrelevant (bool): Indicates if the image set is irrelevant.

    Returns:
        ImageSetEvaluation: The created evaluation record.
    """
    try:
        # Validate input data using Pydantic model
        eval_data = ImageSetEvaluationCreate(
            doctor_uuid=doctor_uuid,
            image_set_uuid=image_set_uuid,
            session_uuid=session_uuid,
            is_low_quality=is_low_quality,
            is_irrelevant=is_irrelevant,
        )
        doctor_uuid_ = eval_data.doctor_uuid
        image_set_uuid_ = eval_data.image_set_uuid
        session_uuid_ = eval_data.session_uuid
        is_low_quality_ = eval_data.is_low_quality
        is_irrelevant_ = eval_data.is_irrelevant
    except ValidationError as ve:
        raise InvalidEvaluationError(f"Invalid evaluation data: {ve}") from ve

    if not doctor_exists(session, doctor_uuid_):
        raise UserNotFoundError("Doctor with the given UUID does not exist.")
    if not check_image_set_exists(session, image_set_uuid_):
        raise ImageSetNotFoundError("Image set with the given ID does not exist.")

    session_result = get_session(session, session_uuid_)
    if not session_result:
        raise SessionNotFoundError("Session with the given UUID does not exist.")
    if session_result.doctor_uuid != doctor_uuid_:
        raise SessionMismatchError("Session does not belong to the specified doctor.")
    if not session_result.is_active:
        raise SessionInactiveError("Session is not active.")
    if not (is_low_quality_ or is_irrelevant_):
        raise InvalidEvaluationError(
            "At least one of is_low_quality or is_irrelevant must be True."
        )
    try:
        evaluation = ImageSetEvaluation(
            doctor_uuid=doctor_uuid_,
            image_set_uuid=image_set_uuid_,
            session_uuid=session_uuid_,
            is_low_quality=is_low_quality_,
            is_irrelevant=is_irrelevant_,
        )
        session.add(evaluation)
        session.commit()
        return evaluation
    except IntegrityError as exc:
        session.rollback()
        raise EvaluationAlreadyExistsError(
            "An evaluation already exists for this doctor, session, and image set."
        ) from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise DatabaseError("Failed to evaluate image set.") from exc
