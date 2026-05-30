"""SQLAlchemy ORM models for MedFabric 3.0.

Key changes from v2:
- Session renamed to LoginSession; AnnotationSession added as separate concept
- AnnotationSession is the FK anchor for both ImageSetEvaluation and ImageEvaluation
- ImageSetUsability gains Irrelevant variant
- Doctors and ImageSet gain is_active soft-delete flag
- DoctorDatasetAssignment tracks admin→doctor dataset delegation
- AdminAuditLog records all admin mutations
- Bilateral scoring: every ASPECTS zone has _left and _right columns
- ImageSetEvaluation gains notes column
- conflicted field dropped from ImageSet (out of scope)
"""

from __future__ import annotations

import enum
import uuid as uuid_lib
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.types import CHAR, TypeDecorator

from app.core.database import Base


# ---------------------------------------------------------------------------
# Custom UUID type (PostgreSQL native UUID, SQLite CHAR(36))
# ---------------------------------------------------------------------------

class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid_lib.UUID) else uuid_lib.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid_lib.UUID):
            return value
        return uuid_lib.UUID(str(value))


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ImageFormat(enum.Enum):
    DICOM = "DICOM"
    JPEG = "JPEG"
    PNG = "PNG"


class Region(enum.Enum):
    None_ = "None"
    BasalGanglia = "BasalGanglia"
    CoronaRadiata = "CoronaRadiata"


class ImageSetUsability(enum.Enum):
    IschemicAssessable = "IschemicAssessable"
    HemorrhagicPresent = "HemorrhagicPresent"
    Anomaly = "Anomaly"
    Irrelevant = "Irrelevant"


class RegionScore(enum.Enum):
    Affected = "Affected"
    Not_Affected = "Not_Affected"
    Not_In_This_Slice = "Not_In_This_Slice"
    Not_Applicable = "Not_Applicable"


class Gender(enum.Enum):
    Male = "Male"
    Female = "Female"
    Other = "Other"


class DoctorRole(enum.Enum):
    Doctor = "Doctor"
    Admin = "Admin"


# ---------------------------------------------------------------------------
# Core tables
# ---------------------------------------------------------------------------

class DataSet(Base):
    __tablename__ = "datasets"

    dataset_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid_lib.uuid4, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    patients: Mapped[List["Patient"]] = relationship("Patient", back_populates="dataset")
    assignments: Mapped[List["DoctorDatasetAssignment"]] = relationship(
        "DoctorDatasetAssignment", back_populates="dataset"
    )


class Patient(Base):
    __tablename__ = "patients"

    patient_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid_lib.uuid4
    )
    patient_id: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), ForeignKey("datasets.dataset_uuid"), nullable=False
    )
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[Gender]] = mapped_column(Enum(Gender), nullable=True)

    dataset: Mapped["DataSet"] = relationship("DataSet", back_populates="patients")
    image_sets: Mapped[List["ImageSet"]] = relationship(
        "ImageSet", back_populates="patient"
    )

    __table_args__ = (
        UniqueConstraint("patient_id", "dataset_uuid", name="uq_patient_dataset"),
    )


class Doctors(Base):
    __tablename__ = "doctors"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid_lib.uuid4
    )
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[DoctorRole] = mapped_column(
        Enum(DoctorRole), nullable=False, default=DoctorRole.Doctor
    )
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    must_set_name: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    registration_source: Mapped[str] = mapped_column(String(64), nullable=False, default="admin_created")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    last_seen: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
    )
    preferences: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, default=None,
    )

    login_sessions: Mapped[List["LoginSession"]] = relationship(
        "LoginSession", back_populates="doctor"
    )
    annotation_sessions: Mapped[List["AnnotationSession"]] = relationship(
        "AnnotationSession", back_populates="doctor"
    )
    assignments: Mapped[List["DoctorDatasetAssignment"]] = relationship(
        "DoctorDatasetAssignment", back_populates="doctor"
    )

    @validates("username")
    def validate_username(self, key, value):
        if not value or len(value) < 3:
            raise ValueError("Username must be at least 3 characters.")
        return value


class ImageSet(Base):
    __tablename__ = "image_sets"

    index: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, nullable=False
    )
    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), unique=True, nullable=False, default=uuid_lib.uuid4
    )
    dataset_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), ForeignKey("datasets.dataset_uuid"), nullable=False
    )
    patient_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), ForeignKey("patients.patient_uuid"), nullable=False
    )
    image_set_name: Mapped[str] = mapped_column(String(512), nullable=False)
    image_format: Mapped[ImageFormat] = mapped_column(
        Enum(ImageFormat), nullable=False, default=ImageFormat.DICOM
    )
    image_window_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_window_width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    num_images: Mapped[int] = mapped_column(Integer, nullable=False)
    folder_path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icd_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )

    patient: Mapped["Patient"] = relationship("Patient", back_populates="image_sets")
    images: Mapped[List["Image"]] = relationship(
        "Image", back_populates="image_set", order_by="Image.slice_index"
    )

    __table_args__ = (
        UniqueConstraint(
            "image_set_name", "patient_uuid", "dataset_uuid", name="uq_imageset_patient"
        ),
    )


