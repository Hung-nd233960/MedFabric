"""Admin operations: doctor management, dataset assignment, audit logging, analytics."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    AdminAuditLog,
    AnnotationSession,
    DataSet,
    DoctorDatasetAssignment,
    Doctors,
    ImageSet,
    ImageSetEvaluation,
)
from app.services.errors import (
    AssignmentNotFoundError,
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


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


def get_dataset_analytics(db: Session, dataset_uuid: uuid.UUID) -> Dict[str, Any]:
    ds = db.query(DataSet).filter(DataSet.dataset_uuid == dataset_uuid).first()
    total: int = (
        db.query(func.count(ImageSet.uuid))
        .filter(ImageSet.dataset_uuid == dataset_uuid)
        .scalar() or 0
    )

    # ── Global stats (non-test accounts only) ────────────────────────────────

    annotated: int = (
        db.query(func.count(func.distinct(AnnotationSession.image_set_uuid)))
        .join(ImageSet, AnnotationSession.image_set_uuid == ImageSet.uuid)
        .join(Doctors, AnnotationSession.doctor_uuid == Doctors.uuid)
        .filter(
            ImageSet.dataset_uuid == dataset_uuid,
            AnnotationSession.submitted_at.isnot(None),
            Doctors.is_test.is_(False),
        )
        .scalar() or 0
    )

    contributor_rows = (
        db.query(
            Doctors.uuid,
            Doctors.username,
            Doctors.full_name,
            func.count(func.distinct(AnnotationSession.image_set_uuid)).label("cnt"),
        )
        .join(AnnotationSession, AnnotationSession.doctor_uuid == Doctors.uuid)
        .join(ImageSet, AnnotationSession.image_set_uuid == ImageSet.uuid)
        .filter(
            ImageSet.dataset_uuid == dataset_uuid,
            AnnotationSession.submitted_at.isnot(None),
            Doctors.is_test.is_(False),
        )
        .group_by(Doctors.uuid, Doctors.username, Doctors.full_name)
        .order_by(func.count(func.distinct(AnnotationSession.image_set_uuid)).desc())
        .all()
    )

    usability_rows = (
        db.query(
            ImageSetEvaluation.image_set_usability,
            ImageSetEvaluation.ischemic_low_quality,
            func.count().label("cnt"),
        )
        .join(
            AnnotationSession,
            ImageSetEvaluation.annotation_session_uuid == AnnotationSession.annotation_session_uuid,
        )
        .join(ImageSet, AnnotationSession.image_set_uuid == ImageSet.uuid)
        .join(Doctors, AnnotationSession.doctor_uuid == Doctors.uuid)
        .filter(
            ImageSet.dataset_uuid == dataset_uuid,
            Doctors.is_test.is_(False),
        )
        .group_by(ImageSetEvaluation.image_set_usability, ImageSetEvaluation.ischemic_low_quality)
        .all()
    )
    usability_counts: Dict[str, int] = {}
    for row in usability_rows:
        if row.image_set_usability.value == "IschemicAssessable":
            bucket = "IschemicLowQuality" if row.ischemic_low_quality else "IschemicAssessable"
        else:
            bucket = row.image_set_usability.value
        usability_counts[bucket] = usability_counts.get(bucket, 0) + row.cnt

    # ── Per-doctor stats (all accounts including test) ────────────────────────

    per_doctor_rows = (
        db.query(
            Doctors.uuid,
            Doctors.username,
            Doctors.full_name,
            Doctors.is_test,
            func.count(func.distinct(AnnotationSession.image_set_uuid)).label("cnt"),
            func.max(AnnotationSession.submitted_at).label("last_annotation"),
        )
        .join(AnnotationSession, AnnotationSession.doctor_uuid == Doctors.uuid)
        .join(ImageSet, AnnotationSession.image_set_uuid == ImageSet.uuid)
        .filter(
            ImageSet.dataset_uuid == dataset_uuid,
            AnnotationSession.submitted_at.isnot(None),
        )
        .group_by(Doctors.uuid, Doctors.username, Doctors.full_name, Doctors.is_test)
        .order_by(func.count(func.distinct(AnnotationSession.image_set_uuid)).desc())
        .all()
    )

    # Per-doctor usability breakdown (all accounts)
    per_doctor_usability: Dict[str, Dict[str, int]] = {}
    if per_doctor_rows:
        doc_uuids = [row.uuid for row in per_doctor_rows]
        detail_rows = (
            db.query(
                AnnotationSession.doctor_uuid,
                ImageSetEvaluation.image_set_usability,
                ImageSetEvaluation.ischemic_low_quality,
                func.count().label("cnt"),
            )
            .join(
                ImageSetEvaluation,
                ImageSetEvaluation.annotation_session_uuid == AnnotationSession.annotation_session_uuid,
            )
            .join(ImageSet, AnnotationSession.image_set_uuid == ImageSet.uuid)
            .filter(
                ImageSet.dataset_uuid == dataset_uuid,
                AnnotationSession.submitted_at.isnot(None),
                AnnotationSession.doctor_uuid.in_(doc_uuids),
            )
            .group_by(
                AnnotationSession.doctor_uuid,
                ImageSetEvaluation.image_set_usability,
                ImageSetEvaluation.ischemic_low_quality,
            )
            .all()
        )
        for row in detail_rows:
            key = str(row.doctor_uuid)
            if row.image_set_usability.value == "IschemicAssessable":
                bucket = "IschemicLowQuality" if row.ischemic_low_quality else "IschemicAssessable"
            else:
                bucket = row.image_set_usability.value
            doc_counts = per_doctor_usability.setdefault(key, {})
            doc_counts[bucket] = doc_counts.get(bucket, 0) + row.cnt

    return {
        "dataset": {"name": ds.name if ds else "Unknown", "total_image_sets": total},
        "global": {
            "annotated_sets": annotated,
            "unannotated_sets": total - annotated,
            "contributors": [
                {
                    "doctor_uuid": str(row.uuid),
                    "username": row.username,
                    "full_name": row.full_name,
                    "unique_sets": row.cnt,
                }
                for row in contributor_rows
            ],
            "usability_counts": {
                "IschemicAssessable": usability_counts.get("IschemicAssessable", 0),
                "IschemicLowQuality": usability_counts.get("IschemicLowQuality", 0),
                "HemorrhagicPresent": usability_counts.get("HemorrhagicPresent", 0),
                "Anomaly": usability_counts.get("Anomaly", 0),
                "Irrelevant": usability_counts.get("Irrelevant", 0),
            },
        },
        "per_doctor": [
            {
                "doctor_uuid": str(row.uuid),
                "username": row.username,
                "full_name": row.full_name,
                "is_test": row.is_test,
                "annotated_count": row.cnt,
                "last_annotation": row.last_annotation.isoformat() if row.last_annotation else None,
                "usability_counts": per_doctor_usability.get(str(row.uuid), {}),
            }
            for row in per_doctor_rows
        ],
    }
