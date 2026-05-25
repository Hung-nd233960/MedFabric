"""Doctor registration and login service."""

import logging
import uuid
from typing import Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import DoctorRole, Doctors
from app.services.errors import (
    DatabaseError,
    DuplicateEntryError,
    InactiveAccountError,
    InvalidCredentialsError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)


def register_doctor(
    db: Session,
    username: str,
    password: str,
    email: Optional[str] = None,
    role: DoctorRole = DoctorRole.Doctor,
) -> Doctors:
    doctor = Doctors(
        uuid=uuid.uuid4(),
        username=username,
        email=email,
        password_hash=hash_password(password),
        role=role,
    )
    try:
        db.add(doctor)
        db.commit()
        db.refresh(doctor)
        logger.info("Registered doctor '%s'", username)
        return doctor
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateEntryError(f"Username or email already exists: {username}") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise DatabaseError(f"Failed to register doctor '{username}'") from exc


def authenticate_doctor(db: Session, username: str, password: str) -> Doctors:
    doctor: Optional[Doctors] = (
        db.query(Doctors).filter(Doctors.username == username).first()
    )
    if not doctor:
        raise UserNotFoundError(f"Doctor '{username}' not found.")
    if not doctor.is_active:
        raise InactiveAccountError(f"Account '{username}' is deactivated.")
    if not verify_password(password, doctor.password_hash):
        raise InvalidCredentialsError("Invalid password.")
    logger.info("Doctor '%s' authenticated", username)
    return doctor


def get_doctor_by_uuid(db: Session, doctor_uuid: uuid.UUID) -> Optional[Doctors]:
    return db.query(Doctors).filter(Doctors.uuid == doctor_uuid).first()


def get_doctor_by_username(db: Session, username: str) -> Optional[Doctors]:
    return db.query(Doctors).filter(Doctors.username == username).first()
