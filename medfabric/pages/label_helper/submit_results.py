from typing import Optional, List
from dataclasses import dataclass, field
import uuid as uuid_lib
from sqlalchemy.orm import Session as db_Session
from medfabric.db.models import (
    ImageEvaluation,
    ImageSetEvaluation,
)
from medfabric.pages.label_helper.session_initialization import (
    ImageEvaluationSession,
    ImageSetEvaluationSession,
)
from medfabric.api.image_evaluation_input import (
    add_evaluate_image,
)
from medfabric.api.image_set_evaluation_input import add_evaluate_image_set


@dataclass
class SubmissionResult:
    set_evaluation: Optional[ImageSetEvaluation] = None
    image_evaluations: List[ImageEvaluation] = field(default_factory=list)


def submit_result_image(
    db_session: db_Session,
    doctor_uuid: uuid_lib.UUID,
    session_uuid: uuid_lib.UUID,
    result: ImageEvaluationSession,
) -> Optional[ImageEvaluation]:
    """Submit the evaluation result for a specific image in an evaluation session.
    Args:
        db_session: SQLAlchemy session object.
        doctor_uuid: UUID of the doctor submitting the evaluation.
        session_uuid: UUID of the evaluation session.
        result: ImageEvaluationSession object containing the evaluation details.
    Returns:
        ImageEvaluation object if submission is successful, None otherwise.
    """
    evaluation = add_evaluate_image(
        session=db_session,
        doctor_id=doctor_uuid,
        image_uuid=result.image_uuid,
        session_id=session_uuid,
        region=result.region,
        basal_score_central_left=result.basal_score_central_left,
        basal_score_central_right=result.basal_score_central_right,
        basal_score_cortex_left=result.basal_score_cortex_left,
        basal_score_cortex_right=result.basal_score_cortex_right,
        corona_score_left=result.corona_score_left,
        corona_score_right=result.corona_score_right,
        notes=result.notes,
    )
    return evaluation if evaluation else None


def submit_result_image_set_evaluation(
    db_session: db_Session,
    doctor_uuid: uuid_lib.UUID,
    session_uuid: uuid_lib.UUID,
    result: ImageSetEvaluationSession,
) -> Optional[ImageSetEvaluation]:
    """Submit the evaluation result for an entire image set evaluation session.
    Args:
        db_session: SQLAlchemy session object.
        doctor_uuid: UUID of the doctor submitting the evaluation.
        session_uuid: UUID of the evaluation session.
        result: ImageSetEvaluationSession object containing the evaluation details.
    Returns:
        ImageSetEvaluation object if submission is successful, None otherwise.
    """
    evaluation = add_evaluate_image_set(
        session=db_session,
        doctor_id=doctor_uuid,
        image_set_uuid=result.uuid,
        session_id=session_uuid,
        is_low_quality=result.low_quality,
        is_irrelevant=result.irrelevant_data,
    )
    return evaluation if evaluation else None


def submit_image_set_results(
    db_session: db_Session,
    doctor_uuid: uuid_lib.UUID,
    session_uuid: uuid_lib.UUID,
    result: ImageSetEvaluationSession,
) -> SubmissionResult:
    """Submit the evaluation results for an image set evaluation session.
    Depending on whether the entire set is marked as low quality or irrelevant,
    it either submits a single ImageSetEvaluation or multiple ImageEvaluations.
    Args:
        db_session: SQLAlchemy session object.
        doctor_uuid: UUID of the doctor submitting the evaluations.
        session_uuid: UUID of the evaluation session.
        result: ImageSetEvaluationSession object containing the evaluation details.
    Returns:
        SubmissionResult object containing either the ImageSetEvaluation or a list of ImageEvaluations.
    """
    if result.low_quality or result.irrelevant_data:
        set_eval = submit_result_image_set_evaluation(
            db_session, doctor_uuid, session_uuid, result
        )
        return SubmissionResult(set_evaluation=set_eval)
    else:
        image_evals = [
            submit_result_image(db_session, doctor_uuid, session_uuid, img_sess)
            for img_sess in result.images_sessions
        ]
    return SubmissionResult(image_evaluations=[e for e in image_evals if e])
