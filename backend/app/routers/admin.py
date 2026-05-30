"""Admin-only endpoints: doctor management, dataset assignment, audit log, drafts."""

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import AnnotationSession, Doctors, DoctorRole, ImageSet
from app.db.schemas import (
    AdminAuditLogRead,
    AssignDatasetRequest,
    DoctorCreate,
    DoctorDatasetAssignmentRead,
    DoctorRead,
    DoctorUpdate,
    DraftItem,
    DraftRead,
    SubmissionRecord,
)
from app.services.evaluations import get_image_evaluations, get_image_set_evaluation
from app.deps import get_current_admin
from app.services.admin import (
    assign_dataset,
    audit_log,
    get_active_assignment,
    get_audit_log,
    list_doctors,
    revoke_assignment,
    set_doctor_active,
)
from app.services.credentials import (
    change_password as reset_doctor_password,
    register_doctor,
)
from app.services.errors import (
    AssignmentNotFoundError,
    DuplicateEntryError,
    UserNotFoundError,
)

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Doctor management
# ---------------------------------------------------------------------------


@router.get("/doctors", response_model=List[DoctorRead])
def list_all_doctors(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _admin: Doctors = Depends(get_current_admin),
):
    return list_doctors(db, include_inactive=include_inactive)


@router.post("/doctors", response_model=DoctorRead, status_code=status.HTTP_201_CREATED)
def create_doctor(
    body: DoctorCreate,
    db: Session = Depends(get_db),
    admin: Doctors = Depends(get_current_admin),
):
    try:
        doctor = register_doctor(
            db,
            username=body.username,
            password=body.password,
            full_name=body.full_name or None,
            email=body.email,
            role=body.role,
            is_test=body.is_test,
            must_change_password=True,
            must_set_name=not bool(body.full_name and body.full_name.strip()),
            registration_source="admin_created",
        )
    except DuplicateEntryError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    audit_log(
        db,
        admin.uuid,
        "CREATE",
        "doctors",
        str(doctor.uuid),
        f"Created {doctor.username}",
    )
    return doctor


@router.patch("/doctors/{doctor_uuid}", response_model=DoctorRead)
def update_doctor(
    doctor_uuid: uuid.UUID,
    body: DoctorUpdate,
    db: Session = Depends(get_db),
    admin: Doctors = Depends(get_current_admin),
):
    from app.services.credentials import get_doctor_by_uuid as _get_doc

    doctor = None
    try:
        if body.is_active is not None:
            doctor = set_doctor_active(db, doctor_uuid, body.is_active)
            audit_log(
                db,
                admin.uuid,
                "DEACTIVATE" if not body.is_active else "ACTIVATE",
                "doctors",
                str(doctor_uuid),
            )
        if body.password is not None:
            doctor = reset_doctor_password(
                db, doctor_uuid, body.password, must_change_password=True
            )
            audit_log(db, admin.uuid, "RESET_PASSWORD", "doctors", str(doctor_uuid))
        if body.full_name is not None:
            doc = _get_doc(db, doctor_uuid)
            if not doc:
                raise UserNotFoundError(f"Doctor {doctor_uuid} not found.")
            doc.full_name = body.full_name.strip() or None
            doc.must_set_name = not bool(doc.full_name)
            db.commit()
            db.refresh(doc)
            doctor = doc
            audit_log(db, admin.uuid, "UPDATE_NAME", "doctors", str(doctor_uuid))
        if body.is_test is not None:
            doc = _get_doc(db, doctor_uuid)
            if not doc:
                raise UserNotFoundError(f"Doctor {doctor_uuid} not found.")
            if not body.is_test:
                # Admins are permanently test accounts
                if doc.role == DoctorRole.Admin:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Admin accounts are always test accounts.",
                    )
                # Cannot remove test flag once the account has submitted annotations
                has_submissions = (
                    db.query(AnnotationSession.annotation_session_uuid)
                    .filter(
                        AnnotationSession.doctor_uuid == doc.uuid,
                        AnnotationSession.submitted_at.isnot(None),
                    )
                    .first()
                )
                if has_submissions:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "Cannot remove test flag: this account has submitted annotations."
                            " Test data cannot be retroactively counted toward global progress."
                        ),
                    )
            doc.is_test = body.is_test
            db.commit()
            db.refresh(doc)
            doctor = doc
            audit_log(
                db,
                admin.uuid,
                "SET_TEST" if body.is_test else "UNSET_TEST",
                "doctors",
                str(doctor_uuid),
            )
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No valid update fields provided",
        )
    return doctor


