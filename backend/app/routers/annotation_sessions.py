"""AnnotationSession endpoints — open a session, then submit via evaluations router."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import Doctors, LoginSession
from app.db.schemas import AnnotationSessionCreate, AnnotationSessionRead
from app.deps import get_current_doctor
from app.services.annotation_sessions import (
    create_annotation_session,
    get_annotation_session,
    list_sessions_for_doctor,
)
from app.services.errors import AnnotationSessionNotFoundError
from app.services.login_sessions import get_recent_sessions_for_doctor

router = APIRouter(prefix="/annotation-sessions", tags=["annotation-sessions"])


def _get_latest_login_session(db: Session, doctor_uuid: uuid.UUID) -> uuid.UUID:
    """Return the most recent active login session UUID for this doctor."""
    sessions = get_recent_sessions_for_doctor(db, doctor_uuid, limit=1)
    if not sessions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No login session found — please log in again.",
        )
    return sessions[0].session_uuid


@router.post("/", response_model=AnnotationSessionRead, status_code=status.HTTP_201_CREATED)
def open_annotation_session(
    body: AnnotationSessionCreate,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    login_session_uuid = _get_latest_login_session(db, doctor.uuid)
    session = create_annotation_session(
        db,
        doctor_uuid=doctor.uuid,
        image_set_uuid=body.image_set_uuid,
        login_session_uuid=login_session_uuid,
    )
    return session


@router.get("/mine", response_model=List[AnnotationSessionRead])
def list_my_sessions(
    submitted_only: bool = False,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    return list_sessions_for_doctor(db, doctor.uuid, submitted_only=submitted_only)


@router.get("/{annotation_session_uuid}", response_model=AnnotationSessionRead)
def get_one_annotation_session(
    annotation_session_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    try:
        sess = get_annotation_session(db, annotation_session_uuid)
    except AnnotationSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if sess.doctor_uuid != doctor.uuid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your session")
    return sess
