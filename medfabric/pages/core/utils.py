from typing import List
import streamlit as st


def reset():
    st.cache_data.clear()
    st.session_state.clear()
    st.switch_page("pages/login.py")


def clear_session_state(states_keys: List[str]):
    for key in states_keys:
        if key in st.session_state:
            del st.session_state[key]
