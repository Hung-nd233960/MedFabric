from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from medfabric.db.database import Base, URL_OBJECT


def get_session_factory_bare():
    engine = create_engine(URL_OBJECT, echo=True)
    Base.metadata.create_all(engine)  # optional: create tables if not exists
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
