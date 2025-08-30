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
from medfabric.db.models import Region
from medfabric.api.config import BASAL_CENTRAL_MAX, BASAL_CORTEX_MAX, CORONA_MAX
from medfabric.pages.label_helper.state_management import LabelingAppState
from medfabric.pages.label_helper.dispatcher import flag_listener


def initial_setup():
    """Initialize event flags in Streamlit session state if not already present."""
    if "flag" not in st.session_state:
        st.session_state.flag = EventFlags()
    if "key_mngr" not in st.session_state:
        st.session_state.key_mngr = EnumKeyManager()


def render_set_column(prev_key: str, next_key: str) -> None:
    """Render a column with set navigation controls."""
    col1, col2 = st.columns([1, 1])
    with col1:
        st.button(
            "Previous Set",
            key=prev_key,
            on_click=raise_flag,
            args=(
                app.flag,
                EventType.PREV_SET,
            ),
        )
    with col2:
        st.button(
            "Next Set",
            key=next_key,
            on_click=raise_flag,
            args=(
                app.flag,
                EventType.NEXT_SET,
            ),
        )


def render_logout_button(key: str) -> None:
    """Render a logout button."""
    st.button(
        "Logout",
        key=key,
        type="secondary",
        on_click=raise_flag,
        args=(
            app.flag,
            EventType.LOGOUT,
        ),
    )


def render_image_region_selection(key: str) -> None:
    """Render a segmented control for region selection."""
    options = [
        "Basal Ganglia (Central)",
        "Basal Ganglia (Cortex)",
        "Corona Radiata",
    ]
    st.segmented_control(
        "Region",
        options=options,
        key=key,
        on_change=raise_flag,
        args=(
            app.flag,
            EventType.REGION_SELECTED,
            key,
        ),
    )


def render_image_navigation_controls(
    next_img_key: str,
    prev_img_key: str,
    img_slider_key: str,
    num_images: int,
    current_index: int,
    brightness: int,
    contrast: float,
    brightness_slider_key: str,
    contrast_slider_key: str,
    reset_key: str,
    filter_selectbox_key: str,
) -> None:
    """Render navigation controls for image selection."""
    with st.expander("Image Navigation and Adjustment Controls", expanded=True):
        st.write(f"Image {current_index + 1} of {num_images}")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            st.button(
                "Prev Image",
                key=prev_img_key,
                on_click=raise_flag,
                args=(
                    app.flag,
                    EventType.PREV_IMAGE,
                ),
            )
        with col2:
            st.button(
                "Next Image",
                key=next_img_key,
                on_click=raise_flag,
                args=(
                    app.flag,
                    EventType.NEXT_IMAGE,
                ),
            )
        with col3:
            st.slider(
                "Jump to image",
                1,
                num_images,
                current_index + 1,
                key=img_slider_key,
                on_change=raise_flag,
                args=(
                    app.flag,
                    EventType.JUMP_TO_IMAGE,
                    img_slider_key,
                ),
            )
        col1, col2 = st.columns(2)
        with col1:
            st.slider(
                "Brightness",
                -100,
                100,
                brightness,
                key=brightness_slider_key,
                on_change=raise_flag,
                args=(
                    app.flag,
                    EventType.BRIGHTNESS_CHANGED,
                    brightness_slider_key,
                ),
            )
            st.button(
                "Reset Adjustments",
                key=reset_key,
                on_click=raise_flag,
                args=(
                    app.flag,
                    EventType.RESET_ADJUSTMENTS,
                ),
            )
        with col2:
            st.slider(
                "Contrast",
                0.1,
                3.0,
                contrast,
                key=contrast_slider_key,
                on_change=raise_flag,
                args=(
                    app.flag,
                    EventType.CONTRAST_CHANGED,
                    contrast_slider_key,
                ),
            )
            st.selectbox(
                "Filter",
                ["In Development"],
                key=filter_selectbox_key,
                on_change=raise_flag,
                disabled=True,
                args=(
                    app.flag,
                    EventType.FILTER_CHANGED,
                    app.key_mngr.make(
                        UIElementType.SELECTBOX,
                        EventType.FILTER_CHANGED,
                    ),
                ),
            )


