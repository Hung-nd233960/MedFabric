"""Evaluation endpoints — submit and read back annotation results."""

import json
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import AnnotationSession, Doctors, ImageSet, Patient
from app.db.schemas import (
    AnnotationSessionRead,
    DraftItem,
    DraftRead,
    ImageEvaluationRead,
    ImageSetEvaluationRead,
    SaveDraft,
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


@router.post("/draft", response_model=DraftRead)
def save_draft(
    body: SaveDraft,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    """Persist a partial annotation as a draft without finalising the session."""
    try:
        ann_sess = get_annotation_session(db, body.annotation_session_uuid)
    except AnnotationSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if ann_sess.doctor_uuid != doctor.uuid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your session")
    if ann_sess.submitted_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session already submitted")

    now = datetime.now(timezone.utc)
    ann_sess.draft_payload = body.model_dump_json()
    ann_sess.draft_saved_at = now
    db.commit()

    return DraftRead(
        annotation_session_uuid=body.annotation_session_uuid,
        draft_saved_at=now,
        payload=body.model_dump(),
    )


@router.get("/draft/by-image-set/{image_set_uuid}", response_model=DraftRead)
def get_draft_by_image_set(
    image_set_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    """Retrieve the most recent saved draft for a doctor + image set combination."""
    ann_sess = (
        db.query(AnnotationSession)
        .filter(
            AnnotationSession.doctor_uuid == doctor.uuid,
            AnnotationSession.image_set_uuid == image_set_uuid,
            AnnotationSession.submitted_at.is_(None),
            AnnotationSession.draft_payload.isnot(None),
        )
        .order_by(AnnotationSession.draft_saved_at.desc())
        .first()
    )

    if ann_sess is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No draft found")

    return DraftRead(
        annotation_session_uuid=ann_sess.annotation_session_uuid,
        draft_saved_at=ann_sess.draft_saved_at,
        payload=json.loads(ann_sess.draft_payload),
    )


@router.get("/drafts/mine", response_model=List[DraftItem])
def list_my_drafts(
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    """List all active drafts for the current doctor."""
    rows = (
        db.query(AnnotationSession, ImageSet)
        .join(ImageSet, AnnotationSession.image_set_uuid == ImageSet.uuid)
        .filter(
            AnnotationSession.doctor_uuid == doctor.uuid,
            AnnotationSession.submitted_at.is_(None),
            AnnotationSession.draft_payload.isnot(None),
            AnnotationSession.draft_deleted_at.is_(None),
        )
        .order_by(AnnotationSession.draft_saved_at.desc())
        .all()
    )

    # Submitted image sets — to derive "Annotated" column
    submitted_set_uuids = {
        row.image_set_uuid
        for row in db.query(AnnotationSession.image_set_uuid)
        .filter(
            AnnotationSession.doctor_uuid == doctor.uuid,
            AnnotationSession.submitted_at.isnot(None),
        )
        .all()
    }

    # Dataset index map: count position within dataset
    from sqlalchemy import func as _func
    index_rows = (
        db.query(ImageSet.uuid, _func.row_number().over(
            partition_by=ImageSet.dataset_uuid, order_by=ImageSet.uuid
        ).label("idx"))
        .subquery()
    )
    index_map = dict(db.query(index_rows.c.uuid, index_rows.c.idx).all())

    result = []
    for sess, img_set in rows:
        result.append(DraftItem(
            annotation_session_uuid=sess.annotation_session_uuid,
            image_set_uuid=img_set.uuid,
            image_set_name=img_set.image_set_name,
            dataset_index=index_map.get(img_set.uuid, 0),
            icd_code=img_set.icd_code,
            num_images=img_set.num_images,
            draft_saved_at=sess.draft_saved_at,
            evaluated_by_me=img_set.uuid in submitted_set_uuids,
        ))
    return result


@router.delete("/draft/by-image-set/{image_set_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft_by_image_set(
    image_set_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    """Delete the active draft for a doctor's image set."""
    ann_sess = (
        db.query(AnnotationSession)
        .filter(
            AnnotationSession.doctor_uuid == doctor.uuid,
            AnnotationSession.image_set_uuid == image_set_uuid,
            AnnotationSession.submitted_at.is_(None),
            AnnotationSession.draft_payload.isnot(None),
            AnnotationSession.draft_deleted_at.is_(None),
        )
        .order_by(AnnotationSession.draft_saved_at.desc())
        .first()
    )
    if ann_sess is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No draft found")

    now = datetime.now(timezone.utc)
    ann_sess.draft_payload = None
    ann_sess.draft_deleted_at = now
    db.commit()
