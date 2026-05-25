"""Dashboard statistics service."""

import uuid
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import AnnotationSession, DataSet, ImageSet
from app.db.schemas import DashboardStats
from app.services.admin import get_active_assignment


def get_dashboard_stats(db: Session, doctor_uuid: uuid.UUID) -> DashboardStats:
    assignment = get_active_assignment(db, doctor_uuid)
    assigned_dataset = None

    if assignment:
        ds = db.query(DataSet).filter(
            DataSet.dataset_uuid == assignment.dataset_uuid
        ).first()
        if ds:
            from app.db.schemas import DataSetRead
            assigned_dataset = DataSetRead.model_validate(ds)

    dataset_uuid = assignment.dataset_uuid if assignment else None

    total_image_sets = 0
    my_progress = 0
    global_progress = 0

    if dataset_uuid:
        total_image_sets = (
            db.query(func.count(ImageSet.index))
            .filter(ImageSet.dataset_uuid == dataset_uuid, ImageSet.is_active.is_(True))
            .scalar()
            or 0
        )

        my_progress = (
            db.query(func.count(func.distinct(AnnotationSession.image_set_uuid)))
            .join(ImageSet, ImageSet.uuid == AnnotationSession.image_set_uuid)
            .filter(
                AnnotationSession.doctor_uuid == doctor_uuid,
                AnnotationSession.submitted_at.isnot(None),
                ImageSet.dataset_uuid == dataset_uuid,
            )
            .scalar()
            or 0
        )

        # Global = unique image_sets with ≥1 submitted annotation
        global_progress = (
            db.query(func.count(func.distinct(AnnotationSession.image_set_uuid)))
            .join(ImageSet, ImageSet.uuid == AnnotationSession.image_set_uuid)
            .filter(
                AnnotationSession.submitted_at.isnot(None),
                ImageSet.dataset_uuid == dataset_uuid,
            )
            .scalar()
            or 0
        )

    return DashboardStats(
        assigned_dataset=assigned_dataset,
        my_progress=my_progress,
        global_progress=global_progress,
        total_image_sets=total_image_sets,
    )
