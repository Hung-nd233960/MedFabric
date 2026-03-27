import streamlit as st
from sqlalchemy.orm import sessionmaker
from medfabric.db.database import Base, return_engine


@st.cache_resource
def get_session_factory():
    engine = return_engine()
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session_factory_bare():
    engine = return_engine()
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
