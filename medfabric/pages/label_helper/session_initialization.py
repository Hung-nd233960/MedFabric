# pylint: disable: missing-class-docstring, missing-module-docstring, missing-function-docstring
#  medfabric/pages/label/label_session_initialization.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict
import uuid as uuid_lib
from sqlalchemy.orm import Session as db_Session
import numpy as np
import pandas as pd
from medfabric.db.models import (
    Region,
)
from medfabric.api.image_set_input import get_image_set
from medfabric.api.image_input import get_all_images_in_set, get_image_by_uuid
from medfabric.pages.label_helper.image_helper import load_dicom_image
from medfabric.pages.label_helper.image_session_status import (
    initialize_slice_df,
)


@dataclass
class ImageEvaluationSession:
    image_uuid: uuid_lib.UUID
    image_id: str
    image_path: Path
    slice_index: int
    image_matrix: np.ndarray
    region: Region = Region.None_
    basal_score_central_left: Optional[int] = None
    basal_score_central_right: Optional[int] = None
    basal_score_cortex_left: Optional[int] = None
    basal_score_cortex_right: Optional[int] = None
    corona_score_left: Optional[int] = None
    corona_score_right: Optional[int] = None
    notes: Optional[str] = None
    image_metadata: Optional[Dict[str, str]] = None
    dirty: bool = False  # Indicates if the evaluation has been modified


@dataclass
class ImageSetEvaluationSession:
    set_index: int
    uuid: uuid_lib.UUID
    image_set_id: str
    patient_id: Optional[str]
    num_images: int
    folder_path: Path
    images_sessions: List[ImageEvaluationSession]
    notes: Optional[str] = None
    low_quality: bool = False
    irrelevant_data: bool = False
    #   conflicted: bool
    current_index: int = 0
    slice_status_df: pd.DataFrame = field(default_factory=initialize_slice_df)
    patient_information: Optional[pd.DataFrame] = None
    dirty: bool = False  # Indicates if the evaluation has been modified
    render_score_box_mode: bool = True

    @property
    def current_image_session(self) -> ImageEvaluationSession:
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
    images_in_set: List[uuid_lib.UUID] = get_all_images_in_set(
        db_session, image_set.uuid
    )
    image_sessions: List[ImageEvaluationSession] = []
    for img in images_in_set:
        if img is None:
            raise ValueError(f"Image in set {image_set.image_set_id} not found.")
        img_base = initialize_image_evaluation(
            db_session=db_session,
            image_uuid=img,
            parent_path=Path(image_set.folder_path),
        )
        image_sessions.append(img_base)
    return ImageSetEvaluationSession(
        set_index=image_set.index,
        uuid=image_set.uuid,
        image_set_id=image_set.image_set_id,
        patient_id=image_set.patient_id,
        num_images=image_set.num_images,
        folder_path=Path(image_set.folder_path),
        images_sessions=image_sessions,
        # conflicted=image_set.conflicted,
        current_index=0,
        patient_information=None,  # patient_diagnosis_to_df(patient),
    )


def initialize_image_evaluation(
    db_session: db_Session, image_uuid: uuid_lib.UUID, parent_path: Path
) -> ImageEvaluationSession:
    """
    Retrieve a specific image evaluation made by a doctor.

    Args:
        db_session: SQLAlchemy session object.
        image_uuid: UUID of the image to retrieve.
        parent_path: Base path where the image files are stored.

    Returns:
        ImageEvaluation object
    """
    image = get_image_by_uuid(db_session, image_uuid)
    if image is None:
        raise ValueError(f"Image with UUID {image_uuid} not found.")
    image_matrix = load_dicom_image(parent_path / Path(image.image_id))[0]

    return ImageEvaluationSession(
        image_uuid=image.uuid,
        image_id=image.image_id,
        image_path=parent_path / image.image_id,
        slice_index=image.slice_index,
        image_matrix=image_matrix,
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
