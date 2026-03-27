# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
# medfabric/pages/label.py
"""Label page for image evaluation and annotation.

This module provides the main labeling interface for doctors to evaluate medical images.
It orchestrates the UI components for image display, region selection, and scoring.
"""

import streamlit as st
from medfabric.pages.label_helper.state_management import (
    EventType,
    UIElementType,
    EventFlags,
    EnumKeyManager,
    raise_flag,
)
from medfabric.pages.label_helper.session_initialization import (
    initialize_evaluation_session,
)

from medfabric.pages.label_helper.image_loader.jpg_processing import jpg_image
from medfabric.pages.label_helper.image_loader.dicom_processing import dicom_image
from medfabric.pages.label_helper.image_loader.image_helper import render_image
from medfabric.db.engine import get_session_factory
from medfabric.db.orm_model import ImageSetUsability, ImageFormat
from medfabric.api.config import (
    DEFAULT_WINDOW_LEVEL,
    DEFAULT_WINDOW_WIDTH,
)
from medfabric.pages.utils import sudden_close
from medfabric.pages.label_helper.state_management import LabelingAppState
from medfabric.pages.label_helper.dispatcher import (
    flag_listener,
)
from medfabric.pages.label_helper.image_set_session_status import (
    SetStatus,
    add_row,
    get_invalid_indices,
)
from medfabric.pages.label_helper.column_config import (
    config_image_eval,
    config_set_eval,
)

# Import UI components from separate modules
from medfabric.pages.label_helper.ui_buttons import (
    render_set_column,
    render_logout_button,
    render_back_to_dashboard_button,
)
from medfabric.pages.label_helper.ui_image_controls import (
    render_image_navigation_controls,
    render_dicom_windowing_controls,
)
from medfabric.pages.label_helper.ui_annotations import (
    render_set_labeling_row,
    render_labeling_column,
)


def _initialize_session_state():
    """Initialize event flags and key manager in Streamlit session state."""
    if "label_flag" not in st.session_state:
        st.session_state.label_flag = EventFlags()
    if "key_mngr" not in st.session_state:
        st.session_state.key_mngr = EnumKeyManager()


st.set_page_config(
    page_title="Labeling Phase",
    page_icon=":pencil2:",
    layout="wide",
)

app = st.session_state
selected_scans = app.get("selected_scans")
user_session = app.get("user_session")

if user_session is None:
    st.error("Session information missing. Please log in again.")
    sudden_close()
elif selected_scans is None:
    st.error("No scans selected for evaluation.")
    sudden_close()

doctor_uuid = user_session.doctor_uuid
if "app_state" not in app:
    db_session = get_session_factory()()
    print(f"Selected scans: {selected_scans}")
    app.app_state = LabelingAppState(
        labeling_session=initialize_evaluation_session(
            db_session=db_session,
            image_set_uuids=selected_scans,
        ),
        doctor_id=doctor_uuid,
        login_session=user_session.session_uuid,
    )
    db_session.close()
    for sess in app.app_state.labeling_session:
        app.app_state.set_status_df = add_row(
            app.app_state.set_status_df, sess.uuid, SetStatus.INVALID
        )
_initialize_session_state()
flag_listener(app.label_flag, app.app_state)


