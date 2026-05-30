"""AnnotationSession service — create, open, and finalise annotation sessions."""

import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from app.db.models import AnnotationSession
from app.services.errors import (
    AnnotationSessionAlreadySubmittedError,
    AnnotationSessionNotFoundError,
)


def create_annotation_session(
    db: Session,
    doctor_uuid: uuid.UUID,
    image_set_uuid: uuid.UUID,
    login_session_uuid: uuid.UUID,
) -> AnnotationSession:
    session = AnnotationSession(
        annotation_session_uuid=uuid.uuid4(),
        doctor_uuid=doctor_uuid,
        image_set_uuid=image_set_uuid,
        login_session_uuid=login_session_uuid,
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_annotation_session(
    db: Session, annotation_session_uuid: uuid.UUID
) -> AnnotationSession:
    sess = (
        db.query(AnnotationSession)
        .filter(AnnotationSession.annotation_session_uuid == annotation_session_uuid)
        .first()
    )
    if not sess:
        raise AnnotationSessionNotFoundError(
            f"AnnotationSession {annotation_session_uuid} not found."
        )
    return sess


def mark_submitted(
    db: Session, annotation_session_uuid: uuid.UUID
) -> AnnotationSession:
    sess = get_annotation_session(db, annotation_session_uuid)
    if sess.submitted_at is not None:
        raise AnnotationSessionAlreadySubmittedError(
            f"AnnotationSession {annotation_session_uuid} already submitted."
        )
    sess.submitted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(sess)
    return sess


def list_sessions_for_doctor(
    db: Session, doctor_uuid: uuid.UUID, submitted_only: bool = False
) -> List[AnnotationSession]:
    q = db.query(AnnotationSession).filter(AnnotationSession.doctor_uuid == doctor_uuid)
    if submitted_only:
        q = q.filter(AnnotationSession.submitted_at.isnot(None))
    return q.order_by(AnnotationSession.started_at.desc()).all()


def has_doctor_evaluated(
    db: Session, doctor_uuid: uuid.UUID, image_set_uuid: uuid.UUID
) -> bool:
    return (
        db.query(AnnotationSession)
        .filter(
            AnnotationSession.doctor_uuid == doctor_uuid,
            AnnotationSession.image_set_uuid == image_set_uuid,
            AnnotationSession.submitted_at.isnot(None),
        )
        .first()
        is not None
    )
