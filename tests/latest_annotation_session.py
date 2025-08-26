import uuid as uuid_lib
from typing import List
import pytest
from sqlalchemy.orm import Session as db_Session
from medfabric.api.sessions import create_session
from medfabric.api.credentials import register_doctor
from medfabric.api.image_set_input import add_image_set
from medfabric.api.image_input import add_image
from medfabric.api.image_set_evaluation_input import add_evaluate_image_set
from medfabric.api.image_evaluation_input import add_evaluate_image
from medfabric.api.utils.latest_annotation_session import (
    get_last_evaluation,
    EvaluationResult,
)
from medfabric.db.models import (
    Doctors,
    Session,
    ImageSet,
    Image,
    Region,
)


@pytest.fixture
def doctor(db_session: db_Session) -> List[Doctors]:
    doc1 = register_doctor(db_session, "doc1", "password123")
    doc2 = register_doctor(db_session, "doc2", "password456")
    doc3 = register_doctor(db_session, "doc3", "password789")
    return [doc1, doc2, doc3]


@pytest.fixture
def sessions(db_session: db_Session, doctor: List[Doctors]) -> List[Session]:
    sess1 = create_session(db_session, doctor[0].uuid)
    sess2 = create_session(db_session, doctor[1].uuid)
    sess3 = create_session(db_session, doctor[2].uuid)
    return [sess1, sess2, sess3]


@pytest.fixture
def image_sets(db_session: db_Session) -> List[ImageSet]:
    set1 = add_image_set(db_session, "set1", 3)
    set2 = add_image_set(db_session, "set2", 2)
    set3 = add_image_set(db_session, "set3", 4)
    print(
        "Created image sets:", set1.image_set_id, set2.image_set_id, set3.image_set_id
    )
    return [set1, set2, set3]
