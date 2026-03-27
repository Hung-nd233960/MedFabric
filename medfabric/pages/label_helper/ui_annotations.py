"""Image annotation and labeling UI components.

This module provides functions for rendering image annotation controls, including
region selection, basal ganglia scoring, corona radiata scoring, and set-level labeling.
"""

import streamlit as st
from medfabric.db.orm_model import Region
from medfabric.pages.label_helper.state_management import (
    EventType,
    raise_flag,
)
from medfabric.pages.label_helper.dispatcher import (
    image_set_usability_translation_dict,
)
from medfabric.pages.label_helper.ui_helpers import render_text


def render_image_region_selection(key: str) -> None:
    """Render a segmented control for region selection.

    Args:
        key: Streamlit key for the pills control.
    """
    options = [
        "BasalGanglia",
        "CoronaRadiata",
    ]
    st.pills(
        "Region",
        options=options,
        key=key,
        default=None,
        format_func=render_text,
        on_change=raise_flag,
        args=(
            st.session_state.label_flag,
            EventType.REGION_SELECTED,
            key,
        ),
    )


def render_image_basal_score_selection(
    key_basal_c_left: str,
    key_basal_c_right: str,
    key_basal_ic_left: str,
    key_basal_ic_right: str,
    key_basal_l_left: str,
    key_basal_l_right: str,
    key_basal_i_left: str,
    key_basal_i_right: str,
    key_basal_m1_left: str,
    key_basal_m1_right: str,
    key_basal_m2_left: str,
    key_basal_m2_right: str,
    key_basal_m3_left: str,
    key_basal_m3_right: str,
) -> None:
    """Render segmented score inputs for basal ganglia regions.

    Provides separate score selectors for left and right sides, covering C, IC, L, I, M1, M2, and M3 regions.

    Args:
        key_basal_c_left: Key for left C score.
        key_basal_c_right: Key for right C score.
        key_basal_ic_left: Key for left IC score.
        key_basal_ic_right: Key for right IC score.
        key_basal_l_left: Key for left L score.
        key_basal_l_right: Key for right L score.
        key_basal_i_left: Key for left I score.
        key_basal_i_right: Key for right I score.
        key_basal_m1_left: Key for left M1 score.
        key_basal_m1_right: Key for right M1 score.
        key_basal_m2_left: Key for left M2 score.
        key_basal_m2_right: Key for right M2 score.
        key_basal_m3_left: Key for left M3 score.
        key_basal_m3_right: Key for right M3 score.
    """
    options = ["Not Visible", "0 Score", "1 Score"]
    col1, col2 = st.columns(2)
    with col1:
        st.write("Left:")
        st.pills(
            "C Score",
            options=options,
            key=key_basal_c_left,
            default=None,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.BASAL_C_LEFT_SCORE_CHANGED,
                key_basal_c_left,
            ),
        )
        st.pills(
            "IC Score",
            options=options,
            default=None,
            key=key_basal_ic_left,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.BASAL_IC_LEFT_SCORE_CHANGED,
                key_basal_ic_left,
            ),
        )
        st.pills(
            "L Score",
            options=options,
            default=None,
            key=key_basal_l_left,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.BASAL_L_LEFT_SCORE_CHANGED,
                key_basal_l_left,
            ),
        )
        st.pills(
            "I Score",
            options=options,
            default=None,
            key=key_basal_i_left,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.BASAL_I_LEFT_SCORE_CHANGED,
                key_basal_i_left,
            ),
        )
        st.pills(
            "M1 Score",
            options=options,
            default=None,
            key=key_basal_m1_left,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.BASAL_M1_LEFT_SCORE_CHANGED,
                key_basal_m1_left,
            ),
        )
        st.pills(
            "M2 Score",
            options=options,
            default=None,
            key=key_basal_m2_left,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.BASAL_M2_LEFT_SCORE_CHANGED,
                key_basal_m2_left,
            ),
        )
        st.pills(
            "M3 Score",
            options=options,
            default=None,
            key=key_basal_m3_left,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.BASAL_M3_LEFT_SCORE_CHANGED,
                key_basal_m3_left,
            ),
        )
    with col2:
        st.write("Right:")
        st.pills(
            "C Score",
            options=options,
            key=key_basal_c_right,
            default=None,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.BASAL_C_RIGHT_SCORE_CHANGED,
                key_basal_c_right,
            ),
        )
        st.pills(
            "IC Score",
            options=options,
            default=None,
            key=key_basal_ic_right,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.BASAL_IC_RIGHT_SCORE_CHANGED,
                key_basal_ic_right,
            ),
        )
        st.pills(
            "L Score",
            options=options,
            default=None,
            key=key_basal_l_right,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.BASAL_L_RIGHT_SCORE_CHANGED,
                key_basal_l_right,
            ),
        )
        st.pills(
            "I Score",
            options=options,
            default=None,
            key=key_basal_i_right,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.BASAL_I_RIGHT_SCORE_CHANGED,
                key_basal_i_right,
            ),
        )
        st.pills(
            "M1 Score",
            options=options,
            default=None,
            key=key_basal_m1_right,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.BASAL_M1_RIGHT_SCORE_CHANGED,
                key_basal_m1_right,
            ),
        )
        st.pills(
            "M2 Score",
            options=options,
            default=None,
            key=key_basal_m2_right,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.BASAL_M2_RIGHT_SCORE_CHANGED,
                key_basal_m2_right,
            ),
        )
        st.pills(
            "M3 Score",
            options=options,
            default=None,
            key=key_basal_m3_right,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.BASAL_M3_RIGHT_SCORE_CHANGED,
                key_basal_m3_right,
            ),
        )


