"""Image display and control UI components.

This module provides functions for rendering image navigation controls and
DICOM windowing adjustments.
"""

import streamlit as st
from medfabric.pages.label_helper.state_management import (
    EventType,
    raise_flag,
)


def render_image_navigation_controls(
    next_img_key: str,
    prev_img_key: str,
    img_slider_key: str,
    num_images: int,
    current_index: int,
) -> None:
    """Render navigation controls for image selection.

    Provides buttons to navigate between images and a slider to jump to a specific image.

    Args:
        next_img_key: Key for the next image button.
        prev_img_key: Key for the previous image button.
        img_slider_key: Key for the jump to image slider.
        num_images: Total number of images in the set.
        current_index: Current image index (0-based).
    """
    with st.expander("Image Navigation", expanded=True):
        st.write(f"Image {current_index + 1} of {num_images}")
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            st.button(
                "Prev Image",
                key=prev_img_key,
                on_click=raise_flag,
                args=(
                    st.session_state.label_flag,
                    EventType.PREV_IMAGE,
                ),
            )
        with col2:
            st.button(
                "Next Image",
                key=next_img_key,
                on_click=raise_flag,
                args=(
                    st.session_state.label_flag,
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
                    st.session_state.label_flag,
                    EventType.JUMP_TO_IMAGE,
                    img_slider_key,
                ),
            )


def render_dicom_windowing_controls(
    window_width: int,
    window_level: int,
    window_width_key: str,
    window_level_key: str,
    reset_window_key: str,
):
    """Render DICOM windowing adjustment controls.

    Provides number inputs for windowing width and level, and a button to reset to defaults.

    Args:
        window_width: Current windowing width value.
        window_level: Current windowing level (center) value.
        window_width_key: Key for the width number input.
        window_level_key: Key for the level number input.
        reset_window_key: Key for the reset button.
    """
    with st.expander("DICOM Windowing", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.number_input(
                "Windowing Width",
                1,
                2000,
                value=window_width,
                key=window_width_key,
                on_change=raise_flag,
                args=(
                    st.session_state.label_flag,
                    EventType.WINDOWING_WIDTH_CHANGED,
                    window_width_key,
                ),
            )
        with col2:
            st.number_input(
                "Windowing Level",
                -1000,
                1000,
                value=window_level,
                key=window_level_key,
                on_change=raise_flag,
                args=(
                    st.session_state.label_flag,
                    EventType.WINDOWING_LEVEL_CHANGED,
                    window_level_key,
                ),
            )
        with col3:
            st.button(
                "Reset Windowing",
                key=reset_window_key,
                on_click=raise_flag,
                args=(
                    st.session_state.label_flag,
                    EventType.RESET_WINDOWING,
                ),
            )
