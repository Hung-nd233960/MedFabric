"""Evaluation endpoints — submit and read back annotation results."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import Doctors
from app.db.schemas import (
    AnnotationSessionRead,
    ImageEvaluationRead,
    ImageSetEvaluationRead,
    SubmitAnnotation,
)
from app.deps import get_current_doctor
from app.services.errors import (
    AnnotationSessionAlreadySubmittedError,
    AnnotationSessionNotFoundError,
    InvalidEvaluationError,
)
from app.services.evaluations import (
    get_image_evaluations,
    get_image_set_evaluation,
    submit_annotation,
)
from app.services.annotation_sessions import get_annotation_session

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("/submit", response_model=AnnotationSessionRead)
def submit(
    body: SubmitAnnotation,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    # Verify ownership
    try:
        ann_sess = get_annotation_session(db, body.annotation_session_uuid)
    except AnnotationSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if ann_sess.doctor_uuid != doctor.uuid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your session")

    try:
        return submit_annotation(db, body)
    except AnnotationSessionAlreadySubmittedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except InvalidEvaluationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get(
    "/{annotation_session_uuid}/set-evaluation",
    response_model=ImageSetEvaluationRead,
)
def get_set_eval(
    annotation_session_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    try:
        ann_sess = get_annotation_session(db, annotation_session_uuid)
    except AnnotationSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if ann_sess.doctor_uuid != doctor.uuid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your session")

    result = get_image_set_evaluation(db, annotation_session_uuid)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No set-level evaluation found")
    return result


@router.get(
    "/{annotation_session_uuid}/image-evaluations",
    response_model=List[ImageEvaluationRead],
)
def get_image_evals(
    annotation_session_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    try:
        ann_sess = get_annotation_session(db, annotation_session_uuid)
    except AnnotationSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if ann_sess.doctor_uuid != doctor.uuid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your session")

    return get_image_evaluations(db, annotation_session_uuid)