def render_set_labeling_row(low_quality_key: str, irrelevant_key: str):
    acol1, acol2 = st.columns(2)
    with acol1:
        st.checkbox(
            "Low Quality",
            key=low_quality_key,
            on_change=raise_flag,
            args=(app.flag, EventType.MARK_LOW_QUALITY, low_quality_key),
        )
    with acol2:
        st.checkbox(
            "Irrelevant Data",
            key=irrelevant_key,
            on_change=raise_flag,
            args=(app.flag, EventType.MARK_IRRELEVANT, irrelevant_key),
        )


def render_labeling_column(
    key_basal_cortex_left: str,
    key_basal_cortex_right: str,
    key_basal_central_left: str,
    key_basal_central_right: str,
    key_corona_left: str,
    key_corona_right: str,
) -> None:
    """Render the labeling column with region selection and score inputs."""
    with st.expander("Image Annotation", expanded=True):
        if app.app_state.score_box_render_mode is None:
            st.warning(
                "Score inputs are disabled due to the image being marked as low quality or irrelevant."
            )
        else:
            render_image_region_selection(
                key=app.key_mngr.make(
                    UIElementType.SEGMENTED_CONTROL,
                    EventType.REGION_SELECTED,
                    app.app_state.current_session.uuid,
                )
            )
            if app.app_state.score_box_render_mode == Region.None_:
                st.info("None region selected, no scores to display.")
            else:
                acol1, acol2 = st.columns([1, 1])
                with acol1:
                    if (
                        app.app_state.score_box_render_mode == Region.BasalCortex
                        or app.app_state.score_box_render_mode == Region.BasalCentral
                    ):
                        st.write("Left:")
                        st.number_input(
                            "Basal Cortex Score",
                            min_value=0,
                            max_value=BASAL_CORTEX_MAX,
                            step=1,
                            key=key_basal_cortex_left,
                            on_change=raise_flag,
                            args=(
                                app.flag,
                                EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED,
                                key_basal_cortex_left,
                            ),
                        )
                    if app.app_state.score_box_render_mode == Region.BasalCentral:
                        st.number_input(
                            "Basal Central Score",
                            min_value=0,
                            max_value=BASAL_CENTRAL_MAX,
                            step=1,
                            key=key_basal_central_left,
                            on_change=raise_flag,
                            args=(
                                app.flag,
                                EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED,
                                key_basal_central_left,
                            ),
                        )
                    if app.app_state.score_box_render_mode == Region.CoronaRadiata:
                        st.write("Left:")
                        st.number_input(
                            "Corona Radiata Score",
                            min_value=0,
                            max_value=CORONA_MAX,
                            step=1,
                            key=key_corona_left,
                            on_change=raise_flag,
                            args=(
                                app.flag,
                                EventType.CORONA_LEFT_SCORE_CHANGED,
                                key_corona_left,
                            ),
                        )
                with acol2:
                    if (
                        app.app_state.score_box_render_mode == Region.BasalCortex
                        or app.app_state.score_box_render_mode == Region.BasalCentral
                    ):
                        st.write("Right:")
                        st.number_input(
                            "Basal Cortex Score",
                            min_value=0,
                            max_value=BASAL_CORTEX_MAX,
                            step=1,
                            key=key_basal_cortex_right,
                            on_change=raise_flag,
                            args=(
                                app.flag,
                                EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED,
                                key_basal_cortex_right,
                            ),
                        )
                    if app.app_state.score_box_render_mode == Region.BasalCentral:
                        st.number_input(
                            "Basal Central Score",
                            min_value=0,
                            max_value=BASAL_CENTRAL_MAX,
                            step=1,
                            key=key_basal_central_right,
                            on_change=raise_flag,
                            args=(
                                app.flag,
                                EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED,
                                key_basal_central_right,
                            ),
                        )
                    if app.app_state.score_box_render_mode == Region.CoronaRadiata:
                        st.write("Right:")
                        st.number_input(
                            "Corona Radiata Score",
                            min_value=0,
                            max_value=CORONA_MAX,
                            step=1,
                            key=key_corona_right,
                            on_change=raise_flag,
                            args=(
                                app.flag,
                                EventType.CORONA_RIGHT_SCORE_CHANGED,
                                key_corona_right,
                            ),
                        )


