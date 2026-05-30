"""Evaluation submission service.

Handles the full submission flow:
  1. Write ImageSetEvaluation (always).
  2. If IschemicAssessable + !low_quality: also write per-slice ImageEvaluations
     with Not_Applicable normalization applied.
"""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import (
    AnnotationSession,
    ImageEvaluation,
    ImageSetEvaluation,
    ImageSetUsability,
    Region,
    RegionScore,
)
from app.db.schemas import ImageEvaluationSubmit, SubmitAnnotation
from app.services.errors import (
    AnnotationSessionAlreadySubmittedError,
    AnnotationSessionNotFoundError,
    InvalidEvaluationError,
)

# Ordered field names matching ImageEvaluation columns
_ALL_SCORE_FIELDS = [
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
_BASAL_FIELDS = _ALL_SCORE_FIELDS[:14]  # c, ic, l, i, m1, m2, m3
_CORONA_FIELDS = _ALL_SCORE_FIELDS[14:]  # m4, m5, m6


def _normalize_scores(data: ImageEvaluationSubmit) -> dict:
    """Apply Not_Applicable policy based on region."""
    scores = {f: getattr(data, f) for f in _ALL_SCORE_FIELDS}
    if data.region == Region.None_:
        for f in _ALL_SCORE_FIELDS:
            scores[f] = RegionScore.Not_Applicable
    elif data.region == Region.BasalGanglia:
        for f in _CORONA_FIELDS:
            scores[f] = RegionScore.Not_Applicable
    elif data.region == Region.CoronaRadiata:
        for f in _BASAL_FIELDS:
            scores[f] = RegionScore.Not_Applicable
    return scores


def _validate_full_submission(image_evals: List[ImageEvaluationSubmit]) -> None:
    """Validate ASPECTS coverage: ≥1 basal + ≥1 corona slice classified."""
    has_basal = any(e.region == Region.BasalGanglia for e in image_evals)
    has_corona = any(e.region == Region.CoronaRadiata for e in image_evals)
    if not has_basal:
        raise InvalidEvaluationError(
            "Full ASPECTS scoring requires at least one BasalGanglia slice."
        )
    if not has_corona:
        raise InvalidEvaluationError(
            "Full ASPECTS scoring requires at least one CoronaRadiata slice."
        )


def submit_annotation(db: Session, payload: SubmitAnnotation) -> AnnotationSession:
    """Atomic submission: writes evaluations and marks the AnnotationSession submitted."""
    ann_sess: Optional[AnnotationSession] = (
        db.query(AnnotationSession)
        .filter(
            AnnotationSession.annotation_session_uuid == payload.annotation_session_uuid
        )
        .first()
    )
    if not ann_sess:
        raise AnnotationSessionNotFoundError(
            f"AnnotationSession {payload.annotation_session_uuid} not found."
        )
    if ann_sess.submitted_at is not None:
        raise AnnotationSessionAlreadySubmittedError(
            "This annotation session has already been submitted."
        )

    needs_full_aspects = (
        payload.usability == ImageSetUsability.IschemicAssessable
        and not payload.low_quality
    )

    if needs_full_aspects:
        _validate_full_submission(payload.image_evaluations)

    # Always write set-level evaluation
    set_eval = ImageSetEvaluation(
        annotation_session_uuid=ann_sess.annotation_session_uuid,
        image_set_uuid=ann_sess.image_set_uuid,
        image_set_usability=payload.usability,
        ischemic_low_quality=payload.low_quality,
        notes=payload.notes,
    )
    db.add(set_eval)

    if needs_full_aspects:
        for img_data in payload.image_evaluations:
            scores = _normalize_scores(img_data)
            img_eval = ImageEvaluation(
                annotation_session_uuid=ann_sess.annotation_session_uuid,
                image_uuid=img_data.image_uuid,
                region=img_data.region,
                notes=img_data.notes,
                **scores,
            )
            db.add(img_eval)

    from datetime import datetime, timezone

    ann_sess.submitted_at = datetime.now(timezone.utc)
    ann_sess.auto_draft_payload = None
    ann_sess.auto_draft_saved_at = None
    db.commit()
    db.refresh(ann_sess)
    return ann_sess


def get_image_set_evaluation(
    db: Session, annotation_session_uuid: uuid.UUID
) -> Optional[ImageSetEvaluation]:
    return (
        db.query(ImageSetEvaluation)
        .filter(ImageSetEvaluation.annotation_session_uuid == annotation_session_uuid)
        .first()
    )


def get_image_evaluations(
    db: Session, annotation_session_uuid: uuid.UUID
) -> List[ImageEvaluation]:
    return (
        db.query(ImageEvaluation)
        .filter(ImageEvaluation.annotation_session_uuid == annotation_session_uuid)
        .all()
    )