# ---------------------------------------------------------------------------
# Dataset assignment
# ---------------------------------------------------------------------------


def _assignment_with_progress(db: Session, assignment) -> DoctorDatasetAssignmentRead:
    """Build a DoctorDatasetAssignmentRead augmented with dataset total and doctor progress."""
    total = (
        db.query(func.count(ImageSet.uuid))
        .filter(ImageSet.dataset_uuid == assignment.dataset_uuid)
        .scalar()
        or 0
    )
    doctor_prog = (
        db.query(func.count(func.distinct(AnnotationSession.image_set_uuid)))
        .join(ImageSet, AnnotationSession.image_set_uuid == ImageSet.uuid)
        .filter(
            ImageSet.dataset_uuid == assignment.dataset_uuid,
            AnnotationSession.doctor_uuid == assignment.doctor_uuid,
            AnnotationSession.submitted_at.isnot(None),
        )
        .scalar()
        or 0
    )
    return DoctorDatasetAssignmentRead(
        id=assignment.id,
        doctor_uuid=assignment.doctor_uuid,
        dataset_uuid=assignment.dataset_uuid,
        assigned_at=assignment.assigned_at,
        is_active=assignment.is_active,
        total_image_sets=total,
        doctor_progress=doctor_prog,
    )


@router.post(
    "/assignments",
    response_model=DoctorDatasetAssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
def assign_doctor_to_dataset(
    body: AssignDatasetRequest,
    db: Session = Depends(get_db),
    admin: Doctors = Depends(get_current_admin),
):
    assignment = assign_dataset(db, body.doctor_uuid, body.dataset_uuid)
    audit_log(
        db,
        admin.uuid,
        "ASSIGN_DATASET",
        "doctor_dataset_assignments",
        str(assignment.id),
        f"doctor={body.doctor_uuid} dataset={body.dataset_uuid}",
    )
    return _assignment_with_progress(db, assignment)


@router.get("/assignments/{doctor_uuid}", response_model=DoctorDatasetAssignmentRead)
def get_doctor_assignment(
    doctor_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = get_active_assignment(db, doctor_uuid)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active assignment"
        )
    return _assignment_with_progress(db, result)


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_doctor_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    admin: Doctors = Depends(get_current_admin),
):
    try:
        revoke_assignment(db, assignment_id)
    except AssignmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    audit_log(
        db,
        admin.uuid,
        "REVOKE_ASSIGNMENT",
        "doctor_dataset_assignments",
        str(assignment_id),
    )


# ---------------------------------------------------------------------------
# Draft management
# ---------------------------------------------------------------------------


@router.get("/drafts", response_model=List[DraftItem])
def list_all_drafts(
    db: Session = Depends(get_db),
    _admin: Doctors = Depends(get_current_admin),
):
    """List all active drafts across all doctors."""
    from sqlalchemy import or_

    rows = (
        db.query(AnnotationSession, ImageSet, Doctors)
        .join(ImageSet, AnnotationSession.image_set_uuid == ImageSet.uuid)
        .join(Doctors, AnnotationSession.doctor_uuid == Doctors.uuid)
        .filter(
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

    index_rows = db.query(
        ImageSet.uuid,
        func.row_number()
        .over(partition_by=ImageSet.dataset_uuid, order_by=ImageSet.uuid)
        .label("idx"),
    ).subquery()
    index_map = dict(db.query(index_rows.c.uuid, index_rows.c.idx).all())

    submitted_pairs = {
        (row.doctor_uuid, row.image_set_uuid)
        for row in db.query(
            AnnotationSession.doctor_uuid, AnnotationSession.image_set_uuid
        )
        .filter(AnnotationSession.submitted_at.isnot(None))
        .all()
    }

    result = []
    for sess, img_set, doctor in rows:
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
                evaluated_by_me=(doctor.uuid, img_set.uuid) in submitted_pairs,
                doctor_uuid=doctor.uuid,
                doctor_username=doctor.username,
            )
        )
    return result


