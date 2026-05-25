"""Admin-only endpoints: doctor management, dataset assignment, audit log."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import Doctors
from app.db.schemas import (
    AdminAuditLogRead,
    AssignDatasetRequest,
    DoctorCreate,
    DoctorDatasetAssignmentRead,
    DoctorRead,
    DoctorUpdate,
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
from app.services.credentials import register_doctor
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
            return doctor
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="No valid update fields provided",
    )


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