st.set_page_config(
    page_title="Labeling Phase",
    page_icon=":pencil2:",
    layout="wide",
)

app = st.session_state
doctor_uuid = app.get("user")
selected_scans = app.get("selected_scans")
session_uuid = app.get("user_session")
if not doctor_uuid:
    st.error("You must be logged in to access this page.")
    st.stop()
if session_uuid is None:
    st.error("Session information missing. Please log in again.")
    st.stop()
elif selected_scans is None:
    st.error("No scans selected for evaluation.")
    st.stop()
elif "db_session" not in app or app.db_session is None:
    st.error("Database session not found. Please restart the application.")
    st.stop()

if "app_state" not in app:
    app.app_state = LabelingAppState(
        labeling_session=initialize_evaluation_session(
            db_session=app.db_session,
            image_set_uuids=selected_scans,
        ),
        doctor_id=doctor_uuid,
        login_session=session_uuid,
        db_session=app.db_session,
    )

initial_setup()
flag_listener(app.flag, app.app_state)


col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    render_logout_button(key=app.key_mngr.make(UIElementType.BUTTON, EventType.LOGOUT))
with col2:
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
        brightness_slider_key=app.key_mngr.make(
            UIElementType.SLIDER,
            EventType.BRIGHTNESS_CHANGED,
            app.app_state.current_session.uuid,
        ),
        contrast=app.app_state.contrast,
        brightness=app.app_state.brightness,
        contrast_slider_key=app.key_mngr.make(
            UIElementType.SLIDER,
            EventType.CONTRAST_CHANGED,
            app.app_state.current_session.uuid,
        ),
        reset_key=app.key_mngr.make(
            UIElementType.BUTTON,
            EventType.RESET_ADJUSTMENTS,
        ),
        filter_selectbox_key=app.key_mngr.make(
            UIElementType.SELECTBOX,
            EventType.FILTER_CHANGED,
        ),
    )

    render_labeling_column(
        key_basal_cortex_left=app.key_mngr.make(
            UIElementType.NUMBER_INPUT,
            EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED,
            app.app_state.current_session.uuid,
        ),
        key_basal_cortex_right=app.key_mngr.make(
            UIElementType.NUMBER_INPUT,
            EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED,
            app.app_state.current_session.uuid,
        ),
        key_basal_central_left=app.key_mngr.make(
            UIElementType.NUMBER_INPUT,
            EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED,
            app.app_state.current_session.uuid,
        ),
        key_basal_central_right=app.key_mngr.make(
            UIElementType.NUMBER_INPUT,
            EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED,
            app.app_state.current_session.uuid,
        ),
        key_corona_left=app.key_mngr.make(
            UIElementType.NUMBER_INPUT,
            EventType.CORONA_LEFT_SCORE_CHANGED,
            app.app_state.current_session.uuid,
        ),
        key_corona_right=app.key_mngr.make(
            UIElementType.NUMBER_INPUT,
            EventType.CORONA_RIGHT_SCORE_CHANGED,
            app.app_state.current_session.uuid,
        ),
    )

with col3:
    st.write(
        f"Set {app.app_state.session_index + 1} of {len(app.app_state.labeling_session)}"
    )
    render_set_column(
        prev_key=app.key_mngr.make(UIElementType.BUTTON, EventType.PREV_SET),
        next_key=app.key_mngr.make(UIElementType.BUTTON, EventType.NEXT_SET),
    )
    render_set_labeling_row(
        low_quality_key=app.key_mngr.make(
            UIElementType.CHECKBOX,
            EventType.MARK_LOW_QUALITY,
            app.app_state.current_session.uuid,
        ),
        irrelevant_key=app.key_mngr.make(
            UIElementType.CHECKBOX,
            EventType.MARK_IRRELEVANT,
            app.app_state.current_session.uuid,
        ),
    )