col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    img = None
    acol1, acol2, acol3 = st.columns(3)
    with acol1:
        render_back_to_dashboard_button(
            key=app.key_mngr.make(UIElementType.BUTTON, EventType.BACK_TO_DASHBOARD)
        )

    with acol2:
        render_logout_button(
            key=app.key_mngr.make(UIElementType.BUTTON, EventType.LOGOUT)
        )

    with acol3:
        # render_user_guide_button(
        #    key=app.key_mngr.make(UIElementType.BUTTON, EventType.USER_GUIDE)
        # )
        pass
    if app.app_state.current_session.image_set_format == ImageFormat.DICOM:
        img = dicom_image(
            app.app_state.current_session.current_image_session.image_path,
            width=(
                app.app_state.current_session.window_width_current
                if app.app_state.current_session.window_width_current is not None
                else DEFAULT_WINDOW_WIDTH
            ),
            center=(
                app.app_state.current_session.window_level_current
                if app.app_state.current_session.window_level_current is not None
                else DEFAULT_WINDOW_LEVEL
            ),
        )
    elif app.app_state.current_session.image_set_format == ImageFormat.JPEG:
        img = jpg_image(
            app.app_state.current_session.current_image_session.image_path,
        )
    else:
        st.error("Unsupported image format.")
    if img is not None:
        render_image(
            img,
            app.app_state.session_index,
            app.app_state.current_session.current_index,
            app.app_state.current_session.num_images,
        )
    render_image_navigation_controls(
        next_img_key=app.key_mngr.make(UIElementType.BUTTON, EventType.NEXT_IMAGE),
        prev_img_key=app.key_mngr.make(UIElementType.BUTTON, EventType.PREV_IMAGE),
        img_slider_key=app.key_mngr.make(
            UIElementType.SLIDER,
            EventType.JUMP_TO_IMAGE,
            app.app_state.current_session.uuid,
        ),
        num_images=app.app_state.current_session.num_images,
        current_index=app.app_state.current_session.current_index,
    )
with col2:
    with st.expander("Image Display", expanded=True):
        if app.app_state.current_session.image_set_format == ImageFormat.DICOM:
            render_dicom_windowing_controls(
                window_width=(
                    app.app_state.current_session.window_width_current
                    if app.app_state.current_session.window_width_current is not None
                    else DEFAULT_WINDOW_WIDTH
                ),
                window_level=(
                    app.app_state.current_session.window_level_current
                    if app.app_state.current_session.window_level_current is not None
                    else DEFAULT_WINDOW_LEVEL
                ),
                window_width_key=app.key_mngr.make(
                    UIElementType.NUMBER_INPUT,
                    EventType.WINDOWING_WIDTH_CHANGED,
                    app.app_state.current_session.uuid,
                ),
                window_level_key=app.key_mngr.make(
                    UIElementType.NUMBER_INPUT,
                    EventType.WINDOWING_LEVEL_CHANGED,
                    app.app_state.current_session.uuid,
                ),
                reset_window_key=app.key_mngr.make(
                    UIElementType.BUTTON,
                    EventType.RESET_WINDOWING,
                    app.app_state.current_session.uuid,
                ),
            )

    render_labeling_column(
        region_segmented_key=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.REGION_SELECTED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_basal_c_left=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.BASAL_C_LEFT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_basal_c_right=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.BASAL_C_RIGHT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_basal_ic_left=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.BASAL_IC_LEFT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_basal_ic_right=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.BASAL_IC_RIGHT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_basal_l_left=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.BASAL_L_LEFT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_basal_l_right=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.BASAL_L_RIGHT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_basal_i_left=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.BASAL_I_LEFT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_basal_i_right=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.BASAL_I_RIGHT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_basal_m1_left=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.BASAL_M1_LEFT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_basal_m1_right=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.BASAL_M1_RIGHT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_basal_m2_left=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.BASAL_M2_LEFT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_basal_m2_right=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.BASAL_M2_RIGHT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_basal_m3_left=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.BASAL_M3_LEFT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_basal_m3_right=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.BASAL_M3_RIGHT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_corona_m4_left=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.CORONA_M4_LEFT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_corona_m4_right=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.CORONA_M4_RIGHT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_corona_m5_left=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.CORONA_M5_LEFT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_corona_m5_right=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.CORONA_M5_RIGHT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_corona_m6_left=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.CORONA_M6_LEFT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
        key_corona_m6_right=app.key_mngr.make(
            UIElementType.SEGMENTED_CONTROL,
            EventType.CORONA_M6_RIGHT_SCORE_CHANGED,
            app.app_state.current_session.current_image_session.image_uuid,
        ),
    )

