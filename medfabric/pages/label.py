# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
# medfabric/pages/label.py
import streamlit as st
from medfabric.pages.label_helper.session_initialization import (
    initialize_evaluation_session,
)
from medfabric.pages.label_helper.label_page_object import LabelingPage
from medfabric.pages.label_helper.image_set_session_status import (
    SetStatus,
    add_row,
)

st.set_page_config(
    page_title="Labeling Phase",
    page_icon=":pencil2:",
    layout="wide",
)
app = st.session_state
doctor_uuid = app.get("user")
selected_scans = app.get("selected_scans")
user_session = app.get("user_session")
if not doctor_uuid:
    st.error("You must be logged in to access this page.")
    st.stop()
if user_session is None:
    st.error("Session information missing. Please log in again.")
    st.stop()
elif selected_scans is None:
    st.error("No scans selected for evaluation.")
    st.stop()
elif "db_session" not in app or app.db_session is None:
    st.error("Database session not found. Please restart the application.")
    st.stop()

if "labeling_page" not in app:
    app.labeling_page = LabelingPage(
        labeling_session=initialize_evaluation_session(
            db_session=app.db_session,
            image_set_uuids=selected_scans,
        ),
        doctor_id=doctor_uuid,
        login_session=user_session.session_id,
        db_session=app.db_session,
    )
    for sess in app.labeling_page.labeling_session:
        app.labeling_page.set_status_df = add_row(
            app.labeling_page.set_status_df, sess.uuid, SetStatus.INVALID
        )

app.labeling_page.render()
