"""Evaluation endpoints — submit and read back annotation results."""

import json
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import AnnotationSession, Doctors, ImageSet
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not your session"
        )

    try:
        return submit_annotation(db, body)
    except AnnotationSessionAlreadySubmittedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except InvalidEvaluationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )


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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not your session"
        )

    result = get_image_set_evaluation(db, annotation_session_uuid)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No set-level evaluation found",
        )
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not your session"
        )

    return get_image_evaluations(db, annotation_session_uuid)


@router.post("/auto-draft", response_model=DraftRead)
def save_auto_draft(
    body: SaveDraft,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    """Persist an auto-save draft without overwriting any manually saved draft."""
    try:
        ann_sess = get_annotation_session(db, body.annotation_session_uuid)
    except AnnotationSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if ann_sess.doctor_uuid != doctor.uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not your session"
        )
    if ann_sess.submitted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Session already submitted"
        )

    now = datetime.now(timezone.utc)
    ann_sess.auto_draft_payload = body.model_dump_json()
    ann_sess.auto_draft_saved_at = now
    db.commit()

    return DraftRead(
        annotation_session_uuid=body.annotation_session_uuid,
        draft_saved_at=now,
        payload=body.model_dump(),
    )


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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not your session"
        )
    if ann_sess.submitted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Session already submitted"
        )

    now = datetime.now(timezone.utc)
    ann_sess.draft_payload = body.model_dump_json()
    ann_sess.draft_saved_at = now
    ann_sess.auto_draft_payload = None
    ann_sess.auto_draft_saved_at = None
    db.commit()

    return DraftRead(
        annotation_session_uuid=body.annotation_session_uuid,
        draft_saved_at=now,
        payload=body.model_dump(),
    )


@router.get("/submission/by-image-set/{image_set_uuid}", response_model=DraftRead)
def get_submission_by_image_set(
    image_set_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    """Return the latest submitted annotation for the current doctor + image set as a draft-shaped payload."""
    ann_sess = (
        db.query(AnnotationSession)
        .filter(
            AnnotationSession.doctor_uuid == doctor.uuid,
            AnnotationSession.image_set_uuid == image_set_uuid,
            AnnotationSession.submitted_at.isnot(None),
        )
        .order_by(AnnotationSession.submitted_at.desc())
        .first()
    )
    if ann_sess is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No submission found"
        )

    set_eval = get_image_set_evaluation(db, ann_sess.annotation_session_uuid)
    if not set_eval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation data missing"
        )

    _SCORE_FIELDS = [
        f"{z}_{side}_score"
        for z in ["c", "ic", "l", "i", "m1", "m2", "m3", "m4", "m5", "m6"]
        for side in ["left", "right"]
    ]
    img_evals = get_image_evaluations(db, ann_sess.annotation_session_uuid)
    payload = {
        "annotation_session_uuid": str(ann_sess.annotation_session_uuid),
        "usability": set_eval.image_set_usability.value,
        "low_quality": set_eval.ischemic_low_quality,
        "notes": set_eval.notes,
        "image_evaluations": [
            {
                "image_uuid": str(e.image_uuid),
                "region": e.region.value,
                "notes": e.notes,
                **{f: getattr(e, f).value for f in _SCORE_FIELDS},
            }
            for e in img_evals
        ],
    }
    return DraftRead(
        annotation_session_uuid=ann_sess.annotation_session_uuid,
        draft_saved_at=ann_sess.submitted_at,
        payload=payload,
        doctor_username=doctor.username,
        doctor_full_name=doctor.full_name,
    )


