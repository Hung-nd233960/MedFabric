"""Login session management (one record per JWT issuance)."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import LoginSession


def create_login_session(db: Session, doctor_uuid: uuid.UUID) -> LoginSession:
    session = LoginSession(
        session_uuid=uuid.uuid4(),
        doctor_uuid=doctor_uuid,
        login_time=datetime.now(timezone.utc),
        is_active=True,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_login_session(db: Session, session_uuid: uuid.UUID) -> Optional[LoginSession]:
    return db.query(LoginSession).filter(
        LoginSession.session_uuid == session_uuid
    ).first()


def deactivate_login_session(db: Session, session_uuid: uuid.UUID) -> None:
    session = db.query(LoginSession).filter(
        LoginSession.session_uuid == session_uuid
    ).first()
    if session:
        session.is_active = False
        db.commit()


def deactivate_all_sessions_for_doctor(db: Session, doctor_uuid: uuid.UUID) -> None:
    """Invalidate all active sessions for a doctor — call on account deactivation."""
    db.query(LoginSession).filter(
        LoginSession.doctor_uuid == doctor_uuid,
        LoginSession.is_active == True,  # noqa: E712
    ).update({"is_active": False})
    db.commit()


def get_recent_sessions_for_doctor(
    db: Session, doctor_uuid: uuid.UUID, limit: int = 10
):
    return (
        db.query(LoginSession)
        .filter(LoginSession.doctor_uuid == doctor_uuid)
        .order_by(LoginSession.login_time.desc())
        .limit(limit)
        .all()
    )
