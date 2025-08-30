import uuid as uuid_lib
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from medfabric.db.models import ImageSet
from medfabric.api.errors import ImageSetNotFoundError, DatabaseError


def update_image_set_folder_path(
    session: Session,
    image_set_uuid: uuid_lib.UUID,
    folder_path: str,
) -> ImageSet:
    """
    Update (or override) the folder_path of an ImageSet by UUID.

    Args:
        session (Session): SQLAlchemy session.
        image_set_uuid (UUID): UUID of the ImageSet.
        folder_path (str): New folder path to set.

    Returns:
        ImageSet: The updated ImageSet object.

    Raises:
        ImageSetNotFoundError: If no ImageSet with the given UUID exists.
        DatabaseError: If the database operation fails.
    """
    try:
        image_set = session.query(ImageSet).filter_by(uuid=image_set_uuid).first()
        if not image_set:
            raise ImageSetNotFoundError(
                f"No ImageSet with UUID {image_set_uuid} found."
            )

        image_set.folder_path = folder_path  # overwrite regardless of old value
        session.commit()
        session.refresh(image_set)  # refresh so updated values are loaded
        return image_set

    except SQLAlchemyError as exc:
        session.rollback()
        raise DatabaseError(f"Failed to update folder_path: {exc}") from exc
