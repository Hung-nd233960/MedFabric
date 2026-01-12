# Image Processing

## Overview

The image processing module handles loading and rendering medical images in DICOM and JPEG formats. It provides specialized functions for CT scan visualization with proper windowing controls.

---

## Module Structure

```
medfabric/pages/label_helper/image_loader/
├── __init__.py
├── dicom_processing.py    # DICOM-specific processing
├── jpg_processing.py      # JPEG/PNG processing
└── image_helper.py        # Common rendering utilities
```

---

## DICOM Processing

### Hounsfield Units

CT scans are stored in Hounsfield Units (HU), a standardized scale:

| Tissue | HU Range |
|--------|----------|
| Air | -1000 |
| Lung | -500 to -700 |
| Fat | -100 to -50 |
| Water | 0 |
| Soft tissue | +40 to +80 |
| Bone | +700 to +3000 |

### Core Functions

#### load_raw_dicom_image

Loads DICOM file and converts to Hounsfield Units.

```python
def load_raw_dicom_image(file_path: Path) -> Tuple[FileDataset, np.ndarray]:
    """
    Load DICOM and convert to HU.
    
    Args:
        file_path: Path to DICOM file
        
    Returns:
        Tuple of (DICOM dataset, HU array)
        
    Raises:
        InvalidDicomFileError: If file is not valid DICOM
    """
    try:
        dcm_obj = pydicom.dcmread(file_path)
    except InvalidDicomError as e:
        raise InvalidDicomFileError(f"Invalid DICOM file: {file_path}") from e

    img = dcm_obj.pixel_array.astype(np.int16)

    # Apply rescale transformation
    slope = getattr(dcm_obj, "RescaleSlope", 1)
    intercept = getattr(dcm_obj, "RescaleIntercept", 0)
    hu = img * slope + intercept
    
    return dcm_obj, hu
```

#### apply_window

Applies windowing to convert HU to displayable image.

```python
def apply_window(img: np.ndarray, center: float, width: float) -> Image.Image:
    """
    Apply CT windowing to HU image.
    
    Windowing formula:
        low = center - width/2
        high = center + width/2
        output = ((clipped - low) / (high - low)) * 255
    
    Args:
        img: Image in Hounsfield Units
        center: Window level (center HU value)
        width: Window width (range of HU values)
        
    Returns:
        PIL Image (8-bit grayscale)
    """
    low = center - width // 2
    high = center + width // 2
    windowed = np.clip(img, low, high)
    windowed = ((windowed - low) / (high - low) * 255).astype(np.uint8)
    return Image.fromarray(windowed)
```

### Windowing Visualization

```
                    Window Width = 80 HU
                ◄─────────────────────────►
                │                         │
    ────────────┼─────────────────────────┼────────────── HU Scale
              low                       high
                          ▲
                          │
                    Window Level = 40 HU
                    
    Output:
    ■■■■■■■■■▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░□□□□□□□□
    0 (black)           128 (gray)              255 (white)
    
    HU < low  → 0 (black)
    HU > high → 255 (white)
    HU in [low, high] → linear interpolation
```

### Common CT Window Presets

| Window Name | Width | Level | Use Case |
|-------------|-------|-------|----------|
| Brain | 80 | 40 | **Default for ischemic stroke** |
| Stroke | 40 | 40 | Acute ischemia detection |
| Bone | 2500 | 480 | Skull fractures |
| Subdural | 250 | 75 | Subdural hemorrhage |

#### dicom_image

High-level function used in label.py.

```python
def dicom_image(file_path: Path, center: float, width: float) -> Image.Image:
    """
    Load DICOM and apply windowing in one call.
    
    Args:
        file_path: Path to DICOM file
        center: Window level
        width: Window width
        
    Returns:
        Windowed PIL Image ready for display
    """
    _, hu = load_raw_dicom_image(file_path)
    windowed_image = apply_window(hu, center, width)
    return windowed_image
```

### DICOM Metadata Extraction

```python
def dicom_to_dict_str(dicom: FileDataset) -> Dict[str, str]:
    """Convert DICOM tags to dictionary."""
    dicom_dict: Dict[str, str] = {}
    for elem in dicom:
        if elem.VR != "SQ":  # Skip sequences
            tag_name = elem.keyword if elem.keyword else str(elem.tag)
            dicom_dict[tag_name] = str(elem.value)
    return dicom_dict


def extract_searchable_info(dicom: FileDataset) -> Dict[str, str]:
    """Extract key fields for search/display."""
    return {
        "PatientName": str(getattr(dicom, "PatientName", "")),
        "PatientID": str(getattr(dicom, "PatientID", "")),
        "StudyDate": str(getattr(dicom, "StudyDate", "")),
        "Modality": str(getattr(dicom, "Modality", "")),
        "SliceThickness": str(getattr(dicom, "SliceThickness", "")),
        "PixelSpacing": str(getattr(dicom, "PixelSpacing", "")),
    }
```

---

## JPEG Processing

For non-DICOM datasets (pre-converted or research sets).

