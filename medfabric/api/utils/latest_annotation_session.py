# pylint: disable=C0121, missing-module-docstring
# medfabric/api/utils/latest_annotation_session.py
from dataclasses import dataclass
from typing import Optional, List

import uuid as uuid_lib
from sqlalchemy.orm import Session as db_Session
from sqlalchemy import select
from medfabric.db.models import (
    Image,
    Session,
    ImageSetEvaluation,
    ImageEvaluation,
)


@dataclass
class EvaluationResult:
    """Holds the result of the latest evaluation retrieval."""

    session_id: uuid_lib.UUID
    image_set_evaluation: Optional[ImageSetEvaluation]
    image_evaluations: List[ImageEvaluation]


def get_last_evaluation(
    db: db_Session, doctor_id: uuid_lib.UUID, image_set_uuid: uuid_lib.UUID
) -> Optional[EvaluationResult]:
    """Retrieve the latest evaluation session for a doctor and image set.
    Args:
        db (Session): SQLAlchemy DB session
        doctor_id (uuid.UUID): ID of the doctor
        image_set_uuid (uuid.UUID): ID of the image set
    Returns:"""
    # 1. Find latest inactive session *that has evaluations for this set*
    last_session = db.execute(
        select(Session)
        .where(
            Session.doctor_id == doctor_id,
            Session.is_active == False,  # noqa: E712
            Session.session_id.in_(
                # Subquery: session_ids where this doctor evaluated this set
                select(ImageSetEvaluation.session_id)
                .where(
                    ImageSetEvaluation.doctor_id == doctor_id,
                    ImageSetEvaluation.image_set_uuid == image_set_uuid,
                )
                .union(
                    select(ImageEvaluation.session_id)
                    .join(Image)
                    .where(
                        ImageEvaluation.doctor_id == doctor_id,
                        Image.image_set_uuid == image_set_uuid,
                    )
                )
            ),
        )
        .order_by(Session.login_time.desc())
        .limit(1)
    ).scalar_one_or_none()

    if not last_session:
        return None

    # 2. Fetch ImageSetEvaluation (maybe 1)
    ise = db.execute(
        select(ImageSetEvaluation).where(
            ImageSetEvaluation.doctor_id == doctor_id,
            ImageSetEvaluation.image_set_uuid == image_set_uuid,
            ImageSetEvaluation.session_id == last_session.session_id,
        )
    ).scalar_one_or_none()

    # 3. Fetch ImageEvaluations (many)
    ie_list = (
        db.execute(
            select(ImageEvaluation)
            .join(Image)
            .where(
                ImageEvaluation.doctor_id == doctor_id,
                ImageEvaluation.session_id == last_session.session_id,
                Image.image_set_uuid == image_set_uuid,
            )
        )
        .scalars()
        .all()
    )

    if not ise and not ie_list:
        return None

    return EvaluationResult(
        session_id=last_session.session_id,
        image_set_evaluation=ise,
        image_evaluations=list(ie_list),
    )
