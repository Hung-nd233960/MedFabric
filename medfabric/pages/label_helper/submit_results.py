from typing import Optional, List
from dataclasses import dataclass, field
import uuid as uuid_lib
from sqlalchemy.orm import Session as db_Session
from medfabric.db.orm_model import (
    ImageEvaluation,
    ImageSetEvaluation,
    ImageSetUsability,
    Region,
    RegionScore,
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


ALL_SCORE_FIELDS = [
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

BASAL_SCORE_FIELDS = ALL_SCORE_FIELDS[:14]
CORONA_SCORE_FIELDS = ALL_SCORE_FIELDS[14:]


def _normalize_score_value(value) -> RegionScore:
    if isinstance(value, RegionScore):
        return value
    if value is None:
        return RegionScore.Not_Applicable
    if value in ("Not Visible",):
        return RegionScore.Not_In_This_Slice
    if value in ("0", "0 Score", 0):
        return RegionScore.Affected
    if value in ("1", "1 Score", 1):
        return RegionScore.Not_Affected
    raise ValueError(f"Unsupported score value: {value}")


def _normalize_scores_for_region(result: ImageEvaluationSession) -> dict:
    scores = {
        field: _normalize_score_value(getattr(result, field, None))
        for field in ALL_SCORE_FIELDS
    }

    # Region-based Not_Applicable policy.
    if result.region == Region.None_:
        for field in ALL_SCORE_FIELDS:
            scores[field] = RegionScore.Not_Applicable
    elif result.region == Region.BasalGanglia:
        for field in CORONA_SCORE_FIELDS:
            scores[field] = RegionScore.Not_Applicable
    elif result.region == Region.CoronaRadiata:
        for field in BASAL_SCORE_FIELDS:
            scores[field] = RegionScore.Not_Applicable

    return scores


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
    scores = _normalize_scores_for_region(result)

    evaluation = add_evaluate_image(
        session=db_session,
        doctor_uuid=doctor_uuid,
        image_uuid=result.image_uuid,
        session_uuid=session_uuid,
        region=result.region,
        **scores,
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
        doctor_uuid=doctor_uuid,
        image_set_uuid=result.uuid,
        session_uuid=session_uuid,
        image_set_usability=result.image_set_usability,
        ischemic_low_quality=result.low_quality,
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
        SubmissionResult object containing either the
        ImageSetEvaluation or a list of ImageEvaluations.
    """
    if (
        result.low_quality
        and result.image_set_usability == ImageSetUsability.IschemicAssessable
    ) or result.image_set_usability != ImageSetUsability.IschemicAssessable:
        set_eval = submit_result_image_set_evaluation(
            db_session, doctor_uuid, session_uuid, result
        )
        return SubmissionResult(set_evaluation=set_eval)
    image_evals = [
        submit_result_image(db_session, doctor_uuid, session_uuid, img_sess)
        for img_sess in result.images_sessions
    ]
    return SubmissionResult(image_evaluations=[e for e in image_evals if e])