```python
def load_jpg_image(file_path: Path) -> Image.Image:
    """
    Load JPG/PNG image.
    
    Args:
        file_path: Path to image file
        
    Returns:
        PIL Image in original mode
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If unsupported format
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

    return Image.open(file_path)


def jpg_image(file_path: Path) -> Image.Image:
    """Wrapper for Streamlit compatibility."""
    return load_jpg_image(file_path)
```

---

## Image Rendering

### render_image

Displays image in Streamlit with position caption.

```python
def render_image(
    image: Image.Image,
    current_set_index: int,
    current_image_index: int,
    num_images: int,
) -> None:
    """
    Render image with caption.
    
    Args:
        image: PIL Image to display
        current_set_index: 0-indexed set number
        current_image_index: 0-indexed slice number
        num_images: Total slices in set
    """
    st.image(
        image,
        caption=(
            f"Set {current_set_index + 1} | "
            f"Image {current_image_index + 1} of {num_images}"
        ),
        width="stretch",
        clamp=False,
    )
```

---

## Processing Pipeline

### DICOM Pipeline

```
┌─────────────┐     ┌──────────────────┐     ┌────────────────┐
│ DICOM File  │────▶│ load_raw_dicom   │────▶│ HU np.ndarray  │
│ (.dcm)      │     │ _image()         │     │ (int16)        │
└─────────────┘     └──────────────────┘     └───────┬────────┘
                                                     │
                                                     ▼
┌─────────────┐     ┌──────────────────┐     ┌────────────────┐
│ Streamlit   │◀────│ render_image()   │◀────│ apply_window() │
│ Display     │     │                  │     │ → PIL Image    │
└─────────────┘     └──────────────────┘     └────────────────┘
```

### JPEG Pipeline

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│ JPEG File   │────▶│ jpg_image()      │────▶│ Streamlit   │
│ (.jpg/.png) │     │ → PIL Image      │     │ Display     │
└─────────────┘     └──────────────────┘     └─────────────┘
```

---

## Usage in Label Page

```python
# In label.py main rendering section
if app.app_state.current_session.image_set_format == ImageFormat.DICOM:
    img = dicom_image(
        app.app_state.current_session.current_image_session.image_path,
        width=(
            app.app_state.current_session.window_width_current
            if app.app_state.current_session.window_width_current is not None
            else DEFAULT_WINDOW_WIDTH  # 80
        ),
        center=(
            app.app_state.current_session.window_level_current
            if app.app_state.current_session.window_level_current is not None
            else DEFAULT_WINDOW_LEVEL  # 40
        ),
    )
elif app.app_state.current_session.image_set_format == ImageFormat.JPEG:
    img = jpg_image(
        app.app_state.current_session.current_image_session.image_path,
    )

if img is not None:
    render_image(
        img,
        app.app_state.session_index,
        app.app_state.current_session.current_index,
        app.app_state.current_session.num_images,
    )
```

---

## Future Enhancements (Commented Code)

The codebase contains several planned but disabled features:

### Zoom

```python
# def zoom_image(image: np.ndarray, zoom_factor: float) -> np.ndarray:
#     """Crop and resize for zoom effect."""
#     h, w = image.shape
#     new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
#     top = (h - new_h) // 2
#     left = (w - new_w) // 2
#     cropped = image[top:top + new_h, left:left + new_w]
#     return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
```

### Filters

```python
# def apply_filter(image: np.ndarray, filter_type: str) -> np.ndarray:
#     """Apply edge detection, blur, or sharpening."""
#     if filter_type == "Gaussian Blur":
#         return cv2.GaussianBlur(image, (5, 5), 0)
#     elif filter_type == "Sharpen":
#         kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
#         return cv2.filter2D(image, -1, kernel)
#     elif filter_type == "Edge Detection":
#         return cv2.Canny(image, 100, 200)
#     return image
```

### Brightness/Contrast for JPEG

```python
# def apply_brightness_contrast_jpg(
#     image: Image.Image, brightness: int = 0, contrast: float = 1.0
# ) -> Image.Image:
#     """Enhance brightness and contrast for non-DICOM images."""
#     enhancer_contrast = ImageEnhance.Contrast(image)
#     img = enhancer_contrast.enhance(contrast)
#     enhancer_brightness = ImageEnhance.Brightness(img)
#     return enhancer_brightness.enhance(1 + brightness / 100.0)
```

---

## Error Handling

### InvalidDicomFileError

Custom exception for DICOM validation failures.

```python
class InvalidDicomFileError(Exception):
    """Raised when a file is not a valid DICOM."""
    pass
```

### Error Recovery Pattern

```python
# In label.py
try:
    if format == ImageFormat.DICOM:
        img = dicom_image(path, width, center)
    elif format == ImageFormat.JPEG:
        img = jpg_image(path)
    else:
        st.error("Unsupported image format.")
        img = None
except InvalidDicomFileError:
    st.error(f"Cannot load DICOM: {path}")
    img = None
except FileNotFoundError:
    st.error(f"Image not found: {path}")
    img = None
```
