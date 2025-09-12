# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
# /medfabric/db/database.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy import URL
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Syntax: postgresql+psycopg://username:password@host:port/dbname

load_dotenv()

URL_OBJECT = URL.create(
    "postgresql+psycopg",
    username=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    host=os.getenv("POSTGRES_HOST"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
    database=os.getenv("POSTGRES_DB"),
)


def return_engine():
    return create_engine(URL_OBJECT, echo=True)
