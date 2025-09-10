# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
# /medfabric/db/database.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.orm import scoped_session


class Base(DeclarativeBase):
    pass


# Syntax: postgresql+psycopg://username:password@host:port/dbname

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# URL_OBJECT = URL.create(
#    "postgresql+psycopg",
#    username=os.getenv("POSTGRES_USER"),
#    password=os.getenv("POSTGRES_PASSWORD"),
#    host=os.getenv("POSTGRES_HOST"),
#    port=int(os.getenv("POSTGRES_PORT", "5432")),
#    database=os.getenv("POSTGRES_DB"),
# )

URL_OBJECT = URL.create(
    "postgresql+psycopg",
    username="ibmehust",
    password="ibmehust2025",
    host="db",
    port=5432,
    database="medfabric",
)

engine = create_engine(URL_OBJECT, echo=True)  # echo=True logs SQL

session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Session = scoped_session(session_factory)


def get_db():
    db = Session()  # scoped_session creates or reuses current Session
    try:
        yield db  # give the session to FastAPI route handler
        db.commit()  # if no exception, commit transaction
    except:
        db.rollback()  # if any exception in the route, rollback transaction
        raise  # re-raise so FastAPI still sees the error
    finally:
        Session.remove()  # cleanup: close & discard this Session
