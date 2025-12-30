import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from medfabric.db.database import Base, DATABASE_URL


@st.cache_resource
def get_session_factory():
    engine = create_engine(
        DATABASE_URL,
        echo=True,
        connect_args=(
            {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
        ),
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session_factory_bare():
    engine = create_engine(
        DATABASE_URL,
        echo=True,
        connect_args=(
            {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
        ),
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
