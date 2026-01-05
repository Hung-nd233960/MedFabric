from PIL import Image
import streamlit as st


def render_image(
    image: Image.Image,
    current_set_index: int,
    current_image_index: int,
    num_images: int,
) -> None:
    """
    Render an image to Streamlit with caption.
    Args:
        image: Image to render.
        current_set_index: Index of the current image set.
        current_image_index: Index of the current image in the set.
        num_images: Total number of images in the set.
    """
    st.image(
        image,
        caption=(
            f"Set {current_set_index + 1} | "
            f"Image {current_image_index + 1} of "
            f"{num_images}"
        ),
        width="stretch",
        clamp=False,
    )


# def zoom_image(image: np.ndarray, zoom_factor: float) -> np.ndarray:
#    """
#    Apply zoom by cropping and resizing.
#
#    Args:
#        image: Grayscale image.
#        zoom_factor: Zoom multiplier (>1 means zoom in).
#
#    Returns:
#        Zoomed image as numpy array.
#    """
#    h, w = image.shape
#    new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
#    top: int = (h - new_h) // 2
#    left: int = (w - new_w) // 2
#    cropped: np.ndarray = image[top : top + new_h, left : left + new_w]
#    zoomed: np.ndarray = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
#    return zoomed


# def apply_filter(image: np.ndarray, filter_type: str) -> np.ndarray:
#    """
#    Apply an image filter.
#
#    Args:
#        image: Grayscale or RGB image as numpy array.
#        filter_type: One of "Gaussian Blur", "Sharpen", "Edge Detection", "Original".
#
#    Returns:
#        Filtered image as numpy array.
#    """
#    if filter_type == "Gaussian Blur":
#        return cv2.GaussianBlur(image, (5, 5), 0)
#    elif filter_type == "Sharpen":
#        kernel: np.ndarray = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
#        return cv2.filter2D(image, -1, kernel)
#    elif filter_type == "Edge Detection":
#        return cv2.Canny(image, 100, 200)
#    else:
#        return image


# def apply_brightness_contrast_jpg(
#     image: Image.Image, brightness: int = 0, contrast: float = 1.0
# ) -> Image.Image:
#     """
#     Apply brightness and contrast adjustment for JPG/PNG images.

#     Args:
#         image: PIL Image.
#         brightness: Value to add after scaling.
#         contrast: Multiplicative factor for scaling.
#     Returns:
#         Adjusted image as PIL Image.
#     """

#     enhancer_contrast = ImageEnhance.Contrast(image)
#     img = enhancer_contrast.enhance(contrast)

#     enhancer_brightness = ImageEnhance.Brightness(img)
#     img = enhancer_brightness.enhance(1 + brightness / 100.0)

#     return img


# def get_filter_explanation(filter_type: str) -> str:
#     """
#     Get a human-readable explanation of a filter.

#     Args:
#         filter_type: Filter name.

#     Returns:
#         Explanation string.
#     """
#     explanations: Dict[str, str] = {
#         "Original": "No filter applied; view the raw image.",
#         "Gaussian Blur": "Smooths the image to reduce noise and detail, useful for preprocessing.",
#         "Sharpen": "Enhances edges and details to make structures more distinct.",
#         "Edge Detection": "Detects boundaries using Canny algorithm, highlighting edges.",
#     }
#     return explanations.get(filter_type, "")
