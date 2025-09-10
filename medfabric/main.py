# medfabric/main.py
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from medfabric.db.database import Base, URL_OBJECT


@st.cache_resource
def get_session_factory():
    engine = create_engine(URL_OBJECT, echo=True)
    Base.metadata.create_all(engine)  # optional: create tables if not exists
    return scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False))


SessionFactory = get_session_factory()

if "db_session" not in st.session_state:
    st.session_state.db_session = SessionFactory()

# 3. Navigation
pg = st.navigation(
    [
        st.Page("pages/login.py"),
        st.Page("pages/register.py"),
        st.Page("pages/dashboard.py"),
        st.Page("pages/label.py"),
    ]
)
pg.run()
