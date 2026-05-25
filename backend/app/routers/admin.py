"""Admin-only endpoints: doctor management, dataset assignment, audit log, drafts."""

import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import AnnotationSession, Doctors, ImageSet
from app.db.schemas import (
    AdminAuditLogRead,
    AssignDatasetRequest,
    DoctorCreate,
    DoctorDatasetAssignmentRead,
    DoctorRead,
    DoctorUpdate,
    DraftItem,
)
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
from app.services.credentials import change_password as reset_doctor_password, register_doctor
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
    admin: Doctors = Depends(get_current_admin),
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
            email=body.email,
            role=body.role,
            registration_source="admin_created",
        )
    except DuplicateEntryError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    audit_log(
        db, admin.uuid, "CREATE", "doctors", str(doctor.uuid), f"Created {doctor.username}"
    )
    return doctor


@router.patch("/doctors/{doctor_uuid}", response_model=DoctorRead)
def update_doctor(
    doctor_uuid: uuid.UUID,
    body: DoctorUpdate,
    db: Session = Depends(get_db),
    admin: Doctors = Depends(get_current_admin),
):
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
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No valid update fields provided",
        )
    return doctor


# ---------------------------------------------------------------------------
# Dataset assignment
# ---------------------------------------------------------------------------

@router.post("/assignments", response_model=DoctorDatasetAssignmentRead, status_code=status.HTTP_201_CREATED)
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
    return assignment


@router.get("/assignments/{doctor_uuid}", response_model=DoctorDatasetAssignmentRead)
def get_doctor_assignment(
    doctor_uuid: uuid.UUID,
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    result = get_active_assignment(db, doctor_uuid)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active assignment")
    return result


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_doctor_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    admin: Doctors = Depends(get_current_admin),
):
    try:
        revoke_assignment(db, assignment_id)
    except AssignmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    audit_log(db, admin.uuid, "REVOKE_ASSIGNMENT", "doctor_dataset_assignments", str(assignment_id))


# ---------------------------------------------------------------------------
# Draft management
# ---------------------------------------------------------------------------

@router.get("/drafts", response_model=List[DraftItem])
def list_all_drafts(
    db: Session = Depends(get_db),
    admin: Doctors = Depends(get_current_admin),
):
    """List all active drafts across all doctors."""
    rows = (
        db.query(AnnotationSession, ImageSet, Doctors)
        .join(ImageSet, AnnotationSession.image_set_uuid == ImageSet.uuid)
        .join(Doctors, AnnotationSession.doctor_uuid == Doctors.uuid)
        .filter(
            AnnotationSession.submitted_at.is_(None),
            AnnotationSession.draft_payload.isnot(None),
            AnnotationSession.draft_deleted_at.is_(None),
        )
        .order_by(AnnotationSession.draft_saved_at.desc())
        .all()
    )

    from sqlalchemy import func as _func
    index_rows = (
        db.query(ImageSet.uuid, _func.row_number().over(
            partition_by=ImageSet.dataset_uuid, order_by=ImageSet.uuid
        ).label("idx"))
        .subquery()
    )
    index_map = dict(db.query(index_rows.c.uuid, index_rows.c.idx).all())

    submitted_pairs = {
        (row.doctor_uuid, row.image_set_uuid)
        for row in db.query(AnnotationSession.doctor_uuid, AnnotationSession.image_set_uuid)
        .filter(AnnotationSession.submitted_at.isnot(None))
        .all()
    }

    result = []
    for sess, img_set, doctor in rows:
        result.append(DraftItem(
            annotation_session_uuid=sess.annotation_session_uuid,
            image_set_uuid=img_set.uuid,
            image_set_name=img_set.image_set_name,
            dataset_index=index_map.get(img_set.uuid, 0),
            icd_code=img_set.icd_code,
            num_images=img_set.num_images,
            draft_saved_at=sess.draft_saved_at,
            evaluated_by_me=(doctor.uuid, img_set.uuid) in submitted_pairs,
            doctor_uuid=doctor.uuid,
            doctor_username=doctor.username,
        ))
    return result


@router.delete("/drafts/{annotation_session_uuid}", status_code=status.HTTP_204_NO_CONTENT)
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

    ann_sess.draft_payload = None
    ann_sess.draft_deleted_at = datetime.now(timezone.utc)
    db.commit()
    audit_log(
        db, admin.uuid, "DELETE_DRAFT", "annotation_sessions",
        str(annotation_session_uuid),
        f"Admin deleted draft for doctor={ann_sess.doctor_uuid}",
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