def render_image_corona_score_selection(
    key_corona_m4_left: str,
    key_corona_m4_right: str,
    key_corona_m5_left: str,
    key_corona_m5_right: str,
    key_corona_m6_left: str,
    key_corona_m6_right: str,
) -> None:
    """Render segmented score inputs for corona radiata regions.

    Provides separate score selectors for left and right sides, covering M4, M5, and M6 regions.

    Args:
        key_corona_m4_left: Key for left M4 score.
        key_corona_m4_right: Key for right M4 score.
        key_corona_m5_left: Key for left M5 score.
        key_corona_m5_right: Key for right M5 score.
        key_corona_m6_left: Key for left M6 score.
        key_corona_m6_right: Key for right M6 score.
    """
    options = ["Not Visible", "0 Score", "1 Score"]
    col1, col2 = st.columns(2)
    with col1:
        st.write("Left:")
        st.pills(
            "M4 Score",
            options=options,
            key=key_corona_m4_left,
            default=None,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.CORONA_M4_LEFT_SCORE_CHANGED,
                key_corona_m4_left,
            ),
        )
        st.pills(
            "M5 Score",
            options=options,
            default=None,
            key=key_corona_m5_left,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.CORONA_M5_LEFT_SCORE_CHANGED,
                key_corona_m5_left,
            ),
        )
        st.pills(
            "M6 Score",
            options=options,
            default=None,
            key=key_corona_m6_left,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.CORONA_M6_LEFT_SCORE_CHANGED,
                key_corona_m6_left,
            ),
        )
    with col2:
        st.write("Right:")
        st.pills(
            "M4 Score",
            options=options,
            key=key_corona_m4_right,
            default=None,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.CORONA_M4_RIGHT_SCORE_CHANGED,
                key_corona_m4_right,
            ),
        )
        st.pills(
            "M5 Score",
            options=options,
            default=None,
            key=key_corona_m5_right,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.CORONA_M5_RIGHT_SCORE_CHANGED,
                key_corona_m5_right,
            ),
        )
        st.pills(
            "M6 Score",
            options=options,
            default=None,
            key=key_corona_m6_right,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.CORONA_M6_RIGHT_SCORE_CHANGED,
                key_corona_m6_right,
            ),
        )


def render_set_labeling_row(
    low_quality_key: str, irrelevant_key: str, low_quality_enabled: bool = True
) -> None:
    """Render set-level labeling controls for usability and quality marking.

    Args:
        low_quality_key: Key for the low quality checkbox.
        irrelevant_key: Key for the image set usability selectbox.
        low_quality_enabled: Whether the low quality checkbox is enabled (default True).
    """
    acol1, acol2 = st.columns(2)
    with acol1:
        st.selectbox(
            "Image Set Usability",
            options=image_set_usability_translation_dict.keys(),
            key=irrelevant_key,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.MARK_IRRELEVANT_CHANGED,
                irrelevant_key,
            ),
        )

    with acol2:
        if low_quality_enabled:
            st.checkbox(
                "Low Quality",
                key=low_quality_key,
                on_change=raise_flag,
                args=(
                    st.session_state.label_flag,
                    EventType.MARK_LOW_QUALITY_CHANGED,
                    low_quality_key,
                ),
            )


