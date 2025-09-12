import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from medfabric.db.orm_model import Base
from medfabric.db.orm_model import DataSet


@pytest.fixture
def db_session(postgresql):
    """Create a fresh DB and session per test."""
    # Build SQLAlchemy URL from the fixture info
    user = postgresql.info.user
    password = postgresql.info.password or ""
    host = postgresql.info.host
    port = postgresql.info.port
    dbname = postgresql.info.dbname

    url = f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}"
    engine = create_engine(url, echo=False)

    Base.metadata.create_all(engine)  # create tables

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def dataset_uuid(db_session):
    """Create and return a dataset UUID."""
    dataset = DataSet(name="test_dataset")
    db_session.add(dataset)
    db_session.commit()
    return dataset.dataset_uuid
