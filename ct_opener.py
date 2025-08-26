from typing import Any, Dict, List, Tuple, Union
import os
import json
import numpy as np
import cv2
import pydicom
from pydicom.dataset import FileDataset
import streamlit as st


def main() -> None:
    uploaded_files = [
        "public_data/eda_public_data/data/CQ500-CT-9/CT Thin Plain/CT000001.dcm",
        "public_data/eda_public_data/data/CQ500-CT-9/CT Thin Plain/CT000002.dcm",
        "public_data/eda_public_data/data/CQ500-CT-9/CT Thin Plain/CT000003.dcm",
        "public_data/eda_public_data/data/CQ500-CT-9/CT Thin Plain/CT000004.dcm",
        "public_data/eda_public_data/data/CQ500-CT-9/CT Thin Plain/CT000005.dcm",
        "public_data/eda_public_data/data/CQ500-CT-9/CT Thin Plain/CT000006.dcm",
        "public_data/eda_public_data/data/CQ500-CT-9/CT Thin Plain/CT000007.dcm",
        "public_data/eda_public_data/data/CQ500-CT-9/CT Thin Plain/CT000008.dcm",
    ]
    if uploaded_files:
        images, dicoms = load_multi_dicom(uploaded_files)
        if not images:
            st.error("No valid DICOM images loaded.")
            return

        slice_idx: int = 0
        if len(images) > 1:
            slice_idx = st.slider("Slice", 0, len(images) - 1, 0)

        original_image: np.ndarray = images[slice_idx]
        current_dicom: FileDataset = dicoms[slice_idx][0]

        st.subheader("📄 Selected Metadata Viewer")
        metadata_fields: List[str] = [
            "PatientName",
            "PatientID",
            "StudyDate",
            "Modality",
            "SliceThickness",
            "PixelSpacing",
        ]
        selected_field: str = st.selectbox(
            "Choose metadata field to view", metadata_fields
        )
        field_value: Any = getattr(current_dicom, selected_field, "Not Found")
        st.write(f"**{selected_field}**: {field_value}")

        with st.expander("📁 Show full DICOM Metadata"):
            metadata_str: str = dicom_to_dict_str(current_dicom)
            st.code(metadata_str, language="json")

        st.subheader("🛠️ Brightness / Contrast / Filter Controls")
        col1, col2 = st.columns(2)
        with col1:
            brightness: int = st.slider("Brightness", -100, 100, 0)
        with col2:
            contrast: float = st.slider("Contrast", 0.1, 3.0, 1.0)

        filter_type: str = st.selectbox(
            "Filter", ["Original", "Gaussian Blur", "Sharpen", "Edge Detection"]
        )
        explanation: str = get_filter_explanation(filter_type)
        st.markdown(f"**Filter Explanation:** {explanation}")

        zoom_factor: float = st.slider("Zoom", 1.0, 5.0, 1.0, 0.1)

        processed: np.ndarray = apply_brightness_contrast(
            original_image, brightness, contrast
        )
        processed = apply_filter(processed, filter_type)
        processed = zoom_image(processed, zoom_factor)

        if filter_type == "Edge Detection":
            processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)

        st.image(
            processed,
            caption=f"Slice {slice_idx+1} | Filter: {filter_type} | Zoom: {zoom_factor}x",
            use_container_width=True,
            clamp=True,
        )


if __name__ == "__main__":
    main()