with col3:
    tab1, tab2 = st.tabs(["Set Information", "All Sets Status"])
    with tab1:
        with st.expander("Set Navigation and Metadata", expanded=True):
            st.write(
                f"Set {app.app_state.session_index + 1} of {len(app.app_state.labeling_session)}"
            )
            zcol1, zcol2 = st.columns([1, 1])
            with zcol1:
                if app.app_state.current_session.icd_code:
                    st.write(f"ICD Code: {app.app_state.current_session.icd_code}")
                st.write(f"Set Index: {app.app_state.current_session.set_index}")
            with zcol2:
                if app.app_state.current_session.description:
                    st.write(
                        f"Description: {app.app_state.current_session.description}"
                    )
            if len(app.app_state.labeling_session) > 1:
                render_set_column(
                    prev_key=app.key_mngr.make(
                        UIElementType.BUTTON, EventType.PREV_SET
                    ),
                    next_key=app.key_mngr.make(
                        UIElementType.BUTTON, EventType.NEXT_SET
                    ),
                    jump_to_key=app.key_mngr.make(
                        UIElementType.SLIDER,
                        EventType.JUMP_TO_SET,
                        app.app_state.current_session.uuid,
                    ),
                    current_index=app.app_state.session_index,
                    num_sets=len(app.app_state.labeling_session),
                )
        with st.expander("Current Image Set Status", expanded=True):
            if not app.app_state.current_session.render_score_box_mode:
                st.info("This image set is valid for submission.")
            else:
                if app.app_state.current_session.render_valid_message:
                    st.success("This image set is valid for submission.")
                else:
                    st.warning("This image set is not yet valid for submission.")
                if not app.app_state.current_session.consecutive_slices:
                    st.warning(
                        "The slices in this image set are not consecutive. Please ensure that all slices are consecutive before submission."
                    )
                st.dataframe(
                    app.app_state.current_session.slice_status_df,
                    width="stretch",
                    hide_index=True,
                    column_config=config_image_eval,
                    column_order=["slice_index", "region", "status"],
                )

    with tab2:
        with st.expander("Set Annotations", expanded=True):
            render_set_labeling_row(
                low_quality_key=app.key_mngr.make(
                    UIElementType.CHECKBOX,
                    EventType.MARK_LOW_QUALITY_CHANGED,
                    app.app_state.current_session.uuid,
                ),
                irrelevant_key=app.key_mngr.make(
                    UIElementType.SELECTBOX,
                    EventType.MARK_IRRELEVANT_CHANGED,
                    app.app_state.current_session.uuid,
                ),
                low_quality_enabled=app.app_state.current_session.image_set_usability
                == ImageSetUsability.IschemicAssessable,
            )
            st.text_area(
                "Notes",
                key=app.key_mngr.make(
                    UIElementType.TEXTAREA,
                    EventType.NOTES_CHANGED,
                    app.app_state.current_session.uuid,
                ),
                on_change=raise_flag,
                args=(
                    app.label_flag,
                    EventType.NOTES_CHANGED,
                    app.key_mngr.make(
                        UIElementType.TEXTAREA,
                        EventType.NOTES_CHANGED,
                        app.app_state.current_session.uuid,
                    ),
                ),
                max_chars=500,
            )

        with st.expander("All image set statuses", expanded=False):
            invalid_indices = get_invalid_indices(app.app_state.set_status_df)
            if invalid_indices:
                st.warning(
                    f"Some image sets are invalid. Invalid set indices: {list(invalid_indices)}"
                )
            else:
                st.success("All image sets are valid.")
                st.success("You can proceed to submit your evaluations.")
                st.button(
                    "Submit All Evaluations",
                    type="primary",
                    on_click=raise_flag,
                    args=(
                        app.label_flag,
                        EventType.SUBMIT,
                    ),
                )
            st.dataframe(
                app.app_state.set_status_df,
                width="stretch",
                hide_index=True,
                column_config=config_set_eval,
                column_order=["index", "status"],
            )
