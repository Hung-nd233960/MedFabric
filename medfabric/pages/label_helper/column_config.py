import streamlit as st

st.session_state.config_image_eval = {
    "slice_index": st.column_config.NumberColumn(
        label="Slice Index", disabled=True, pinned=True, help="Index of the slice"
    ),
    "image_uuid": st.column_config.TextColumn(
        label="Image UUID",
        disabled=True,
        pinned=True,
        help="Unique identifier for the image slice",
    ),
    "region": st.column_config.TextColumn(
        label="Region",
        disabled=True,
        help="Anatomical region associated with the slice",
    ),
    "status": st.column_config.TextColumn(
        label="Status", disabled=True, help="Labeling status of the slice"
    ),
}

st.session_state.config_set_eval = {
    "index": st.column_config.NumberColumn(
        label="Index", disabled=True, pinned=True, help="Index of the scan"
    ),
    "set_uuid": st.column_config.TextColumn(
        label="Set UUID",
        disabled=True,
        pinned=True,
        help="Unique identifier for the image set",
    ),
    "status": st.column_config.TextColumn(
        label="Status", disabled=True, help="Labeling status of the image set"
    ),
}
config_image_eval = st.session_state.config_image_eval
config_set_eval = st.session_state.config_set_eval
