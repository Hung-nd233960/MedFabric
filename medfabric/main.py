# medfabric/main.py
import sys
from pathlib import Path

import streamlit as st


# Ensure absolute imports like `from medfabric...` work in page scripts
# regardless of the directory used to launch Streamlit.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# 3. Navigation
pg = st.navigation(
    [
        st.Page("pages/login.py"),
        st.Page("pages/register.py"),
        st.Page("pages/dashboard.py"),
        st.Page("pages/label.py"),
        st.Page("pages/guide.py"),
    ]
)
pg.run()
