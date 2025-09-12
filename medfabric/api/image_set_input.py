# medfabric/api/image_set_input.py
"""Module for handling image set input operations in the MedFabric API."""

from typing import Optional, List
import uuid as uuid_lib
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError
from medfabric.db.orm_model import ImageSet
from medfabric.db.pydantic_model import ImageSetRead, ImageSetCreate, ImageRead
from medfabric.api.errors import (
    PatientNotFoundError,
    DatabaseError,
    InvalidImageSetError,
)


from medfabric.api.patients import (
    check_patient_exists_by_uuid,
    check_patient_exists_by_id,
    get_patient_by_id_and_dataset_uuid,
    get_patient_by_uuid,
)
from medfabric.api.utils.normalize_folder_path import normalize_folder_path


def add_image_set(
    session: Session,
    image_set_name: str,
    num_images: int,
    dataset_uuid: uuid_lib.UUID,
    patient_uuid: uuid_lib.UUID,
    folder_path: str,
    image_set_uuid: Optional[uuid_lib.UUID] = None,
    description: Optional[str] = None,
) -> ImageSet:
    """
    Add a new image set to the database.
    Args:
        session (Session): SQLAlchemy session.
        image_set_name (str): Unique identifier for the image set.
        dataset_uuid (uuid.UUID): UUID of the data set the image set belongs to.
        image_set_uuid (uuid.UUID, optional): UUID for the image set.
        patient_uuid (uuid.UUID): ID of the patient associated with the image set.
        num_images (int): Number of images in the set.
        folder_path (str, optional): Path to the folder containing the images.
        description (str, optional): Description of the image set.
    Returns:
        ImageSet: The created image set record.
    """
    try:
        image_set_validator = ImageSetCreate(
            uuid=image_set_uuid,
            dataset_uuid=dataset_uuid,
            image_set_name=image_set_name,
            num_images=num_images,
            folder_path=folder_path,
            patient_uuid=patient_uuid,
            description=description,
        )
        image_set_uuid_ = image_set_validator.uuid
        image_set_name_ = image_set_validator.image_set_name
        folder_path_ = normalize_folder_path(image_set_validator.folder_path)
        dataset_uuid_ = image_set_validator.dataset_uuid
        num_images_ = image_set_validator.num_images
        patient_uuid_ = image_set_validator.patient_uuid
        description_ = image_set_validator.description

    except InvalidImageSetError as exc:
        raise InvalidImageSetError(f"Invalid image set data: {exc}") from exc

    except ValidationError as exc:
        raise InvalidImageSetError(f"Invalid image set data: {exc}") from exc
    if patient_uuid_ is not None:
        if not check_patient_exists_by_uuid(session, patient_uuid_, dataset_uuid_):
            raise PatientNotFoundError(f"Patient with ID '{patient_uuid_}' not found.")

    if not description_:
        description_ = None

    image_set = ImageSet(
        uuid=image_set_uuid_,
        dataset_uuid=dataset_uuid_,
        image_set_name=image_set_name_,
        patient_uuid=patient_uuid_,
        num_images=num_images_,
        folder_path=folder_path_,
        description=description_,
    )
    try:
        session.add(image_set)
        session.commit()
        return image_set
    except SQLAlchemyError as exc:
        session.rollback()
        raise DatabaseError(f"Failed to add image set: {exc}") from exc


def get_image_set(session: Session, uuid: uuid_lib.UUID) -> Optional[ImageSetRead]:
    """
    Retrieve an image set by its UUID.

    Args:
        session (Session): SQLAlchemy DB session
        uuid (uuid.UUID): UUID of the image set to retrieve

    Returns:
        ImageSet if found, None otherwise
    """
    image_set_orm = session.get(ImageSet, uuid)
    if image_set_orm:
        image_reads = [ImageRead.model_validate(img) for img in image_set_orm.images]

        patient = get_patient_by_uuid(session, image_set_orm.patient_uuid)
        if patient is None:
            raise PatientNotFoundError(
                f"Patient with UUID '{image_set_orm.patient_uuid}' not found."
            )
        else:
            image_set = ImageSetRead(
                uuid=image_set_orm.uuid,
                dataset_uuid=image_set_orm.dataset_uuid,
                image_set_name=image_set_orm.image_set_name,
                patient_uuid=image_set_orm.patient_uuid,
                num_images=image_set_orm.num_images,
                folder_path=image_set_orm.folder_path,
                conflicted=image_set_orm.conflicted,
                description=image_set_orm.description,
                index=image_set_orm.index,
                images=image_reads,
                patient=patient,
            )
            return image_set
    return None


def get_image_set_by_name_and_patient_and_data_set(
    session: Session, image_set_name: str, patient_id: str, data_set_uuid: uuid_lib.UUID
) -> Optional[uuid_lib.UUID]:
    """
    Retrieve an image set by its ID and optional patient ID.

    Args:
        session (Session): SQLAlchemy DB session
        image_set_name (str): ID of the image set to retrieve
        patient_id (str, optional): ID of the patient associated with the image set
        data_set_uuid (uuid.UUID): UUID of the data set the image set belongs to

    Returns:
        uuid.UUID if found, None otherwise
    """
    if check_patient_exists_by_id(session, patient_id, data_set_uuid):
        patient = get_patient_by_id_and_dataset_uuid(session, patient_id, data_set_uuid)
        if patient is None:
            raise PatientNotFoundError(f"Patient with ID '{patient_id}' not found.")
        patient_uuid = patient.patient_uuid
    else:
        raise PatientNotFoundError(f"Patient with ID '{patient_id}' not found.")
    query = session.query(ImageSet).filter_by(
        image_set_name=image_set_name, dataset_uuid=data_set_uuid
    )
    if patient_uuid is not None:
        query = query.filter_by(patient_uuid=patient_uuid)
    image_set = query.first()
    return image_set.uuid if image_set else None


def get_all_image_sets_in_a_data_set(
    session: Session, data_set_uuid: uuid_lib.UUID
) -> List[ImageSetRead]:
    """
    Retrieve all image sets from the database.

    Args:
        session (Session): SQLAlchemy DB session
        data_set_uuid (uuid.UUID): UUID of the data set to filter image sets

    Returns:
        List of all ImageSetRead records
    """

    image_sets = session.query(ImageSet).filter_by(dataset_uuid=data_set_uuid).all()

    set_read_list = [
        s for s in (get_image_set(session, x.uuid) for x in image_sets) if s is not None
    ]

    if len(set_read_list) != len(image_sets):
        raise DatabaseError("Data integrity error: Some image sets could not be read.")
    return set_read_list


def check_image_set_exists(session: Session, image_set_uuid: uuid_lib.UUID) -> bool:
    """
    Check if an image set with the given UUID exists.

    Args:
        session (Session): SQLAlchemy DB session
        image_set_uuid (uuid.UUID): UUID of the image set to check

    Returns:
        True if exists, False otherwise
    """
    return session.query(ImageSet).filter_by(uuid=image_set_uuid).first() is not None


def exist_any_image_set(session: Session) -> bool:
    """
    Check if there is at least one image set in the database.

    Args:
        session (Session): SQLAlchemy DB session

    Returns:
        True if at least one image set exists, False otherwise
    """
    return session.query(ImageSet).first() is not None