def render_labeling_column(
    region_segmented_key: str,
    key_basal_c_left: str,
    key_basal_c_right: str,
    key_basal_ic_left: str,
    key_basal_ic_right: str,
    key_basal_l_left: str,
    key_basal_l_right: str,
    key_basal_i_left: str,
    key_basal_i_right: str,
    key_basal_m1_left: str,
    key_basal_m1_right: str,
    key_basal_m2_left: str,
    key_basal_m2_right: str,
    key_basal_m3_left: str,
    key_basal_m3_right: str,
    key_corona_m4_left: str,
    key_corona_m4_right: str,
    key_corona_m5_left: str,
    key_corona_m5_right: str,
    key_corona_m6_left: str,
    key_corona_m6_right: str,
) -> None:
    """Render the labeling column with region selection and score inputs.

    Orchestrates the annotation interface, showing region selection and conditionally
    rendering basal ganglia or corona radiata scoring based on selected region.

    Args:
        region_segmented_key: Key for the region selection control.
        key_basal_c_left: Key for left C score.
        key_basal_c_right: Key for right C score.
        key_basal_ic_left: Key for left IC score.
        key_basal_ic_right: Key for right IC score.
        key_basal_l_left: Key for left L score.
        key_basal_l_right: Key for right L score.
        key_basal_i_left: Key for left I score.
        key_basal_i_right: Key for right I score.
        key_basal_m1_left: Key for left M1 score.
        key_basal_m1_right: Key for right M1 score.
        key_basal_m2_left: Key for left M2 score.
        key_basal_m2_right: Key for right M2 score.
        key_basal_m3_left: Key for left M3 score.
        key_basal_m3_right: Key for right M3 score.
        key_corona_m4_left: Key for left M4 score.
        key_corona_m4_right: Key for right M4 score.
        key_corona_m5_left: Key for left M5 score.
        key_corona_m5_right: Key for right M5 score.
        key_corona_m6_left: Key for left M6 score.
        key_corona_m6_right: Key for right M6 score.
    """
    app_state = st.session_state.app_state
    with st.expander("Image Annotation", expanded=True):
        if not app_state.current_session.render_score_box_mode:
            st.warning(
                "Score inputs are disabled due to the image being marked as low quality or irrelevant."
            )
        else:
            render_image_region_selection(key=region_segmented_key)
            if app_state.current_session.current_image_session.region == Region.None_:
                st.info("None region selected, no scores to display.")
            else:
                current_region = app_state.current_session.current_image_session.region
                if current_region == Region.BasalGanglia:
                    render_image_basal_score_selection(
                        key_basal_c_left=key_basal_c_left,
                        key_basal_c_right=key_basal_c_right,
                        key_basal_ic_left=key_basal_ic_left,
                        key_basal_ic_right=key_basal_ic_right,
                        key_basal_l_left=key_basal_l_left,
                        key_basal_l_right=key_basal_l_right,
                        key_basal_i_left=key_basal_i_left,
                        key_basal_i_right=key_basal_i_right,
                        key_basal_m1_left=key_basal_m1_left,
                        key_basal_m1_right=key_basal_m1_right,
                        key_basal_m2_left=key_basal_m2_left,
                        key_basal_m2_right=key_basal_m2_right,
                        key_basal_m3_left=key_basal_m3_left,
                        key_basal_m3_right=key_basal_m3_right,
                    )
                elif current_region == Region.CoronaRadiata:
                    render_image_corona_score_selection(
                        key_corona_m4_left=key_corona_m4_left,
                        key_corona_m4_right=key_corona_m4_right,
                        key_corona_m5_left=key_corona_m5_left,
                        key_corona_m5_right=key_corona_m5_right,
                        key_corona_m6_left=key_corona_m6_left,
                        key_corona_m6_right=key_corona_m6_right,
                    )
