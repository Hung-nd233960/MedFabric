from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from medfabric.db.models import Base, ImageSet, Image
import uuid

# 1. Make a fresh in-memory database
engine = create_engine("sqlite:///:memory:", echo=False, future=True)
Base.metadata.create_all(engine)

# 2. Open a session
with Session(engine) as session:
    # 3. Create an ImageSet
    iset = ImageSet(uuid=uuid.uuid4(), image_set_name="test", num_images=2)
    session.add(iset)
    session.commit()

    # 4. Create images attached to that ImageSet
    img1 = Image(
        uuid=uuid.uuid4(), image_name="slice1", image_set_uuid=iset.uuid, slice_index=0
    )
    img2 = Image(
        uuid=uuid.uuid4(), image_name="slice2", image_set_uuid=iset.uuid, slice_index=1
    )
    session.add_all([img1, img2])
    session.commit()

    # 5. Query back and test relationships
    loaded_set = session.query(ImageSet).first()
    if loaded_set:
        print("ImageSet.images:", [img.image_name for img in loaded_set.images])

    loaded_image = session.query(Image).first()
    if loaded_image:
        print("Image.image_set:", loaded_image.image_set.image_set_name)