@router.get("/draft/by-image-set/{image_set_uuid}", response_model=DraftRead)
def get_draft_by_image_set(
    image_set_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    """Retrieve the most recent draft snapshot — whichever of manual or auto is newer."""
    from sqlalchemy import or_

    ann_sess = (
        db.query(AnnotationSession)
        .filter(
            AnnotationSession.doctor_uuid == doctor.uuid,
            AnnotationSession.image_set_uuid == image_set_uuid,
            AnnotationSession.submitted_at.is_(None),
            AnnotationSession.draft_deleted_at.is_(None),
            or_(
                AnnotationSession.draft_payload.isnot(None),
                AnnotationSession.auto_draft_payload.isnot(None),
            ),
        )
        .order_by(AnnotationSession.started_at.desc())
        .first()
    )
    if ann_sess is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No draft found"
        )

    # Pick whichever snapshot is newer within this session
    manual_ts = ann_sess.draft_saved_at
    auto_ts = ann_sess.auto_draft_saved_at
    use_auto = ann_sess.auto_draft_payload is not None and (
        manual_ts is None or (auto_ts is not None and auto_ts > manual_ts)
    )

    if use_auto:
        return DraftRead(
            annotation_session_uuid=ann_sess.annotation_session_uuid,
            draft_saved_at=auto_ts,
            payload=json.loads(ann_sess.auto_draft_payload),
            doctor_username=doctor.username,
            doctor_full_name=doctor.full_name,
        )
    return DraftRead(
        annotation_session_uuid=ann_sess.annotation_session_uuid,
        draft_saved_at=manual_ts,
        payload=json.loads(ann_sess.draft_payload),
        doctor_username=doctor.username,
        doctor_full_name=doctor.full_name,
    )


@router.get("/drafts/mine", response_model=List[DraftItem])
def list_my_drafts(
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    """List all active drafts for the current doctor (manual or auto-save)."""
    from sqlalchemy import or_

    rows = (
        db.query(AnnotationSession, ImageSet)
        .join(ImageSet, AnnotationSession.image_set_uuid == ImageSet.uuid)
        .filter(
            AnnotationSession.doctor_uuid == doctor.uuid,
            AnnotationSession.submitted_at.is_(None),
            AnnotationSession.draft_deleted_at.is_(None),
            or_(
                AnnotationSession.draft_payload.isnot(None),
                AnnotationSession.auto_draft_payload.isnot(None),
            ),
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

    index_rows = db.query(
        ImageSet.uuid,
        _func.row_number()
        .over(partition_by=ImageSet.dataset_uuid, order_by=ImageSet.uuid)
        .label("idx"),
    ).subquery()
    index_map = dict(db.query(index_rows.c.uuid, index_rows.c.idx).all())

    result = []
    for sess, img_set in rows:
        is_manual = sess.draft_payload is not None
        result.append(
            DraftItem(
                annotation_session_uuid=sess.annotation_session_uuid,
                image_set_uuid=img_set.uuid,
                image_set_name=img_set.image_set_name,
                dataset_index=index_map.get(img_set.uuid, 0),
                icd_code=img_set.icd_code,
                num_images=img_set.num_images,
                draft_saved_at=(
                    sess.draft_saved_at if is_manual else sess.auto_draft_saved_at
                ),
                draft_source="manual" if is_manual else "auto",
                evaluated_by_me=img_set.uuid in submitted_set_uuids,
            )
        )
    return result


@router.delete(
    "/draft/by-image-set/{image_set_uuid}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_draft_by_image_set(
    image_set_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    """Delete the active draft (manual or auto) for a doctor's image set."""
    from sqlalchemy import or_

    ann_sess = (
        db.query(AnnotationSession)
        .filter(
            AnnotationSession.doctor_uuid == doctor.uuid,
            AnnotationSession.image_set_uuid == image_set_uuid,
            AnnotationSession.submitted_at.is_(None),
            AnnotationSession.draft_deleted_at.is_(None),
            or_(
                AnnotationSession.draft_payload.isnot(None),
                AnnotationSession.auto_draft_payload.isnot(None),
            ),
        )
        .order_by(AnnotationSession.draft_saved_at.desc())
        .first()
    )
    if ann_sess is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No draft found"
        )

    now = datetime.now(timezone.utc)
    ann_sess.draft_payload = None
    ann_sess.auto_draft_payload = None
    ann_sess.auto_draft_saved_at = None
    ann_sess.draft_deleted_at = now
    db.commit()
