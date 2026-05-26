"""Doctor registration, login, and password management service."""

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
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    role: DoctorRole = DoctorRole.Doctor,
    is_test: bool = False,
    must_change_password: bool = False,
    must_set_name: bool = False,
    registration_source: str = "admin_created",
) -> Doctors:
    # Admins are always test accounts — their annotations must not count toward global progress
    effective_is_test = True if role == DoctorRole.Admin else is_test
    doctor = Doctors(
        uuid=uuid.uuid4(),
        username=username,
        full_name=full_name or None,
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_test=effective_is_test,
        must_change_password=must_change_password,
        must_set_name=must_set_name,
        registration_source=registration_source,
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


def change_password(
    db: Session,
    doctor_uuid: uuid.UUID,
    new_password: str,
    must_change_password: bool = False,
) -> Doctors:
    doctor = get_doctor_by_uuid(db, doctor_uuid)
    if not doctor:
        raise UserNotFoundError(f"Doctor {doctor_uuid} not found.")
    doctor.password_hash = hash_password(new_password)
    doctor.must_change_password = must_change_password
    db.commit()
    db.refresh(doctor)
    logger.info("Password changed for doctor '%s'", doctor.username)
    return doctor


def get_doctor_by_uuid(db: Session, doctor_uuid: uuid.UUID) -> Optional[Doctors]:
    return db.query(Doctors).filter(Doctors.uuid == doctor_uuid).first()


def get_doctor_by_username(db: Session, username: str) -> Optional[Doctors]:
    return db.query(Doctors).filter(Doctors.username == username).first()