@router.delete(
    "/drafts/{annotation_session_uuid}", status_code=status.HTTP_204_NO_CONTENT
)
def admin_delete_draft(
    annotation_session_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    admin: Doctors = Depends(get_current_admin),
):
    """Admin deletes any draft by annotation session UUID."""
    ann_sess = (
        db.query(AnnotationSession)
        .filter(
            AnnotationSession.annotation_session_uuid == annotation_session_uuid,
            AnnotationSession.submitted_at.is_(None),
            AnnotationSession.draft_payload.isnot(None),
        )
        .first()
    )
    if ann_sess is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found"
        )

    ann_sess.draft_payload = None
    ann_sess.draft_deleted_at = datetime.now(timezone.utc)
    db.commit()
    audit_log(
        db,
        admin.uuid,
        "DELETE_DRAFT",
        "annotation_sessions",
        str(annotation_session_uuid),
        f"Admin deleted draft for doctor={ann_sess.doctor_uuid}",
    )


# ---------------------------------------------------------------------------
# Submissions view
# ---------------------------------------------------------------------------


@router.get("/submissions", response_model=List[SubmissionRecord])
def list_submissions(
    dataset_uuid: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """List all submitted annotation sessions with doctor info."""
    q = (
        db.query(AnnotationSession, ImageSet, Doctors)
        .join(ImageSet, AnnotationSession.image_set_uuid == ImageSet.uuid)
        .join(Doctors, AnnotationSession.doctor_uuid == Doctors.uuid)
        .filter(AnnotationSession.submitted_at.isnot(None))
    )
    if dataset_uuid:
        q = q.filter(ImageSet.dataset_uuid == dataset_uuid)
    q = q.order_by(AnnotationSession.submitted_at.desc())

    index_rows = db.query(
        ImageSet.uuid,
        func.row_number()
        .over(partition_by=ImageSet.dataset_uuid, order_by=ImageSet.uuid)
        .label("idx"),
    ).subquery()
    index_map = dict(db.query(index_rows.c.uuid, index_rows.c.idx).all())

    return [
        SubmissionRecord(
            annotation_session_uuid=sess.annotation_session_uuid,
            image_set_uuid=img_set.uuid,
            image_set_name=img_set.image_set_name,
            dataset_index=index_map.get(img_set.uuid, 0),
            icd_code=img_set.icd_code,
            doctor_uuid=doctor.uuid,
            doctor_username=doctor.username,
            doctor_full_name=doctor.full_name,
            submitted_at=sess.submitted_at,
        )
        for sess, img_set, doctor in q.all()
    ]


@router.get("/submission/by-image-set/{image_set_uuid}", response_model=DraftRead)
def get_submission_by_image_set_admin(
    image_set_uuid: uuid.UUID,
    doctor_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    """Admin: retrieve any doctor's submission for a specific image set."""
    ann_sess = (
        db.query(AnnotationSession)
        .filter(
            AnnotationSession.doctor_uuid == doctor_uuid,
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

    doctor = db.query(Doctors).filter(Doctors.uuid == doctor_uuid).first()
    set_eval = get_image_set_evaluation(db, ann_sess.annotation_session_uuid)
    if not set_eval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation data missing"
        )

    score_fields = [
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
                **{f: getattr(e, f).value for f in score_fields},
            }
            for e in img_evals
        ],
    }
    return DraftRead(
        annotation_session_uuid=ann_sess.annotation_session_uuid,
        draft_saved_at=ann_sess.submitted_at,
        payload=payload,
        doctor_username=doctor.username if doctor else None,
        doctor_full_name=doctor.full_name if doctor else None,
    )


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


@router.get("/audit-log", response_model=List[AdminAuditLogRead])
def get_admin_audit_log(
    limit: int = 200,
    offset: int = 0,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    return get_audit_log(db, limit=limit, offset=offset)
