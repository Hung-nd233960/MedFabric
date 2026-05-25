"""DataSet CRUD service."""

import uuid
from typing import List, Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import DataSet
from app.services.errors import (
    DatabaseError,
    DataSetAlreadyExistsError,
    DataSetNotFoundError,
    InvalidDataSetError,
)


def create_dataset(
    db: Session,
    name: str,
    description: Optional[str] = None,
) -> DataSet:
    if not name or not name.strip():
        raise InvalidDataSetError("Dataset name cannot be empty.")
    if db.query(DataSet).filter(DataSet.name == name).first():
        raise DataSetAlreadyExistsError(f"Dataset '{name}' already exists.")
    ds = DataSet(dataset_uuid=uuid.uuid4(), name=name.strip(), description=description)
    try:
        db.add(ds)
        db.commit()
        db.refresh(ds)
        return ds
    except IntegrityError as exc:
        db.rollback()
        raise DataSetAlreadyExistsError(f"Dataset '{name}' already exists.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise DatabaseError(str(exc)) from exc


def get_dataset(db: Session, dataset_uuid: uuid.UUID) -> DataSet:
    ds = db.query(DataSet).filter(DataSet.dataset_uuid == dataset_uuid).first()
    if not ds:
        raise DataSetNotFoundError(f"Dataset {dataset_uuid} not found.")
    return ds


def list_datasets(db: Session, active_only: bool = True) -> List[DataSet]:
    q = db.query(DataSet)
    if active_only:
        q = q.filter(DataSet.is_active.is_(True))
    return q.order_by(DataSet.name).all()


def update_dataset(
    db: Session,
    dataset_uuid: uuid.UUID,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> DataSet:
    ds = get_dataset(db, dataset_uuid)
    if description is not None:
        ds.description = description
    if is_active is not None:
        ds.is_active = is_active
    db.commit()
    db.refresh(ds)
    return ds
