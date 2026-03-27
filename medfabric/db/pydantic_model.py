"""Pydantic models for data validation and serialization."""

# pylint: disable=missing-class-docstring, missing-function-docstring, missing-module-docstring
from datetime import datetime
from typing import Optional, List, Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

# NameEmail
from medfabric.db.orm_model import (
    Region,
    RegionScore,
    Gender,
    ImageSetUsability,
    ImageFormat,
)


# --- Base class for all schemas ---
class OrmBase(BaseModel):
    model_config = {"from_attributes": True}


# --- Datasets ---
class DataSetBase(OrmBase):
    dataset_uuid: UUID
    name: Annotated[str, StringConstraints(min_length=1)]
    description: Optional[str] = None


class DataSetCreate(OrmBase):
    name: Annotated[str, StringConstraints(min_length=1)]
    description: Optional[str] = None
    dataset_uuid: Optional[UUID] = None


class DataSetRead(DataSetBase):
    pass


# --- Patients ---
class PatientBase(OrmBase):
    patient_id: Annotated[str, StringConstraints(min_length=1)]
    dataset_uuid: UUID
    category: Optional[str] = None
    age: Annotated[int, Field(ge=0, le=130)] | None = None
    gender: Optional[Gender] = None


class PatientCreate(PatientBase):
    patient_uuid: Optional[UUID] = None


class PatientRead(PatientBase):
    patient_uuid: UUID


#    image_sets: List["ImageSetRead"] = []  # Forward reference


# --- Doctors ---


class DoctorBase(OrmBase):
    uuid: UUID
    username: Annotated[str, StringConstraints(min_length=3, strip_whitespace=True)]
    role: Optional[str] = None
    email: Optional[str] = None


class DoctorLogin(BaseModel):
    username: str
    password: str


class DoctorCreate(OrmBase):
    username: Annotated[str, StringConstraints(min_length=3, strip_whitespace=True)]
    role: Optional[str] = None
    email: Optional[str] = None
    password_hash: Annotated[str, StringConstraints(min_length=8)]


class DoctorRead(DoctorBase):
    pass


# --- Sessions ---
class SessionBase(OrmBase):
    session_uuid: UUID
    doctor_uuid: UUID
    login_time: datetime
    is_active: bool


class SessionCreate(OrmBase):
    doctor_uuid: UUID


class SessionGetter(OrmBase):
    session_uuid: UUID


class SessionRead(SessionBase):
    pass


# --- ImageSets ---
class ImageSetBase(OrmBase):
    uuid: UUID
    dataset_uuid: UUID
    image_set_name: Annotated[str, StringConstraints(min_length=1)]
    patient_uuid: UUID
    num_images: Annotated[int, Field(gt=0)]
    icd_code: Optional[str] = None
    folder_path: str
    conflicted: bool
    description: Optional[str] = None
    image_format: ImageFormat
    image_window_level: Optional[int] = None
    image_window_width: Optional[int] = None


class ImageSetCreate(OrmBase):
    dataset_uuid: UUID
    uuid: Optional[UUID] = None
    image_set_name: Annotated[str, StringConstraints(min_length=1)]
    icd_code: Optional[str] = None
    patient_uuid: UUID
    num_images: Annotated[int, Field(gt=0)]
    folder_path: str
    description: Optional[str] = None
    image_format: ImageFormat
    image_window_level: Optional[int] = None
    image_window_width: Optional[int] = None


class ImageSetRead(ImageSetBase):
    index: int
    images: List["ImageRead"] = []  # Forward reference
    patient: PatientRead  # Forward reference


# --- Images ---
class ImageBase(OrmBase):
    uuid: UUID
    image_name: Annotated[str, StringConstraints(min_length=1)]
    image_set_uuid: UUID
    slice_index: Annotated[int, Field(ge=0)]


class ImageCreate(OrmBase):
    uuid: Optional[UUID] = None
    image_name: Annotated[str, StringConstraints(min_length=1)]
    image_set_uuid: UUID
    slice_index: Annotated[int, Field(ge=0)]


class ImageRead(ImageBase):
    #    image_set: ImageSetRead  # Forward reference
    pass


# --- ImageSetEvaluations ---
class ImageSetEvaluationBase(OrmBase):
    doctor_uuid: UUID
    image_set_uuid: UUID
    session_uuid: UUID
    ischemic_low_quality: bool
    usability: ImageSetUsability


class ImageSetEvaluationCreate(ImageSetEvaluationBase):
    pass


class ImageSetEvaluationRead(ImageSetEvaluationBase):
    id: int


# --- ImageEvaluations ---
class ImageEvaluationBase(OrmBase):
    doctor_uuid: UUID
    image_uuid: UUID
    session_uuid: UUID
    region: Region

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

    notes: Optional[Annotated[str, StringConstraints(max_length=500)]] = None


class ImageEvaluationCreate(ImageEvaluationBase):
    pass


class ImageEvaluationRead(ImageEvaluationBase):
    id: int


PatientRead.model_rebuild()
ImageSetRead.model_rebuild()
ImageRead.model_rebuild()
