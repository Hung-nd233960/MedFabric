from typing import Optional, NoReturn
import streamlit as st
from sqlalchemy.orm import Session


def reset():
    st.cache_data.clear()
    st.session_state.clear()
    st.switch_page("pages/login.py")


def sudden_close(session: Optional[Session] = None) -> NoReturn:
    if session is not None:
        session.close()
    st.stop()
