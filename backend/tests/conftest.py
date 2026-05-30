"""Shared fixtures and helpers for all tests."""

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.db.models import (
    DataSet,
    DoctorRole,
    Doctors,
    Image,
    ImageFormat,
    ImageSet,
    Patient,
)

SQLITE_URL = "sqlite:///./test.db"


# ---------------------------------------------------------------------------
# Rate limit reset — slowapi counts hits per IP; wipe storage before each test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_rate_limits():
    from app.core.limiter import limiter
    if hasattr(limiter, "_storage"):
        limiter._storage.reset()
    yield


# ---------------------------------------------------------------------------
# Engine — session-scoped so table creation happens once per test run
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ---------------------------------------------------------------------------
# DB session — function-scoped; tables are wiped between tests
# ---------------------------------------------------------------------------

@pytest.fixture
def db(test_engine):
    Session = sessionmaker(bind=test_engine, autoflush=False)
    session = Session()
    yield session
    session.rollback()
    session.close()
    # Truncate every table in dependency order after each test
    with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


# ---------------------------------------------------------------------------
# TestClient — patches out PostgreSQL-specific startup code
# ---------------------------------------------------------------------------

@pytest.fixture
def client(db):
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db

    # _add_missing_columns() runs PG-only ALTER TABLE statements — skip for SQLite.
    # Patch app.main.engine so lifespan create_all hits the test DB, not PG.
    with patch("app.main.engine", db.bind), patch("app.main._add_missing_columns"):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# DB factory helpers
# ---------------------------------------------------------------------------

def make_doctor(
    db,
    username="doc1",
    password="pass123!",
    role=DoctorRole.Doctor,
    must_change_password=False,
    is_active=True,
):
    doctor = Doctors(
        uuid=uuid.uuid4(),
        username=username,
        role=role,
        password_hash=hash_password(password),
        is_active=is_active,
        is_test=(role == DoctorRole.Admin),
        must_change_password=must_change_password,
        must_set_name=False,
        registration_source="test",
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


def make_dataset_with_patient(db, dataset_name="TestDataset"):
    dataset = DataSet(dataset_uuid=uuid.uuid4(), name=dataset_name)
    db.add(dataset)
    db.flush()
    patient = Patient(patient_uuid=uuid.uuid4(), patient_id="P001", dataset_uuid=dataset.dataset_uuid)
    db.add(patient)
    db.commit()
    return dataset, patient


def make_image_set(db, dataset_uuid, patient_uuid, name="set1", n_images=4):
    img_set = ImageSet(
        uuid=uuid.uuid4(),
        dataset_uuid=dataset_uuid,
        patient_uuid=patient_uuid,
        image_set_name=name,
        image_format=ImageFormat.DICOM,
        num_images=n_images,
        folder_path=f"test/{name}",
        is_active=True,
    )
    db.add(img_set)
    db.flush()
    images = []
    for i in range(n_images):
        img = Image(
            uuid=uuid.uuid4(),
            image_name=f"slice_{i:03d}.dcm",
            image_set_uuid=img_set.uuid,
            slice_index=i,
        )
        db.add(img)
        images.append(img)
    db.commit()
    db.refresh(img_set)
    return img_set, images


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def api_login(client, username, password="pass123!"):
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# ASPECTS payload helpers
# ---------------------------------------------------------------------------

ZONES = ["c", "ic", "l", "i", "m1", "m2", "m3", "m4", "m5", "m6"]


def all_affected():
    """All 20 zone scores set to Affected."""
    return {f"{z}_{side}_score": "Affected" for z in ZONES for side in ("left", "right")}


def image_eval(image_uuid, region="BasalGanglia"):
    return {"image_uuid": str(image_uuid), "region": region, "notes": None, **all_affected()}


def submit_payload(session_uuid, images, usability="IschemicAssessable", low_quality=False):
    """Build a valid SubmitAnnotation payload.

    Assigns the first half of images to BasalGanglia and the second to
    CoronaRadiata to satisfy the ≥1-of-each-region validation rule.
    """
    mid = max(1, len(images) // 2)
    evals = (
        [image_eval(img.uuid, "BasalGanglia") for img in images[:mid]]
        + [image_eval(img.uuid, "CoronaRadiata") for img in images[mid:]]
    )
    return {
        "annotation_session_uuid": str(session_uuid),
        "usability": usability,
        "low_quality": low_quality,
        "notes": None,
        "image_evaluations": evals if usability == "IschemicAssessable" and not low_quality else [],
    }


# ---------------------------------------------------------------------------
# Common fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def admin(db):
    return make_doctor(db, username="admin", role=DoctorRole.Admin)


@pytest.fixture
def doctor(db):
    return make_doctor(db, username="doc1")


@pytest.fixture
def admin_token(client, admin):
    return api_login(client, "admin")


@pytest.fixture
def doctor_token(client, doctor):
    return api_login(client, "doc1")


@pytest.fixture
def image_set_data(db):
    dataset, patient = make_dataset_with_patient(db)
    return make_image_set(db, dataset.dataset_uuid, patient.patient_uuid)