class Image(Base):
    __tablename__ = "images"

    uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid_lib.uuid4
    )
    image_name: Mapped[str] = mapped_column(String(512), nullable=False)
    image_set_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), ForeignKey("image_sets.uuid"), nullable=False
    )
    slice_index: Mapped[int] = mapped_column(Integer, nullable=False)

    image_set: Mapped["ImageSet"] = relationship("ImageSet", back_populates="images")

    __table_args__ = (
        UniqueConstraint(
            "image_name", "image_set_uuid", "slice_index", name="uq_imageset_slice"
        ),
    )


# ---------------------------------------------------------------------------
# Session tables
# ---------------------------------------------------------------------------

class LoginSession(Base):
    """Records each doctor login event (JWT issuance)."""

    __tablename__ = "login_sessions"

    session_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid_lib.uuid4
    )
    doctor_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), ForeignKey("doctors.uuid"), nullable=False
    )
    login_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    doctor: Mapped["Doctors"] = relationship("Doctors", back_populates="login_sessions")


class AnnotationSession(Base):
    """Represents one doctor's decision to annotate a specific image set.

    Every ImageSetEvaluation and ImageEvaluation is anchored to exactly one
    AnnotationSession, which ties the submission to both the doctor and the
    login session it occurred in.  Multiple AnnotationSessions for the same
    (doctor, image_set) are allowed — each represents an independent re-annotation.
    """

    __tablename__ = "annotation_sessions"

    annotation_session_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid_lib.uuid4
    )
    doctor_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), ForeignKey("doctors.uuid"), nullable=False
    )
    image_set_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), ForeignKey("image_sets.uuid"), nullable=False
    )
    login_session_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), ForeignKey("login_sessions.session_uuid"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    draft_payload: Mapped[Optional[str]] = mapped_column(
        Text(), nullable=True
    )
    draft_saved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    draft_deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    auto_draft_payload: Mapped[Optional[str]] = mapped_column(
        Text(), nullable=True
    )
    auto_draft_saved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    doctor: Mapped["Doctors"] = relationship(
        "Doctors", back_populates="annotation_sessions"
    )
    image_set_evaluation: Mapped[Optional["ImageSetEvaluation"]] = relationship(
        "ImageSetEvaluation", back_populates="annotation_session", uselist=False
    )
    image_evaluations: Mapped[List["ImageEvaluation"]] = relationship(
        "ImageEvaluation", back_populates="annotation_session"
    )


# ---------------------------------------------------------------------------
# Evaluation tables
# ---------------------------------------------------------------------------

class ImageSetEvaluation(Base):
    """Set-level classification (usability + low quality flag)."""

    __tablename__ = "image_set_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    annotation_session_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), ForeignKey("annotation_sessions.annotation_session_uuid"), nullable=False, unique=True
    )
    image_set_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), ForeignKey("image_sets.uuid"), nullable=False
    )
    image_set_usability: Mapped[ImageSetUsability] = mapped_column(
        Enum(ImageSetUsability), nullable=False
    )
    ischemic_low_quality: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    annotation_session: Mapped["AnnotationSession"] = relationship(
        "AnnotationSession", back_populates="image_set_evaluation"
    )


class ImageEvaluation(Base):
    """Per-slice ASPECTS scoring (only written when IschemicAssessable + !low_quality)."""

    __tablename__ = "image_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    annotation_session_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), ForeignKey("annotation_sessions.annotation_session_uuid"), nullable=False
    )
    image_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), ForeignKey("images.uuid"), nullable=False
    )
    region: Mapped[Region] = mapped_column(
        Enum(Region), default=Region.None_, nullable=False
    )

    # Bilateral ASPECTS zone scores
    c_left_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    c_right_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    ic_left_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    ic_right_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    l_left_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    l_right_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    i_left_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    i_right_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    m1_left_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    m1_right_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    m2_left_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    m2_right_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    m3_left_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    m3_right_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    m4_left_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    m4_right_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    m5_left_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    m5_right_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    m6_left_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    m6_right_score: Mapped[RegionScore] = mapped_column(Enum(RegionScore), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    annotation_session: Mapped["AnnotationSession"] = relationship(
        "AnnotationSession", back_populates="image_evaluations"
    )

    __table_args__ = (
        UniqueConstraint(
            "annotation_session_uuid", "image_uuid", name="uq_annot_sess_image"
        ),
    )


# ---------------------------------------------------------------------------
# Admin tables
# ---------------------------------------------------------------------------

class DoctorDatasetAssignment(Base):
    """Admin delegates exactly one active dataset to a doctor at a time."""

    __tablename__ = "doctor_dataset_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doctor_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), ForeignKey("doctors.uuid"), nullable=False
    )
    dataset_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), ForeignKey("datasets.dataset_uuid"), nullable=False
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    doctor: Mapped["Doctors"] = relationship("Doctors", back_populates="assignments")
    dataset: Mapped["DataSet"] = relationship("DataSet", back_populates="assignments")


class AdminAuditLog(Base):
    """Immutable append-only log of all admin mutations."""

    __tablename__ = "admin_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_uuid: Mapped[uuid_lib.UUID] = mapped_column(
        GUID(), ForeignKey("doctors.uuid"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_table: Mapped[str] = mapped_column(String(128), nullable=False)
    target_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("CURRENT_TIMESTAMP"),
    )
