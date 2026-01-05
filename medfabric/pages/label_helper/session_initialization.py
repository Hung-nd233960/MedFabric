# pylint: disable: missing-class-docstring, missing-module-docstring, missing-function-docstring
# medfabric/pages/label/label_session_initialization.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict
import uuid as uuid_lib
from sqlalchemy.orm import Session as db_Session
import pandas as pd
from medfabric.db.orm_model import Region, ImageSetUsability, ImageFormat
from medfabric.api.config import PATHS
from medfabric.db.pydantic_model import ImageRead
from medfabric.api.image_set_input import get_image_set
from medfabric.pages.label_helper.image_session_status import (
    initialize_slice_df,
)


@dataclass
class ImageEvaluationSession:
    image_uuid: uuid_lib.UUID
    image_name: str
    image_path: Path
    slice_index: int
    region: Region = Region.None_
    basal_score_central_left: Optional[int] = None
    basal_score_central_right: Optional[int] = None
    basal_score_cortex_left: Optional[int] = None
    basal_score_cortex_right: Optional[int] = None
    corona_score_left: Optional[int] = None
    corona_score_right: Optional[int] = None
    notes: Optional[str] = None
    image_metadata: Optional[Dict[str, str]] = None


@dataclass
class ImageSetEvaluationSession:
    set_index: int
    uuid: uuid_lib.UUID
    image_set_name: str
    patient_id: Optional[str]
    num_images: int
    folder_path: Path
    images_sessions: List[ImageEvaluationSession]
    window_width_default: Optional[int] = None
    window_level_default: Optional[int] = None
    window_width_current: Optional[int] = window_width_default
    window_level_current: Optional[int] = window_level_default
    notes: Optional[str] = None
    low_quality: bool = False
    icd_code: Optional[str] = None
    description: Optional[str] = None
    image_set_usability: ImageSetUsability = ImageSetUsability.IschemicAssessable
    image_set_format: ImageFormat = ImageFormat.DICOM
    current_index: int = 0
    slice_status_df: pd.DataFrame = field(default_factory=initialize_slice_df)
    consecutive_slices: bool = False
    patient_information: Optional[pd.DataFrame] = None
    render_score_box_mode: bool = True
    render_valid_message: bool = False

    @property
    def current_image_session(self) -> ImageEvaluationSession:
        print(self.images_sessions)
        print(f"Current index: {self.current_index}")
        return self.images_sessions[self.current_index]


def initialize_evaluation_session(
    db_session: db_Session, image_set_uuids: List[uuid_lib.UUID]
) -> List[ImageSetEvaluationSession]:
    """
    Initialize evaluation sessions for a list of image set UUIDs.

    Args:
        db_session: SQLAlchemy session object.
        image_set_uuids: List of UUIDs for the image sets to initialize.

    Returns:
        List of ImageSetEvaluationSession objects.
    """
    sessions: List[ImageSetEvaluationSession] = []
    for img_set_uuid in image_set_uuids:
        session = initialize_image_set_evaluation(db_session, img_set_uuid)
        sessions.append(session)
    return sessions


def initialize_image_evaluation(
    image_read_object: ImageRead, parent_path: Path, dataset_path: Optional[Path] = None
) -> ImageEvaluationSession:
    """
    Retrieve a specific image evaluation made by a doctor.

    Args:
        image_read_object: ImageRead object representing the image to initialize.
        parent_path: Base path where the image files are stored.
        dataset_path: Optional base dataset path.

    Returns:
        ImageEvaluation object
    """
    image = image_read_object
    return ImageEvaluationSession(
        image_uuid=image.uuid,
        image_name=image.image_name,
        image_path=(
            dataset_path / parent_path / image.image_name
            if dataset_path
            else parent_path / image.image_name
        ),
        slice_index=image.slice_index,
    )


def initialize_image_set_evaluation(
    db_session: db_Session, image_set_uuid: uuid_lib.UUID
) -> ImageSetEvaluationSession:
    """
    Initialize an image set evaluation session.

    Args:
        db_session: SQLAlchemy session object.
        image_set_uuid: UUID of the image set to initialize.

    Returns:
        ImageSetEvaluationSession object containing details of the image set and its images.
    """
    image_set = get_image_set(db_session, image_set_uuid)
    if image_set is None:
        raise ValueError(f"Image set with UUID {image_set_uuid} not found.")
    ### Missing patient info handling
    # patient = get_patient(db_session, image_set.patient_id) if image_set.patient_id
    images_in_set: List[ImageRead] = image_set.images
    print(f"Found {len(images_in_set)} images in set {image_set.image_set_name}.")
    image_sessions: List[ImageEvaluationSession] = []
    for img in images_in_set:
        img_base = initialize_image_evaluation(
            image_read_object=img,
            parent_path=Path(image_set.folder_path),
            dataset_path=Path(PATHS.get("dataset", "/data_set")),
        )
        image_sessions.append(img_base)
    print(f"Initialized {len(image_sessions)} image sessions.")
    return ImageSetEvaluationSession(
        set_index=image_set.index,
        uuid=image_set.uuid,
        description=image_set.description if image_set.description else "",
        icd_code=image_set.icd_code if image_set.icd_code else "",
        image_set_name=image_set.image_set_name,
        image_set_format=image_set.image_format,
        window_width_default=image_set.image_window_width,
        window_level_default=image_set.image_window_level,
        patient_id=image_set.patient.patient_id if image_set.patient else None,
        num_images=image_set.num_images,
        folder_path=Path(image_set.folder_path),
        images_sessions=image_sessions,
        # conflicted=image_set.conflicted,
        current_index=0,
        patient_information=None,  # patient_diagnosis_to_df(patient),
    )


# def patient_diagnosis_to_df(patient_obj) -> pd.DataFrame:
#    if patient_obj is None:
#        return pd.DataFrame()
#
#    # List of all diagnostic attributes
#    attrs = [
#        "ICH",
#        "IPH",
#        "IVH",
#        "SDH",
#        "EDH",
#        "SAH",
#        "BleedLocation-Left",
#        "BleedLocation-Right",
#        "ChronicBleed",
#        "Fracture",
#        "CalvarialFracture",
#        "OtherFracture",
#        "MassEffect",
#        "MidlineShift",
#    ]
#
#    # Prepare a dictionary to hold row-wise data
#    data = {attr: [] for attr in attrs}
#
#    for attr in attrs:
#        for r in [1, 2, 3]:
#            value = getattr(patient_obj, f"R{r}:{attr}")
#            data[attr].append(value)
#
#    # Build DataFrame: index = attribute, columns = R1, R2, R3
#    df = pd.DataFrame(data).T
#    df.columns = ["R1", "R2", "R3"]
#    df.index.name = "Attribute"
#
#    return df.reset_index()
