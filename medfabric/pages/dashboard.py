from typing import Tuple
import uuid as uuid_lib
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from medfabric.api.errors import EmptyDatasetError
from medfabric.api.image_set_input import (
    get_all_image_sets_in_a_data_set,
    exist_any_image_set,
)
from medfabric.api.get_evaluated_sets import (
    get_dataset_evaluation_status,
    get_doctor_image_sets,
)
from medfabric.pages.dashboard_helper.dashboard_config import (
    config_self,
    config_chosen,
)
from medfabric.pages.dashboard_helper.state_management import (
    DashboardAppState,
    EventFlags,
    EnumKeyManager,
    EventType,
    UIElementType,
    raise_flag,
)
from medfabric.pages.dashboard_helper.dispatcher import flag_listener
from medfabric.api.data_sets import get_all_data_sets
from medfabric.db.engine import get_session_factory
from medfabric.pages.utils import sudden_close
from medfabric.api.patients import get_patient_by_uuid


def format_string(s: bool) -> str:
    if s:
        return "✅ Evaluated"
    return "❌ Not Evaluated"


def initial_setup() -> None:
    if "dashboard_flag" not in st.session_state:
        st.session_state.dashboard_flag = EventFlags()
    if "dashboard_key_mngr" not in st.session_state:
        st.session_state.dashboard_key_mngr = EnumKeyManager()


@st.cache_data
def get_image_sets_with_evaluation_status(
    _db_session: Session, doctor_uuid: uuid_lib.UUID, dataset_uuid: uuid_lib.UUID
) -> Tuple[pd.DataFrame, int, int, float]:
    """
    Retrieve a DataFrame containing image sets along with their evaluation status by a specific doctor.

    This function fetches all image sets from the database,
    determines which of them have been evaluated by the specified doctor,
    and constructs a DataFrame with relevant details.
    Additionally, it calculates the total number of image sets, the number of evaluated image sets, and the percentage of evaluated image sets.

    Args:
        doctor_uuid (uuid_lib.UUID): The unique identifier of the doctor.
        dataset_uuid (uuid_lib.UUID): The unique identifier of the dataset to filter image sets.
    Returns:
        Tuple[pd.DataFrame, int, int, float]: A tuple containing:
            - A pandas DataFrame with columns:
                - scan_id (str): The unique identifier of the image set.
                - patient_id (str): The unique identifier of the patient.
                - num_images (int): The number of images in the image set.
                - evaluated (str): Whether the image set has been evaluated by the doctor.
                - edit (bool): Placeholder column, currently set to False.
            - The number of evaluated image sets (int).
            - The total number of image sets (int).
            - The percentage of evaluated image sets (float), rounded to two decimal places.


    """
    # Step 1: Get image_set_ids this doctor has evaluated
    evaluated_ids = get_doctor_image_sets(_db_session, doctor_uuid)
    # Step 2: Get all image sets
    all_image_sets = get_all_image_sets_in_a_data_set(_db_session, dataset_uuid)
    if all_image_sets is None:
        raise EmptyDatasetError("No image sets found in the database.")
    # Step 3: Build DataFrame with evaluation status
    df = pd.DataFrame(
        [
            {
                "index": imgset.index,
                "uuid": imgset.uuid,
                "scan_id": imgset.image_set_name,
                "patient_id": (
                    patient.patient_id
                    if (
                        patient := get_patient_by_uuid(_db_session, imgset.patient_uuid)
                    )
                    else "N/A"
                ),
                "num_images": imgset.num_images,
                "evaluated": format_string(imgset.uuid in evaluated_ids),
                "edit": False,
            }
            for imgset in all_image_sets
        ]
    )
    total_count = len(df)
    evluated_count = len(evaluated_ids)
    percent = round(evluated_count / total_count, 2) if total_count else 0.0
    return df, evluated_count, total_count, percent


st.set_page_config(
    page_title="Dashboard",
    page_icon=":bar_chart:",
    layout="wide",
)

