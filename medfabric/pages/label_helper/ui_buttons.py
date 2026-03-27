"""Navigation and action button UI components.

This module provides functions for rendering navigation buttons and controls,
including logout, dashboard navigation, and set navigation controls.
"""

import streamlit as st
from medfabric.pages.label_helper.state_management import (
    EventType,
    raise_flag,
)


def render_set_column(
    prev_key: str, next_key: str, jump_to_key: str, current_index: int, num_sets: int
) -> None:
    """Render a column with set navigation controls.

    Provides buttons to navigate between image sets and a slider to jump to a specific set.

    Args:
        prev_key: Key for the previous set button.
        next_key: Key for the next set button.
        jump_to_key: Key for the jump to set slider.
        current_index: Current set index (0-based).
        num_sets: Total number of sets.
    """
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        st.button(
            "Previous Set",
            key=prev_key,
            on_click=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.PREV_SET,
            ),
        )
    with col2:
        st.button(
            "Next Set",
            key=next_key,
            on_click=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.NEXT_SET,
            ),
        )
    with col3:
        st.slider(
            "Jump to set",
            1,
            num_sets,
            current_index + 1,
            key=jump_to_key,
            on_change=raise_flag,
            args=(
                st.session_state.label_flag,
                EventType.JUMP_TO_SET,
                jump_to_key,
            ),
        )


def render_logout_button(key: str) -> None:
    """Render a logout button.

    Args:
        key: Streamlit key for the button.
    """
    st.button(
        "Logout",
        key=key,
        type="secondary",
        on_click=raise_flag,
        args=(
            st.session_state.label_flag,
            EventType.LOGOUT,
        ),
    )


def render_back_to_dashboard_button(key: str) -> None:
    """Render a back to dashboard button.

    Args:
        key: Streamlit key for the button.
    """
    st.button(
        "Back to Dashboard",
        key=key,
        type="secondary",
        on_click=raise_flag,
        args=(
            st.session_state.label_flag,
            EventType.BACK_TO_DASHBOARD,
        ),
    )


def render_user_guide_button(key: str) -> None:
    """Render a user guide button.

    Args:
        key: Streamlit key for the button.
    """
    st.button(
        "User Guide",
        key=key,
        type="secondary",
        on_click=raise_flag,
        args=(
            st.session_state.label_flag,
            EventType.USER_GUIDE,
        ),
    )
