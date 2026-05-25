"""Pydantic v2 schemas for MedFabric 3.0 API request/response models."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.db.models import (
    DoctorRole,
    Gender,
    ImageFormat,
    ImageSetUsability,
    Region,
    RegionScore,
)


# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------

class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None

    @field_validator("username")
    @classmethod
    def username_length(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters.")
        return v

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    """Body-based refresh (alternative to cookie approach)."""
    refresh_token: str


# ---------------------------------------------------------------------------
# Doctor / user
# ---------------------------------------------------------------------------

class DoctorRead(_ORM):
    uuid: uuid.UUID
    username: str
    role: DoctorRole
    email: Optional[str] = None
    is_active: bool
    created_at: datetime


class DoctorCreate(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None
    role: DoctorRole = DoctorRole.Doctor


class DoctorUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role: Optional[DoctorRole] = None


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

class DataSetRead(_ORM):
    dataset_uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime


class DataSetCreate(BaseModel):
    name: str
    description: Optional[str] = None


class DataSetUpdate(BaseModel):
    description: Optional[str] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Patient
# ---------------------------------------------------------------------------

class PatientRead(_ORM):
    patient_uuid: uuid.UUID
    patient_id: str
    dataset_uuid: uuid.UUID
    category: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[Gender] = None


class PatientCreate(BaseModel):
    patient_id: str
    dataset_uuid: uuid.UUID
    category: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[Gender] = None


class PatientUpdate(BaseModel):
    category: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[Gender] = None


# ---------------------------------------------------------------------------
# ImageSet
# ---------------------------------------------------------------------------

class ImageSetRead(_ORM):
    uuid: uuid.UUID
    dataset_uuid: uuid.UUID
    patient_uuid: uuid.UUID
    image_set_name: str
    image_format: ImageFormat
    image_window_level: Optional[int] = None
    image_window_width: Optional[int] = None
    num_images: int
    folder_path: str
    description: Optional[str] = None
    icd_code: Optional[str] = None
    is_active: bool
    created_at: datetime


class ImageSetCreate(BaseModel):
    patient_uuid: uuid.UUID
    dataset_uuid: uuid.UUID
    image_set_name: str
    folder_path: str
    image_format: ImageFormat = ImageFormat.DICOM
    image_window_level: Optional[int] = None
    image_window_width: Optional[int] = None
    description: Optional[str] = None
    icd_code: Optional[str] = None


class ImageSetUpdate(BaseModel):
    image_window_level: Optional[int] = None
    image_window_width: Optional[int] = None
    description: Optional[str] = None
    icd_code: Optional[str] = None
    is_active: Optional[bool] = None


class ImageSetWithProgress(_ORM):
    """ImageSet row extended with evaluation progress for the dashboard."""
    uuid: uuid.UUID
    dataset_uuid: uuid.UUID
    patient_uuid: uuid.UUID
    image_set_name: str
    image_format: ImageFormat
    image_window_level: Optional[int] = None
    image_window_width: Optional[int] = None
    num_images: int
    description: Optional[str] = None
    icd_code: Optional[str] = None
    is_active: bool
    evaluated_by_me: bool
    total_evaluators: int


# ---------------------------------------------------------------------------
# Image (slice)
# ---------------------------------------------------------------------------

class ImageRead(_ORM):
    uuid: uuid.UUID
    image_name: str
    image_set_uuid: uuid.UUID
    slice_index: int


# ---------------------------------------------------------------------------
# Annotation session
# ---------------------------------------------------------------------------

class AnnotationSessionRead(_ORM):
    annotation_session_uuid: uuid.UUID
    doctor_uuid: uuid.UUID
    image_set_uuid: uuid.UUID
    login_session_uuid: uuid.UUID
    started_at: datetime
    submitted_at: Optional[datetime] = None


class AnnotationSessionCreate(BaseModel):
    image_set_uuid: uuid.UUID


# ---------------------------------------------------------------------------
# ImageSetEvaluation (set-level)
# ---------------------------------------------------------------------------

class ImageSetEvaluationRead(_ORM):
    id: int
    annotation_session_uuid: uuid.UUID
    image_set_uuid: uuid.UUID
    image_set_usability: ImageSetUsability
    ischemic_low_quality: bool
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# ImageEvaluation (per-slice) — zone scores
# ---------------------------------------------------------------------------

class ZoneScores(BaseModel):
    c_left_score: RegionScore
    c_right_score: RegionScore
    ic_left_score: RegionScore
    ic_right_score: RegionScore
    l_left_score: RegionScore
    l_right_score: RegionScore
    i_left_score: RegionScore
    i_right_score: RegionScore
    m1_left_score: RegionScore
    m1_right_score: RegionScore
    m2_left_score: RegionScore
    m2_right_score: RegionScore
    m3_left_score: RegionScore
    m3_right_score: RegionScore
    m4_left_score: RegionScore
    m4_right_score: RegionScore
    m5_left_score: RegionScore
    m5_right_score: RegionScore
    m6_left_score: RegionScore
    m6_right_score: RegionScore


class ImageEvaluationRead(_ORM, ZoneScores):
    id: int
    annotation_session_uuid: uuid.UUID
    image_uuid: uuid.UUID
    region: Region
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Submission payload (doctor submits entire image set at once)
# ---------------------------------------------------------------------------

class ImageEvaluationSubmit(ZoneScores):
    """One slice's data inside a full submission."""
    image_uuid: uuid.UUID
    region: Region
    notes: Optional[str] = None


class SubmitAnnotation(BaseModel):
    """Full payload from doctor when they click submit.

    annotation_session_uuid: the AnnotationSession opened at the start.
    usability / low_quality: set-level fields (always required).
    notes: optional set-level note.
    image_evaluations: only populated when usability=IschemicAssessable AND !low_quality.
    """
    annotation_session_uuid: uuid.UUID
    usability: ImageSetUsability
    low_quality: bool
    notes: Optional[str] = None
    image_evaluations: List[ImageEvaluationSubmit] = []


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

class DoctorDatasetAssignmentRead(_ORM):
    id: int
    doctor_uuid: uuid.UUID
    dataset_uuid: uuid.UUID
    assigned_at: datetime
    is_active: bool


class AssignDatasetRequest(BaseModel):
    doctor_uuid: uuid.UUID
    dataset_uuid: uuid.UUID


class AdminAuditLogRead(_ORM):
    id: int
    admin_uuid: uuid.UUID
    action: str
    target_table: str
    target_id: Optional[str] = None
    detail: Optional[str] = None
    timestamp: datetime


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardStats(BaseModel):
    assigned_dataset: Optional[DataSetRead]
    my_progress: int
    global_progress: int
    total_image_sets: int


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class ExportRequest(BaseModel):
    dataset_uuid: Optional[uuid.UUID] = None
    format: str = "xlsx"
