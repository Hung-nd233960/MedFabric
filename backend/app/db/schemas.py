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
    full_name: str
    email: Optional[EmailStr] = None
    invitation_code: str = ""

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

    @field_validator("full_name")
    @classmethod
    def full_name_length(cls, v: str) -> str:
        if len(v.strip()) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        return v.strip()


class LoginRequest(BaseModel):
    username: str
    password: str


class DoctorMeResponse(BaseModel):
    uuid: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    is_test: bool
    created_at: Optional[str]


class UserPreferences(BaseModel):
    dark: bool = True
    tooltip_mode: str = "all"
    show_kbd_hints: bool = True
    dashboard_hint_open: bool = True
    nav_mode: str = "arrow"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool = False
    must_set_name: bool = False
    preferences: UserPreferences = UserPreferences()


class ChangePasswordRequest(BaseModel):
    new_password: str
    current_password: Optional[str] = None

    @field_validator("new_password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class SetupAccountRequest(BaseModel):
    full_name: Optional[str] = None
    new_password: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def full_name_min(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        return v.strip() if v else v

    @field_validator("new_password")
    @classmethod
    def password_min(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class RefreshRequest(BaseModel):
    """Body-based refresh (alternative to cookie approach)."""

    refresh_token: str


# ---------------------------------------------------------------------------
# Doctor / user
# ---------------------------------------------------------------------------


class DoctorRead(_ORM):
    uuid: uuid.UUID
    username: str
    full_name: Optional[str] = None
    role: DoctorRole
    email: Optional[str] = None
    is_active: bool
    is_test: bool = False
    must_change_password: bool = False
    must_set_name: bool = False
    registration_source: str = "admin_created"
    created_at: datetime
    last_seen: Optional[datetime] = None


class DoctorCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: DoctorRole = DoctorRole.Doctor
    is_test: bool = False


class DoctorUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_test: Optional[bool] = None
    role: Optional[DoctorRole] = None
    password: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class DataSetRead(_ORM):
    dataset_uuid: uuid.UUID
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    total_image_sets: int = 0
    global_progress: int = 0


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
    patient_id: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
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

    dataset_index: int
    uuid: uuid.UUID
    dataset_uuid: uuid.UUID
    patient_uuid: uuid.UUID
    patient_id: Optional[str] = None
    image_set_name: str
    image_format: ImageFormat
    image_window_level: Optional[int] = None
    image_window_width: Optional[int] = None
    num_images: int
    description: Optional[str] = None
    icd_code: Optional[str] = None
    is_active: bool
    evaluated_by_me: bool
    in_draft_by_me: bool
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
    draft_saved_at: Optional[datetime] = None


class AnnotationSessionCreate(BaseModel):
    image_set_uuid: uuid.UUID


class SaveDraft(BaseModel):
    """Partial annotation payload stored server-side; same shape as SubmitAnnotation."""

    annotation_session_uuid: uuid.UUID
    usability: Optional[ImageSetUsability] = None
    low_quality: bool = False
    notes: Optional[str] = None
    image_evaluations: List["ImageEvaluationSubmit"] = []


class DraftRead(BaseModel):
    annotation_session_uuid: uuid.UUID
    draft_saved_at: Optional[datetime] = None
    payload: Optional[dict] = None
    doctor_username: Optional[str] = None
    doctor_full_name: Optional[str] = None


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
    total_image_sets: int = 0
    doctor_progress: int = 0


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
# Drafts and History
# ---------------------------------------------------------------------------


class DraftItem(BaseModel):
    """One active draft entry for the Drafts tab."""

    annotation_session_uuid: uuid.UUID
    image_set_uuid: uuid.UUID
    image_set_name: str
    dataset_index: int
    patient_id: Optional[str] = None
    icd_code: Optional[str] = None
    num_images: int
    draft_saved_at: datetime
    draft_source: str  # "manual" | "auto"
    evaluated_by_me: bool
    # Admin-only — doctor who made the draft
    doctor_uuid: Optional[uuid.UUID] = None
    doctor_username: Optional[str] = None


class HistoryEvent(BaseModel):
    """One activity event for the History tab."""

    event_type: str  # "submitted" | "draft_saved" | "draft_deleted"
    timestamp: datetime
    annotation_session_uuid: uuid.UUID
    image_set_uuid: uuid.UUID
    image_set_name: str
    dataset_index: int
    icd_code: Optional[str] = None


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


class ExportRequest(BaseModel):
    dataset_uuid: Optional[uuid.UUID] = None
    format: str = "xlsx"


# ---------------------------------------------------------------------------
# Admin Submissions
# ---------------------------------------------------------------------------


class SubmissionRecord(BaseModel):
    annotation_session_uuid: uuid.UUID
    image_set_uuid: uuid.UUID
    image_set_name: str
    dataset_index: int
    icd_code: Optional[str] = None
    doctor_uuid: uuid.UUID
    doctor_username: str
    doctor_full_name: Optional[str] = None
    submitted_at: datetime
