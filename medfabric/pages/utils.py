import logging
from typing import Optional, NoReturn
import uuid as uuid_lib
import streamlit as st
from sqlalchemy.orm import Session
from medfabric.api.sessions import create_session, deactivate_session
from medfabric.api.errors import MedFabricError
from medfabric.db.engine import get_session_factory


logger = logging.getLogger(__name__)


def deactivate_current_login_session() -> None:
    """Deactivate the currently stored login session if present."""
    user_session = st.session_state.get("user_session")
    session_uuid = getattr(user_session, "session_uuid", None)
    if session_uuid is None:
        return

    db_session = get_session_factory()()
    try:
        deactivate_session(db_session, session_uuid)
    except MedFabricError as exc:  # Keep logout/navigation resilient.
        logger.warning("Failed to deactivate current login session %s", session_uuid)
        logger.debug("Deactivation error details: %s", exc)
    finally:
        db_session.close()


def reset():
    deactivate_current_login_session()
    st.cache_data.clear()
    st.session_state.clear()
    st.switch_page("pages/login.py")


def sudden_close(session: Optional[Session] = None) -> NoReturn:
    if session is not None:
        session.close()
    st.stop()


def reset_to_dashboard():

    st.cache_data.clear()
    st.session_state.clear()
    st.switch_page("pages/dashboard.py")


def reset_with_new_session(doctor_uuid: uuid_lib.UUID) -> NoReturn:
    """Reset everything but create a new session for the same doctor and return to dashboard.

    This is used after submit to keep the doctor logged in with a fresh session
    instead of fully logging out.
    """
    # Store doctor uuid before clearing session state
    doctor_id = doctor_uuid
    deactivate_current_login_session()

    # Clear all cached data and session state
    st.cache_data.clear()
    st.session_state.clear()

    # Create a new session for the same doctor
    db_session = get_session_factory()()
    try:
        new_session = create_session(db_session, doctor_id)
        st.session_state.user_session = new_session
    finally:
        db_session.close()

    # Switch to dashboard with fresh session
    st.switch_page("pages/dashboard.py")
