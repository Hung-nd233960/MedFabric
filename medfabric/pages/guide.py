import streamlit as st
from pathlib import Path

file_path = Path("docs/UserGuide.md").read_text(encoding="utf-8")

st.set_page_config(
    page_title="Hướng dẫn sử dụng MedFabric",
    page_icon=":book:",
    layout="wide",
)
for line in file_path.split("\n"):
    if line.strip().startswith("![alt text]"):
        image_path = line[line.find("(") + 1 : line.find(")")]
        st.image(f"docs/{image_path}")
    else:
        st.markdown(line, unsafe_allow_html=False)
if st.button("Quay lại trang đăng nhập"):
    st.session_state.clear()
    st.cache_data.clear()
    st.switch_page("pages/login.py")
