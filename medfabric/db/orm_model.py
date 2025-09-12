"""Model definitions for the MedFabric ORM using SQLAlchemy.
Currently there is a problem with class ImageSet, Image and Sessions(?)
where the relationships cause pylint to show E1136:
E1136: Value 'Mapped' is unsubscriptable (unsubscriptable-object)
i dont know why, it seems to work fine otherwise.
"""

from __future__ import (
    annotations,
)  # this is needed for forward references in type hints, but i am in the future???

# pylint: disable = too-few-public-methods, invalid-name, missing-class-docstring, missing-function-docstring
import enum
import uuid as uuid_lib
from datetime import datetime
from typing import Optional, List
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import (
    String,
    Boolean,
    Integer,
    ForeignKey,
    Enum,
    DateTime,
    text,
    Identity,
)
from sqlalchemy.orm import (
    validates,
    mapped_column,
    Mapped,
    relationship,
)
from medfabric.db.database import Base


# --- Enums ---
class Region(enum.Enum):
    None_ = "None"
    BasalCentral = "BasalGangliaCentral"
    BasalCortex = "BasalGangliaCortex"
    CoronaRadiata = "CoronaRadiata"


class Gender(enum.Enum):
    Male = "Male"
    Female = "Female"
    Other = "Other"


class ConflictType(enum.Enum):
    Classification = "Classification"
    Score = "Score"
    Quality = "Quality"
    IrrelevantData = "IrrelevantData"


class DataSet(Base):
    __tablename__ = "datasets"

    dataset_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid_lib.uuid4, nullable=False, primary_key=True
    )
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)


# --- Tables ---
class Patient(Base):
    """Represents a patient and their initial diagnostic data."""

    __tablename__ = "patients"

    patient_id: Mapped[str] = mapped_column(String, nullable=False, primary_key=False)
    dataset_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.dataset_uuid"), nullable=True
    )
    patient_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid_lib.uuid4, primary_key=True
    )
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[Gender]] = mapped_column(Enum(Gender), nullable=True)

    image_sets: Mapped[List["ImageSet"]] = relationship(
        "ImageSet", back_populates="patient"
    )
    __table_args__ = (
        UniqueConstraint("patient_id", "dataset_uuid", name="uq_patient_dataset"),
    )


class Doctors(Base):
    __tablename__ = "doctors"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    @validates("username")
    def validate_username(self, key, value):
        if key != "username":
            return value
        if not value or len(value) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        return value


class ImageSet(Base):
    """Represents a unique CT scan session (image set) belonging to a patient."""

    __tablename__ = "image_sets"

    index: Mapped[int] = mapped_column(
        Integer,
        Identity(start=1, cycle=False),
        nullable=False,
        index=True,
    )
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid_lib.uuid4, nullable=False, primary_key=True
    )
    dataset_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.dataset_uuid"), nullable=False
    )
    image_set_name: Mapped[str] = mapped_column(String)

    patient_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.patient_uuid"),
        nullable=False,
    )
    num_images: Mapped[int] = mapped_column(Integer, nullable=False)
    folder_path: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    conflicted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    patient: Mapped["Patient"] = relationship("Patient", back_populates="image_sets")
    images: Mapped[List["Image"]] = relationship(
        "Image",
        back_populates="image_set",
        order_by="Image.slice_index",
    )
    __table_args__ = (
        UniqueConstraint(
            "image_set_name", "patient_uuid", "dataset_uuid", name="uq_imageset_patient"
        ),
    )


class Image(Base):
    __tablename__ = "images"
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid_lib.uuid4, nullable=False, primary_key=True
    )
    image_name: Mapped[str] = mapped_column(String, nullable=False, primary_key=False)
    image_set_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("image_sets.uuid"), nullable=False
    )
    slice_index: Mapped[int] = mapped_column(Integer, nullable=False)

    image_set: Mapped["ImageSet"] = relationship("ImageSet", back_populates="images")

    __table_args__ = (
        UniqueConstraint(
            "image_name", "image_set_uuid", "slice_index", name="uq_imageset_slice"
        ),
    )


class Session(Base):
    """Represents a doctor's login session.
    Args:
        doctor_uuid (UUID): The UUID of the doctor.
        login_time (datetime): The time the doctor logged in.
        is_active (bool): Whether the session is currently active.
    """

    __tablename__ = "sessions"

    session_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid_lib.uuid4
    )
    doctor_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.uuid"), nullable=False
    )
    login_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.now(),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ImageSetEvaluation(Base):
    __tablename__ = "image_set_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    doctor_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("doctors.uuid"),
        nullable=False,
    )
    image_set_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("image_sets.uuid"),
        nullable=False,
    )
    session_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.session_uuid"),
        nullable=False,
    )

    is_low_quality: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_irrelevant: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "doctor_uuid", "image_set_uuid", "session_uuid", name="uq_eval_triplet"
        ),
    )


class ImageEvaluation(Base):
    """Represents a doctor's evaluation of a single image."""

    __tablename__ = "image_evaluations"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    doctor_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "doctors.uuid",
        ),
        nullable=False,
    )
    image_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "images.uuid",
        ),
        nullable=False,
    )
    session_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.session_uuid"), nullable=False
    )
    region: Mapped[Region] = mapped_column(
        Enum(Region), default=Region.None_, nullable=False
    )
    basal_score_central_left: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    basal_score_central_right: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    basal_score_cortex_left: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    basal_score_cortex_right: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    corona_score_left: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    corona_score_right: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    @validates("region")
    def validate_region(self, key, value):
        if key != "region":
            return value
        if value not in Region:
            raise ValueError(f"Invalid region: {value}. Must be one of {list(Region)}.")
        return value

    __table_args__ = (
        UniqueConstraint(
            "doctor_uuid", "image_uuid", "session_uuid", name="uq_image_eval"
        ),
    )


# """
# class Conflict(Base):
#     """Represents a conflict found in evaluations."""
#
#     __tablename__ = "conflicts"
#
#     conflict_id: Mapped[int] = mapped_column(
#         Integer, primary_key=True, autoincrement=True
#     )
#     image_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
#     image_set_id: Mapped[str] = mapped_column(String, nullable=False)
#     conflict_type: Mapped[ConflictType] = mapped_column(
#         Enum(ConflictType), nullable=False
#     )
#     resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
#
#     __table_args__ = (
#         ForeignKeyConstraint(
#             ["image_set_id", "image_id"],
#             ["images.image_set_id", "images.image_id"],
#             use_alter=True,
#             name="fk_image_conflict",
#         ),
#     )
# """