app = st.session_state
doctor_session = app.get("user_session")

if doctor_session is None:
    st.error("User session not found. Please log in again.")
    sudden_close()

if "dashboard_app_state" not in app:
    db_session = get_session_factory()()
    if not exist_any_image_set(db_session):
        st.error("Error retrieving image sets. Please contact the maintainer.")
        sudden_close(db_session)
    all_datasets = get_all_data_sets(db_session)
    current_dataset = all_datasets[0]
    (
        dataset_evaluated_count,
        dataset_total_count,
        dataset_progress,
    ) = get_dataset_evaluation_status(db_session, current_dataset.dataset_uuid)
    df, evaluated_count, total_count, progress = get_image_sets_with_evaluation_status(
        db_session, doctor_session.doctor_uuid, current_dataset.dataset_uuid
    )
    db_session.close()

    app.dashboard_app_state = DashboardAppState(
        doctor_uuid=doctor_session.doctor_uuid,
        all_sets_df=df,
        dataset_evaluated_count=dataset_evaluated_count,
        dataset_total_count=dataset_total_count,
        dataset_progress=dataset_progress,
        evaluated_count=evaluated_count,
        total_count=total_count,
        progress=progress,
    )

initial_setup()
flag_listener(app.dashboard_flag, app.dashboard_app_state)

dashboard_state = app.dashboard_app_state

st.progress(
    value=dashboard_state.dataset_progress,
    text=(
        f"Dataset Progress: {dashboard_state.dataset_evaluated_count} / "
        f"{dashboard_state.dataset_total_count} "
        f"({dashboard_state.dataset_progress * 100:.2f}%)"
    ),
)

st.progress(
    value=dashboard_state.progress,
    text=(
        f"Your Progress: {dashboard_state.evaluated_count} / {dashboard_state.total_count} "
        f"({dashboard_state.progress * 100:.2f}%)"
    ),
)

col1, col2 = st.columns(2)
editor_key = app.dashboard_key_mngr.make(
    UIElementType.DATA_EDITOR,
    EventType.EDIT_SELECTION,
)

with col1:
    st.subheader("Choose scans to evaluate")
    edited_data = st.data_editor(
        data=dashboard_state.all_sets_df,
        width="stretch",
        column_config=config_self,
        disabled=[
            "index",
            "scan_id",
            "patient_id",
            "num_images",
            "evaluated",
        ],
        column_order=[
            "index",
            "scan_id",
            "patient_id",
            "num_images",
            "evaluated",
            "edit",
        ],
        hide_index=True,
        key=editor_key,
    )
    # Persist edits so checkbox state survives reruns.

with col2:
    selected_scans = edited_data[edited_data["edit"]]
    dashboard_state.selected_scan_uuids = selected_scans["uuid"].tolist()

    if not selected_scans.empty:
        st.subheader("Selected Scans for Evaluation")
        st.dataframe(
            selected_scans.drop(columns=["edit"]),
            width="stretch",
            hide_index=True,
            column_config=config_chosen,
            column_order=[
                "index",
                "scan_id",
                "patient_id",
                "num_images",
                "evaluated",
            ],
            key="selected_image_sets",
        )
        st.write(f"You have chosen {len(selected_scans)} scans for evaluation.")

        st.button(
            "Evaluate Selected Scans",
            key=app.dashboard_key_mngr.make(
                UIElementType.BUTTON,
                EventType.EVALUATE_SELECTED_SCANS,
            ),
            on_click=raise_flag,
            args=(
                app.dashboard_flag,
                EventType.EVALUATE_SELECTED_SCANS,
            ),
        )
    else:
        st.subheader("No Scans Selected")
        st.write("Please select scans to evaluate by checking the 'Evaluate' box.")

st.button(
    "Logout",
    key=app.dashboard_key_mngr.make(UIElementType.BUTTON, EventType.LOGOUT),
    on_click=raise_flag,
    args=(
        app.dashboard_flag,
        EventType.LOGOUT,
    ),
)
