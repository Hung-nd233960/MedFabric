"""Admin operations: doctor management, dataset assignment, audit logging."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import AdminAuditLog, DoctorDatasetAssignment, Doctors
from app.services.errors import (
    AssignmentNotFoundError,
    DatabaseError,
    UserNotFoundError,
)


# ---------------------------------------------------------------------------
# Doctor management
# ---------------------------------------------------------------------------

def list_doctors(db: Session, include_inactive: bool = False) -> List[Doctors]:
    q = db.query(Doctors)
    if not include_inactive:
        q = q.filter(Doctors.is_active.is_(True))
    return q.order_by(Doctors.username).all()


def set_doctor_active(db: Session, doctor_uuid: uuid.UUID, active: bool) -> Doctors:
    doctor = db.query(Doctors).filter(Doctors.uuid == doctor_uuid).first()
    if not doctor:
        raise UserNotFoundError(f"Doctor {doctor_uuid} not found.")
    doctor.is_active = active
    db.commit()
    db.refresh(doctor)
    return doctor


# ---------------------------------------------------------------------------
# Dataset assignment
# ---------------------------------------------------------------------------

def assign_dataset(
    db: Session, doctor_uuid: uuid.UUID, dataset_uuid: uuid.UUID
) -> DoctorDatasetAssignment:
    # Deactivate previous active assignment for this doctor
    db.query(DoctorDatasetAssignment).filter(
        DoctorDatasetAssignment.doctor_uuid == doctor_uuid,
        DoctorDatasetAssignment.is_active.is_(True),
    ).update({"is_active": False})

    assignment = DoctorDatasetAssignment(
        doctor_uuid=doctor_uuid,
        dataset_uuid=dataset_uuid,
        assigned_at=datetime.now(timezone.utc),
        is_active=True,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def get_active_assignment(
    db: Session, doctor_uuid: uuid.UUID
) -> Optional[DoctorDatasetAssignment]:
    return (
        db.query(DoctorDatasetAssignment)
        .filter(
            DoctorDatasetAssignment.doctor_uuid == doctor_uuid,
            DoctorDatasetAssignment.is_active.is_(True),
        )
        .first()
    )


def revoke_assignment(db: Session, assignment_id: int) -> None:
    assignment = (
        db.query(DoctorDatasetAssignment)
        .filter(DoctorDatasetAssignment.id == assignment_id)
        .first()
    )
    if not assignment:
        raise AssignmentNotFoundError(f"Assignment {assignment_id} not found.")
    assignment.is_active = False
    db.commit()


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def audit_log(
    db: Session,
    admin_uuid: uuid.UUID,
    action: str,
    target_table: str,
    target_id: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    entry = AdminAuditLog(
        admin_uuid=admin_uuid,
        action=action,
        target_table=target_table,
        target_id=target_id,
        detail=detail,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()


def get_audit_log(
    db: Session, limit: int = 200, offset: int = 0
) -> List[AdminAuditLog]:
    return (
        db.query(AdminAuditLog)
        .order_by(AdminAuditLog.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
