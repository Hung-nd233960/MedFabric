import streamlit as st


def reset():
    st.cache_data.clear()
    st.session_state.clear()
    st.switch_page("pages/login.py")
