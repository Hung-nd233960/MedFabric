# pylint: disable=missing-module-docstring
# medfabric/api/sessions.py
import logging
from typing import Optional, List
import uuid as uuid_lib
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as db_Session
from pydantic import ValidationError
from medfabric.db.orm_model import Session, Doctors
from medfabric.db.pydantic_model import SessionCreate, SessionRead, SessionGetter
from medfabric.api.errors import (
    SessionNotFoundError,
    InvalidUUIDError,
    DatabaseError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)


def doctor_exists(db_session: db_Session, doctor_uuid: uuid_lib.UUID) -> bool:
    """Check if a doctor with this UUID exists."""
    return (
        db_session.query(Doctors).filter(Doctors.uuid == doctor_uuid).one_or_none()
        is not None
    )


def create_session(db_session: db_Session, doctor_uuid: uuid_lib.UUID) -> Session:
    """Create a new login session for a doctor."""
    try:
        new_session_validator = SessionCreate(doctor_uuid=doctor_uuid)
        doctor_uuid_ = new_session_validator.doctor_uuid
    except ValidationError as exc:
        raise InvalidUUIDError(f"Invalid doctor UUID: {exc}") from exc
    if not doctor_exists(db_session, doctor_uuid_):
        logger.error("Doctor UUID does not exist: %s", doctor_uuid_)
        raise UserNotFoundError(f"Doctor UUID does not exist: {doctor_uuid_}")

    try:
        new_sess = Session(doctor_uuid=doctor_uuid)
        db_session.add(new_sess)
        db_session.commit()
        db_session.refresh(new_sess)
        logger.info(
            "Created new session %s for doctor %s", new_sess.session_uuid, doctor_uuid
        )
        return new_sess
    except SQLAlchemyError as e:
        db_session.rollback()
        logger.exception(
            "Database error while creating session for doctor %s", doctor_uuid
        )
        raise DatabaseError(f"Failed to create session: {e}") from e


def get_session(
    db_session: db_Session, session_uuid: uuid_lib.UUID
) -> Optional[SessionRead]:
    """Retrieve session info by ID."""
    try:
        sess_uuid_validator = SessionGetter(session_uuid=session_uuid)
        sess_uuid = sess_uuid_validator.session_uuid
    except ValidationError as exc:
        raise InvalidUUIDError(f"Invalid session UUID: {exc}") from exc

    sess: Optional[Session] = db_session.get(Session, sess_uuid)
    if sess is not None:
        logger.debug("Retrieved session %s", sess_uuid)
        sess_ = SessionRead.model_validate(sess)
    else:
        sess_ = None
        logger.debug("Session %s not found", sess_uuid)
    return sess_


def deactivate_session(db_session: db_Session, session_uuid: uuid_lib.UUID) -> None:
    """Mark a session as inactive (logout)."""
    try:
        sess_uuid_validator = SessionGetter(session_uuid=session_uuid)
        sess_uuid = sess_uuid_validator.session_uuid
    except ValidationError as exc:
        raise InvalidUUIDError(f"Invalid session UUID: {exc}") from exc
    try:
        sess = db_session.get(Session, sess_uuid)
        if not sess:
            logger.error("Tried to deactivate non-existent session %s", sess_uuid)
            raise SessionNotFoundError(f"Session {sess_uuid} does not exist")

        sess.is_active = False
        db_session.commit()
        logger.info("Deactivated session %s", sess_uuid)

    except SQLAlchemyError as e:
        db_session.rollback()
        logger.exception("Database error while deactivating session %s", sess_uuid)
        raise DatabaseError(f"Failed to deactivate session {sess_uuid}") from e


def list_active_sessions(
    db_session: db_Session, doctor_uuid: uuid_lib.UUID
) -> List[SessionRead]:
    """Return all active sessions for a doctor."""
    try:
        doctor_id_validator = SessionCreate(doctor_uuid=doctor_uuid)
        doctor_uuid_ = doctor_id_validator.doctor_uuid
    except ValidationError as exc:
        raise InvalidUUIDError(f"Invalid doctor UUID: {exc}") from exc

    if not doctor_exists(db_session, doctor_uuid_):
        logger.error("Doctor UUID does not exist: %s", doctor_uuid_)
        raise UserNotFoundError(f"Doctor UUID {doctor_uuid_} does not exist")

    try:
        active_sessions = (
            db_session.query(Session)
            .filter(
                Session.doctor_uuid == doctor_uuid_,
                Session.is_active.is_(True),
            )
            .all()
        )
        logger.debug(
            "Found %d active sessions for doctor %s", len(active_sessions), doctor_uuid_
        )
        return [SessionRead.model_validate(sess) for sess in active_sessions]

    except SQLAlchemyError as e:
        db_session.rollback()
        logger.exception(
            "Database error while listing sessions for doctor %s", doctor_uuid
        )
        raise DatabaseError(f"Failed to list sessions for doctor {doctor_uuid}") from e
