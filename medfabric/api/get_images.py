# medfabric/api/get_images.py
from typing import List
import uuid as uuid_lib
from sqlalchemy.orm import Session
from medfabric.db.orm_model import Image
from medfabric.db.pydantic_model import ImageRead


def get_images_by_set_id(
    session: Session, image_set_uuid: uuid_lib.UUID
) -> List[ImageRead]:
    """
    Retrieve all images associated with a given image set ID.

    Args:
        session (Session): SQLAlchemy DB session
        image_set_uuid (uuid_lib.UUID): ID of the image set

    Returns:
        List of ImageRead objects associated with the image set in ascending order of slice index
    """
    images = (
        session.query(Image)
        .filter_by(image_set_id=image_set_uuid)
        .order_by(Image.slice_index.asc())
        .all()
    )
    image_reads = [ImageRead.model_validate(img) for img in images]
    return image_reads
