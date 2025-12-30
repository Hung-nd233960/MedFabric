# pylint: disable=missing-function-docstring,missing-module-docstring
from typing import Optional
from uuid import UUID, uuid4
import logging
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from pydantic import ValidationError
from medfabric.db.orm_model import Doctors
from medfabric.db.pydantic_model import DoctorCreate, DoctorLogin
from medfabric.api.errors import (
    DatabaseError,
    UserNotFoundError,
    InvalidCredentialsError,
    DuplicateEntryError,
)

# Set up password hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    # DEBUG: password hashing is internal detail, not usually INFO
    logger.debug("Hashing password")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # DEBUG: verification attempt (but DO NOT log the actual password!)
    logger.debug("Verifying password for user login")
    return pwd_context.verify(plain_password, hashed_password)


def register_doctor(
    session: Session, username: str, password: str, **kwargs
) -> Doctors:
    try:
        # Validate input using Pydantic model
        doctor_validator = DoctorCreate(
            username=username,
            password_hash=hash_password(password),
            email=kwargs.get("email"),
        )
        username_ = doctor_validator.username
        password_hash = doctor_validator.password_hash
        email = doctor_validator.email
    except ValidationError as exc:
        raise DuplicateEntryError(f"Invalid doctor data: {exc}") from exc
    doctor = Doctors(
        uuid=uuid4(),
        username=username_,
        email=email,
        password_hash=password_hash,
    )
    try:
        session.add(doctor)
        session.commit()
        logger.info("Registered doctor '%s'", username_)
        return doctor

    except IntegrityError as exc:
        session.rollback()
        logger.error(
            "Failed to register doctor '%s': username already exists", username
        )
        raise DuplicateEntryError(f"Username '{username}' already exists.") from exc

    except SQLAlchemyError as exc:
        session.rollback()
        logger.exception("Database error during registration for '%s'", username)
        raise DatabaseError(f"Failed to register doctor '{username}'") from exc


def check_doctor_already_exists(session: Session, username: str) -> bool:
    """
    Check if a doctor with the given username already exists.

    Args:
        session (Session): SQLAlchemy DB session
        username (str): username to check

    Returns:
        True if exists, False otherwise
    """
    return session.query(Doctors).filter_by(username=username).one_or_none() is not None


def login_doctor(session: Session, username: str, password: str):
    try:
        login_validator = DoctorLogin(username=username, password=password)
        username_ = login_validator.username
        password_ = login_validator.password
    except ValidationError as exc:
        raise InvalidCredentialsError(f"Invalid login data: {exc}") from exc
    try:
        doctor = session.query(Doctors).filter_by(username=username_).first()
    except SQLAlchemyError as exc:
        logger.exception("Database error during login for '%s'", username_)
        raise DatabaseError(f"Failed to login doctor '{username_}'") from exc

    if not doctor:
        logger.info("Login failed: username not found '%s'", username_)
        raise UserNotFoundError(f"Doctor with username '{username_}' not found.")

    if verify_password(password_, doctor.password_hash):
        logger.info("Login successful for '%s'", username_)
        return doctor

    logger.info("Login failed: invalid password for '%s'", username_)
    raise InvalidCredentialsError("Invalid password.")


def get_uuid_from_username(session, username: str) -> Optional[UUID]:
    doctor = session.query(Doctors).filter_by(username=username).first()
    return doctor.uuid if doctor else None


def get_username_from_uuid(session, uuid: UUID) -> Optional[str]:
    doctor = session.query(Doctors).filter_by(uuid=uuid).first()
    return doctor.username if doctor else None
