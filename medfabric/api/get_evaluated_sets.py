import uuid as uuid_lib
from typing import List, Sequence, Tuple
from sqlalchemy import select, union
from sqlalchemy.orm import Session
from medfabric.db.orm_model import (
    Doctors,
    Image,
    ImageEvaluation,
    ImageSet,
    ImageSetEvaluation,
)


def get_doctor_image_sets(
    session: Session, doctor_uuid: uuid_lib.UUID
) -> List[uuid_lib.UUID]:
    """
    Given a doctor_id, return all unique ImageSet.uuids that doctor has annotated.
    Includes both rejected sets (image_set_evaluations) and valid sets (image_evaluations).
    """

    # From image_evaluations → Image → ImageSet
    q1 = (
        select(Image.image_set_uuid)
        .join(ImageEvaluation, ImageEvaluation.image_uuid == Image.uuid)
        .where(ImageEvaluation.doctor_uuid == doctor_uuid)
        .distinct()
    )
    # From image_set_evaluations directly
    q2 = (
        select(ImageSetEvaluation.image_set_uuid)
        .where(ImageSetEvaluation.doctor_uuid == doctor_uuid)
        .distinct()
    )

    # Union both queries
    union_q = union(q1, q2).subquery()

    # Fetch results
    rows = session.execute(select(union_q.c.image_set_uuid)).all()
    print("DEBUG:", rows)

    return [row[0] for row in rows]


def get_dataset_evaluation_status(
    session: Session,
    dataset_uuid: uuid_lib.UUID,
    doctor_username_blocklist: Sequence[str] = ("admin", "test"),
) -> Tuple[int, int, float]:
    """Return evaluated/total image-set counts and completion ratio for a dataset.

    Evaluation is considered complete for an image set if at least one non-blocklisted
    doctor has any evaluation record for that image set (either image-level or
    image-set-level).
    """

    normalized_blocklist = {
        username.strip().lower() for username in doctor_username_blocklist if username
    }
    blocked_usernames = {
        variant
        for username in normalized_blocklist
        for variant in (username, username.upper(), username.capitalize())
    }

    total_count = (
        session.query(ImageSet).filter(ImageSet.dataset_uuid == dataset_uuid).count()
    )

    q1 = (
        select(Image.image_set_uuid)
        .join(ImageEvaluation, ImageEvaluation.image_uuid == Image.uuid)
        .join(ImageSet, ImageSet.uuid == Image.image_set_uuid)
        .join(Doctors, Doctors.uuid == ImageEvaluation.doctor_uuid)
        .where(ImageSet.dataset_uuid == dataset_uuid)
    )

    q2 = (
        select(ImageSetEvaluation.image_set_uuid)
        .join(ImageSet, ImageSet.uuid == ImageSetEvaluation.image_set_uuid)
        .join(Doctors, Doctors.uuid == ImageSetEvaluation.doctor_uuid)
        .where(ImageSet.dataset_uuid == dataset_uuid)
    )

    if blocked_usernames:
        q1 = q1.where(Doctors.username.not_in(blocked_usernames))
        q2 = q2.where(Doctors.username.not_in(blocked_usernames))

    union_q = union(q1.distinct(), q2.distinct()).subquery()
    evaluated_count = len(
        session.execute(select(union_q.c.image_set_uuid).distinct()).all()
    )

    percent = round(evaluated_count / total_count, 2) if total_count else 0.0
    return evaluated_count, total_count, percent
