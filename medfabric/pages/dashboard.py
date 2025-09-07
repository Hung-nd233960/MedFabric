from typing import Tuple, Callable, Dict, List
import uuid as uuid_lib
from enum import Enum
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from medfabric.api.errors import EmptyDatasetError
from medfabric.api.image_set_input import get_all_image_sets, exist_any_image_set
from medfabric.api.get_evaluated_sets import get_doctor_image_sets
from medfabric.pages.dashboard_helper.dashboard_config import (
    config_self,
    config_chosen,
)
from medfabric.pages.core.utils import reset
from medfabric.pages.core.pages import BasePage
from medfabric.pages.core.queue_manager import Event
from medfabric.pages.core.enum_key_manager import Key
from medfabric.pages.core.enum_key_manager import UIElementType


@st.cache_data
def get_image_sets_with_evaluation_status(
    _db_session: Session, doctor_uuid: uuid_lib.UUID
) -> Tuple[pd.DataFrame, int, int, float]:
    """
    Retrieve a DataFrame containing image sets along with their evaluation status by a specific doctor.

    This function fetches all image sets from the database,
    determines which of them have been evaluated by the specified doctor,
    and constructs a DataFrame with relevant details.
    Additionally, it calculates the total number of image sets, the number of evaluated image sets, and the percentage of evaluated image sets.

    Args:
        doctor_uuid (uuid_lib.UUID): The unique identifier of the doctor.

    Returns:
        Tuple[pd.DataFrame, int, int, float]: A tuple containing:
            - A pandas DataFrame with columns:
                - scan_id (str): The unique identifier of the image set.
                - patient_id (str): The unique identifier of the patient.
                - num_images (int): The number of images in the image set.
                - evaluated (bool): Whether the image set has been evaluated by the doctor.
                - edit (bool): Placeholder column, currently set to False.
            - The number of evaluated image sets (int).
            - The total number of image sets (int).
            - The percentage of evaluated image sets (float), rounded to two decimal places.


    """
    # Step 1: Get image_set_ids this doctor has evaluated
    evaluated_ids = get_doctor_image_sets(_db_session, doctor_uuid)
    # Step 2: Get all image sets
    all_image_sets = get_all_image_sets(_db_session)
    if all_image_sets is None:
        raise EmptyDatasetError("No image sets found in the database.")
    # Step 3: Build DataFrame with evaluation status
    df = pd.DataFrame(
        [
            {
                "index": imgset.index,
                "uuid": imgset.uuid,
                "scan_id": imgset.image_set_id,
                "patient_id": imgset.patient_id,
                "num_images": imgset.num_images,
                "evaluated": imgset.uuid in evaluated_ids,
                "edit": False,
            }
            for imgset in all_image_sets
        ]
    )
    total_count = len(df)
    evluated_count = len(evaluated_ids)
    percent = round(evluated_count / total_count, 2) if total_count else 0.0
    return df, evluated_count, total_count, percent


class DashboardPageEventType(Enum):
    DATA_CHANGED = "CHANGED"
    SUBMIT = "SUBMIT"
    LOGOUT = "LOGOUT"


class DashboardPage(BasePage[DashboardPageEventType]):
    EventType = DashboardPageEventType  # bind the enum

    def __init__(
        self,
        doctor_id: uuid_lib.UUID,
        login_session: uuid_lib.UUID,
        data_frame: pd.DataFrame,
        evaluated_count: int,
        total_count: int,
        progress: float,
        db_session: Session,
    ):
        super().__init__()
        self.doctor_id = doctor_id
        self.login_session = login_session
        self.db_session = db_session
        self.data_frame = data_frame
        self.evaluated_count = evaluated_count
        self.total_count = total_count
        self.progress = progress
        self.selected_df = pd.DataFrame()
        self.edited_df = pd.DataFrame()
        self.setup_dispatch_table()

    def setup_dispatch_table(self) -> None:
        self.dispatch_table: Dict[DashboardPageEventType, Callable] = {
            self.EventType.DATA_CHANGED: self.handle_changed,
            self.EventType.SUBMIT: self.handle_submit,
            self.EventType.LOGOUT: self.handle_logout,
        }

    def handle_changed(self, event: Event) -> None:
        status = st.session_state.get(str(event.payload))
        edited_rows: List[int] = []
        if status is None:
            return
        edited_rows_dict = status["edited_rows"]
        for row, value_change in edited_rows_dict.items():
            if value_change["edit"]:
                edited_rows.append(row)
        self.selected_df = self.data_frame.loc[edited_rows]

    # --- Handlers ---
    def handle_submit(self, event: Event) -> None:
        st.session_state.selected_scans = self.selected_df["uuid"].tolist()
        st.switch_page("pages/label.py")

    def handle_logout(self, event: Event) -> None:
        reset()

    # --- UI ---
    def render(self) -> None:
        self.listen_events()
        st.title("Dashboard")
        st.progress(
            value=self.progress,
            text=(
                f"Patients Labeled: {self.evaluated_count} / {self.total_count} "
                f"({self.progress * 100:.2f}%)"
            ),
        )
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Choose scans to evaluate")
            st.data_editor(
                data=self.data_frame,
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
                key=str(
                    self.key_manager.make(
                        UIElementType.DATA_EDITOR, self.EventType.DATA_CHANGED
                    )
                ),
                on_change=self.raise_event,
                args=(
                    self.EventType.DATA_CHANGED,
                    self.key_manager.make(
                        UIElementType.DATA_EDITOR, self.EventType.DATA_CHANGED
                    ),
                ),
            )
        with col2:
            if not self.selected_df.empty:
                st.subheader("Selected Scans for Evaluation")
                st.dataframe(
                    self.selected_df.drop(columns=["edit"]),
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
                st.write(
                    f"You have chosen {len(self.selected_df)} scans for evaluation."
                )
                st.button(
                    "Evaluate Selected Scans",
                    on_click=self.raise_event,
                    args=(self.EventType.SUBMIT,),
                )
            else:
                st.subheader("No Scans Selected")
                st.write(
                    "Please select scans to evaluate by checking the 'Evaluate' box."
                )

            st.button(
                "Logout", on_click=self.raise_event, args=(self.EventType.LOGOUT,)
            )
            # Retrieve necessary session state variables


st.set_page_config(
    page_title="Dashboard",
    page_icon=":bar_chart:",
    layout="wide",
)
doctor_uuid = st.session_state.get("user")
doctor_session = st.session_state.get("user_session")
db_session = st.session_state.get("db_session")
if doctor_uuid is None:
    st.error("You must be logged in to view this information.")
    st.stop()
elif doctor_session is None:
    st.error("User session not found. Please log in again.")
    st.stop()
elif "db_session" not in st.session_state or db_session is None:
    st.error("Database session not found. Please restart the application.")
    st.stop()
elif not exist_any_image_set(db_session):
    st.error("Error retrieving image sets. Please contact the maintainer.")
    st.stop()


if "dashboard_page" not in st.session_state:
    df, evaluated_count, total_count, progress = get_image_sets_with_evaluation_status(
        db_session, doctor_uuid
    )
    st.session_state.dashboard_page = DashboardPage(
        doctor_id=doctor_uuid,
        login_session=doctor_session.session_id,
        data_frame=df,
        evaluated_count=evaluated_count,
        total_count=total_count,
        progress=progress,
        db_session=db_session,
    )
st.session_state.dashboard_page.render()
