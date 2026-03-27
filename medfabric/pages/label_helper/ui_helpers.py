"""Helper functions for UI text formatting and utilities.

This module provides utility functions for rendering and formatting UI text.
"""


def render_text(text: str) -> str:
    """Format text for display in the Streamlit app.

    Args:
        text: The text to format.

    Returns:
        Formatted text string.
    """
    if text == "BasalGanglia":
        return "Basal Ganglia"
    if text == "CoronaRadiata":
        return "Corona Radiata"
    return text
