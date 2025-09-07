# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
# medfabric/pages/label_helper/label_page_object.py
### The loop goes like this:
# 1. UI elemments get interacted with
# 2. on_change triggers first
# 3. state is updated
# 4. rerun with new state


### so system should be designed as:
# 1. Interacted element triggers on_change
# 2. on_change triggers a flag update
# 3. state is updated
# 4. rerun with new state and update the system with the flag
import uuid as uuid_lib
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Callable
import pandas as pd
import streamlit as st

from sqlalchemy.orm import Session as db_Session
from medfabric.pages.core.pages import BasePage
from medfabric.pages.core.queue_manager import Event
from medfabric.pages.core.utils import reset
from medfabric.pages.label_helper.session_initialization import (
    ImageSetEvaluationSession,
)
from medfabric.pages.label_helper.image_set_session_status import (
    create_set_status_dataframe,
)
from medfabric.api.config import DEFAULT_BRIGHTNESS, DEFAULT_CONTRAST, DEFAULT_FILTER
from medfabric.pages.core.enum_key_manager import UIElementType
from medfabric.db.models import Region
from medfabric.pages.label_helper.image_session_status import (
    validate_slices,
    delete_slice,
    handle_df_region_change,
    clear_all_slices,
    modify_status,
    SliceStatus,
)
from medfabric.pages.label_helper.image_set_session_status import (
    SetStatus,
    mark_status,
)
from medfabric.pages.label_helper.submit_results import submit_image_set_results
from medfabric.pages.label_helper.unsatisfactory_sessions import (
    score_based_evaluation,
)
from medfabric.pages.core.enum_key_manager import Key
from medfabric.api.config import BASAL_CENTRAL_MAX, BASAL_CORTEX_MAX, CORONA_MAX
from medfabric.pages.label_helper.image_set_session_status import (
    get_invalid_indices,
)
from medfabric.pages.label_helper.image_helper import apply_brightness_contrast


def render_text(text: str) -> str:
    """Render text in the Streamlit app."""
    if text == "BasalGangliaCortex":
        return "Basal Ganglia (Cortex)"
    elif text == "BasalGangliaCentral":
        return "Basal Ganglia (Central)"
    elif text == "CoronaRadiata":
        return "Corona Radiata"
    return text


class FilterType(Enum):
    NONE = "None"
    GAUSSIAN = "Gaussian_Blur"
    SHARPEN = "Sharpen"
    EDGE_DETECTION = "Edge_Detect"


class LabelingPageEventType(Enum):
    """Types of user interaction events."""

    NEXT_IMAGE = auto()
    PREV_IMAGE = auto()
    JUMP_TO_IMAGE = auto()
    NEXT_SET = auto()
    PREV_SET = auto()
    JUMP_TO_SET = auto()
    BRIGHTNESS_CHANGED = auto()
    CONTRAST_CHANGED = auto()
    FILTER_CHANGED = auto()
    RESET_ADJUSTMENTS = auto()
    REGION_SELECTED = auto()
    BASAL_CORTEX_LEFT_SCORE_CHANGED = auto()
    BASAL_CORTEX_RIGHT_SCORE_CHANGED = auto()
    BASAL_CENTRAL_LEFT_SCORE_CHANGED = auto()
    BASAL_CENTRAL_RIGHT_SCORE_CHANGED = auto()
    CORONA_LEFT_SCORE_CHANGED = auto()
    CORONA_RIGHT_SCORE_CHANGED = auto()
    NOTES_CHANGED = auto()
    MARK_LOW_QUALITY = auto()
    MARK_IRRELEVANT = auto()
    SAVE = auto()
    CANCEL = auto()
    SUBMIT = auto()
    LOGOUT = auto()


@dataclass(init=False)
class LabelingPage(BasePage[LabelingPageEventType]):
    EventType = LabelingPageEventType

    labeling_session: List["ImageSetEvaluationSession"]
    doctor_id: uuid_lib.UUID
    login_session: uuid_lib.UUID
    db_session: "db_Session"

    brightness: int = field(default=DEFAULT_BRIGHTNESS)
    contrast: float = field(default=DEFAULT_CONTRAST)
    filter_type: FilterType = field(default=FilterType.NONE)

    session_index: int = field(default=0)
    set_status_df: pd.DataFrame = field(default_factory=create_set_status_dataframe)
    all_sessions_satisfactory: bool = field(default=False)

    # --- Custom init ---
    def __init__(
        self,
        labeling_session: list["ImageSetEvaluationSession"],
        doctor_id: uuid_lib.UUID,
        login_session: uuid_lib.UUID,
        db_session: "db_Session",
    ):
        super().__init__()  # still call BasePage init
        self.labeling_session = labeling_session
        self.doctor_id = doctor_id
        self.login_session = login_session
        self.db_session = db_session
        self.brightness = DEFAULT_BRIGHTNESS
        self.contrast = DEFAULT_CONTRAST
        self.filter_type = FilterType.NONE
        self.session_index = 0
        self.set_status_df = create_set_status_dataframe()
        self.all_sessions_satisfactory = False
        # Defaults are automatically applied from fields

    # --- Methods ---
    @property
    def current_session(self) -> "ImageSetEvaluationSession":
        return self.labeling_session[self.session_index]

    # --- Dispatcher Block ---
    def setup_dispatch_table(self) -> None:
        self.dispatch_table: Dict[LabelingPageEventType, Callable] = {
            self.EventType.NEXT_IMAGE: self._handle_next_image,
            self.EventType.PREV_IMAGE: self._handle_prev_image,
            self.EventType.JUMP_TO_IMAGE: self._handle_jump_to_image,
            self.EventType.BRIGHTNESS_CHANGED: self._handle_brightness_changed,
            self.EventType.CONTRAST_CHANGED: self._handle_contrast_changed,
            self.EventType.RESET_ADJUSTMENTS: self._handle_reset_adjustments,
            self.EventType.FILTER_CHANGED: self._handle_contrast_changed,
            self.EventType.NEXT_SET: self._handle_next_set,
            self.EventType.PREV_SET: self._handle_prev_set,
            self.EventType.JUMP_TO_SET: self._handle_jump_to_set,
            self.EventType.REGION_SELECTED: self._handle_region_selected,
            self.EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED: self._handle_score_event,
            self.EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED: self._handle_score_event,
            self.EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED: self._handle_score_event,
            self.EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED: self._handle_score_event,
            self.EventType.CORONA_LEFT_SCORE_CHANGED: self._handle_score_event,
            self.EventType.CORONA_RIGHT_SCORE_CHANGED: self._handle_score_event,
            self.EventType.NOTES_CHANGED: self._handle_notes_changed,
            self.EventType.MARK_IRRELEVANT: self._handle_mark_irrelevant,
            self.EventType.MARK_LOW_QUALITY: self._handle_mark_low_quality,
            self.EventType.LOGOUT: self._handle_logout,
            self.EventType.SUBMIT: self._handle_submit,
        }

    def _reimplement_score_fields_in_session(self, app=st.session_state):
        """Reapply score fields for the current image session."""
        session = self.current_session
        img_session = session.current_image_session
        uid = session.uuid
        km = self.key_manager

        app[
            str(
                km.make(
                    UIElementType.NUMBER_INPUT,
                    self.EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED,
                    uid,
                )
            )
        ] = img_session.basal_score_central_left
        app[
            str(
                km.make(
                    UIElementType.NUMBER_INPUT,
                    self.EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED,
                    uid,
                )
            )
        ] = img_session.basal_score_central_right
        app[
            str(
                km.make(
                    UIElementType.NUMBER_INPUT,
                    self.EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED,
                    uid,
                )
            )
        ] = img_session.basal_score_cortex_left
        app[
            str(
                km.make(
                    UIElementType.NUMBER_INPUT,
                    self.EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED,
                    uid,
                )
            )
        ] = img_session.basal_score_cortex_right
        app[
            str(
                km.make(
                    UIElementType.NUMBER_INPUT,
                    self.EventType.CORONA_LEFT_SCORE_CHANGED,
                    uid,
                )
            )
        ] = img_session.corona_score_left
        app[
            str(
                km.make(
                    UIElementType.NUMBER_INPUT,
                    self.EventType.CORONA_RIGHT_SCORE_CHANGED,
                    uid,
                )
            )
        ] = img_session.corona_score_right

    def _reset_score_fields(self, mode: Region):
        """Reset score fields for the current image session."""
        img_session = self.current_session.current_image_session

        fields_to_reset = {
            Region.BasalCentral: ["corona_score_left", "corona_score_right"],
            Region.CoronaRadiata: [
                "basal_score_central_left",
                "basal_score_central_right",
                "basal_score_cortex_left",
                "basal_score_cortex_right",
            ],
            Region.BasalCortex: [
                "corona_score_left",
                "corona_score_right",
                "basal_score_central_left",
                "basal_score_central_right",
            ],
            Region.None_: [
                "corona_score_left",
                "corona_score_right",
                "basal_score_central_left",
                "basal_score_central_right",
                "basal_score_cortex_left",
                "basal_score_cortex_right",
            ],
        }

        for field_ in fields_to_reset.get(mode, []):  # field_ to avoid shadowing
            setattr(img_session, field_, None)

    def _reset_score_fields_in_session(
        self,
        mode: Region,
        app=st.session_state,
    ):
        """Reset score fields for the current image session."""
        km = self.key_manager
        uid = self.current_session.uuid

        # Define mapping of Region -> EventTypes that should be reset
        reset_map: Dict[Region, List[LabelingPageEventType]] = {
            Region.BasalCentral: [
                self.EventType.CORONA_LEFT_SCORE_CHANGED,
                self.EventType.CORONA_RIGHT_SCORE_CHANGED,
            ],
            Region.CoronaRadiata: [
                self.EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED,
                self.EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED,
                self.EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED,
                self.EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED,
            ],
            Region.BasalCortex: [
                self.EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED,
                self.EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED,
                self.EventType.CORONA_LEFT_SCORE_CHANGED,
                self.EventType.CORONA_RIGHT_SCORE_CHANGED,
            ],
            Region.None_: [
                self.EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED,
                self.EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED,
                self.EventType.CORONA_LEFT_SCORE_CHANGED,
                self.EventType.CORONA_RIGHT_SCORE_CHANGED,
                self.EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED,
                self.EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED,
            ],
        }

        for event_type in reset_map.get(mode, []):
            key = str(km.make(UIElementType.NUMBER_INPUT, event_type, uid))
            app[key] = None

    def _update_region_value(self, app=st.session_state):
        """Update the region value in the session state."""
        region = self.current_session.current_image_session.region
        km = self.key_manager

        if region == Region.BasalCortex:
            app[
                str(
                    km.make(
                        UIElementType.SEGMENTED_CONTROL,
                        self.EventType.REGION_SELECTED,
                        self.current_session.current_image_session.image_uuid,
                    )
                )
            ] = "BasalGangliaCortex"

        elif region == Region.BasalCentral:
            app[
                str(
                    km.make(
                        UIElementType.SEGMENTED_CONTROL,
                        self.EventType.REGION_SELECTED,
                        self.current_session.current_image_session.image_uuid,
                    )
                )
            ] = "BasalGangliaCentral"
        elif region == Region.CoronaRadiata:
            app[
                str(
                    km.make(
                        UIElementType.SEGMENTED_CONTROL,
                        self.EventType.REGION_SELECTED,
                        self.current_session.current_image_session.image_uuid,
                    )
                )
            ] = "CoronaRadiata"
        else:
            app[
                str(
                    km.make(
                        UIElementType.SEGMENTED_CONTROL,
                        self.EventType.REGION_SELECTED,
                        self.current_session.current_image_session.image_uuid,
                    )
                )
            ] = None

    def _handle_next_image(self, event: Event):
        self.current_session.current_index = (
            self.current_session.current_index + 1
        ) % self.current_session.num_images
        self._update_region_value()
        self._reimplement_score_fields_in_session()

    def _handle_prev_image(self, event: Event):
        self.current_session.current_index = (
            self.current_session.current_index - 1
        ) % self.current_session.num_images
        self._update_region_value()
        self._reimplement_score_fields_in_session()

    def _handle_jump_to_image(self, event: Event):
        if event.payload:
            self.current_session.current_index = (
                st.session_state[str(event.payload)] - 1
            )
        self._update_region_value()
        self._reimplement_score_fields_in_session()

    def _handle_brightness_changed(self, event: Event):
        self.brightness = st.session_state[str(event.payload)]

    def _handle_contrast_changed(self, event: Event):
        self.contrast = st.session_state[str(event.payload)]

    def _handle_reset_adjustments(self, app=st.session_state):
        self.brightness = DEFAULT_BRIGHTNESS
        self.contrast = DEFAULT_CONTRAST
        self.filter_type = DEFAULT_FILTER
        app[
            str(
                self.key_manager.make(
                    UIElementType.SLIDER, self.EventType.BRIGHTNESS_CHANGED
                )
            )
        ] = DEFAULT_BRIGHTNESS
        app[
            str(
                self.key_manager.make(
                    UIElementType.SLIDER, self.EventType.CONTRAST_CHANGED
                )
            )
        ] = DEFAULT_CONTRAST

    def _handle_next_set(self):
        self.session_index = (self.session_index + 1) % len(self.labeling_session)
        self._update_region_value()
        self._reimplement_score_fields_in_session()

    def _handle_prev_set(self):
        self.session_index = (self.session_index - 1) % len(self.labeling_session)
        self._update_region_value()
        self._reimplement_score_fields_in_session()

    def _handle_jump_to_set(self, event: Event):
        if event.payload:
            self.session_index = st.session_state[str(event.payload)] - 1
        self._update_region_value()
        self._reimplement_score_fields_in_session()

    def _handle_region_selected(self, event: Event):
        if event.payload:
            payload_content = st.session_state[str(event.payload)]
        else:
            payload_content = None
        img_session = self.current_session.current_image_session

        if payload_content is None:
            img_session.region = Region.None_
            self._reset_score_fields(Region.None_)
            self._reset_score_fields_in_session(Region.None_)
            self.current_session.slice_status_df = delete_slice(
                self.current_session.slice_status_df, img_session.image_uuid
            )
            if validate_slices(self.current_session.slice_status_df):
                self.set_status_df = mark_status(
                    self.set_status_df,
                    self.current_session.uuid,
                    SetStatus.VALID,
                )
        elif payload_content == "BasalGangliaCentral":
            img_session.region = Region.BasalCentral
            self._reset_score_fields(Region.BasalCentral)
            self._reset_score_fields_in_session(Region.BasalCentral)
            self.current_session.slice_status_df = handle_df_region_change(
                self.current_session.slice_status_df,
                self.current_session.current_index,
                img_session.image_uuid,
                Region.BasalCentral,
            )
        elif payload_content == "BasalGangliaCortex":
            img_session.region = Region.BasalCortex
            self._reset_score_fields(Region.BasalCortex)
            self._reset_score_fields_in_session(Region.BasalCortex)
            self.current_session.slice_status_df = handle_df_region_change(
                self.current_session.slice_status_df,
                self.current_session.current_index,
                img_session.image_uuid,
                Region.BasalCortex,
            )
            if score_based_evaluation(img_session):
                self.current_session.slice_status_df = modify_status(
                    self.current_session.slice_status_df,
                    img_session.image_uuid,
                    SliceStatus.COMPLETED,
                )
            if validate_slices(self.current_session.slice_status_df):
                self.set_status_df = mark_status(
                    self.set_status_df,
                    self.current_session.uuid,
                    SetStatus.VALID,
                )
        elif payload_content == "CoronaRadiata":
            img_session.region = Region.CoronaRadiata
            self._reset_score_fields(Region.CoronaRadiata)
            self._reset_score_fields_in_session(Region.CoronaRadiata)
            self.current_session.slice_status_df = handle_df_region_change(
                self.current_session.slice_status_df,
                self.current_session.current_index,
                img_session.image_uuid,
                Region.CoronaRadiata,
            )

    def _evaluate_score_and_update_status(self):
        img_session = self.current_session.current_image_session
        if score_based_evaluation(img_session):
            self.current_session.slice_status_df = modify_status(
                self.current_session.slice_status_df,
                img_session.image_uuid,
                SliceStatus.COMPLETED,
            )
        else:
            self.current_session.slice_status_df = modify_status(
                self.current_session.slice_status_df,
                img_session.image_uuid,
                SliceStatus.INCOMPLETED,
            )

    def _handle_score_event(self, event: Event):
        """Generic handler for all score change events."""
        session = self.current_session
        img_session = session.current_image_session

        # Mapping: EventType → attribute name on ImageSession
        field_map = {
            self.EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED: "basal_score_central_left",
            self.EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED: "basal_score_central_right",
            self.EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED: "basal_score_cortex_left",
            self.EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED: "basal_score_cortex_right",
            self.EventType.CORONA_LEFT_SCORE_CHANGED: "corona_score_left",
            self.EventType.CORONA_RIGHT_SCORE_CHANGED: "corona_score_right",
        }

        attr = field_map.get(event.type_)
        if not attr:
            raise ValueError(f"Unexpected score event: {event.type_}")

        # Update the corresponding field
        setattr(img_session, attr, st.session_state[str(event.payload)])

        # Re-run validations and update status
        self._evaluate_score_and_update_status()
        if validate_slices(session.slice_status_df):
            self.set_status_df = mark_status(
                self.set_status_df,
                session.uuid,
                SetStatus.VALID,
            )

    def _handle_notes_changed(self, event: Event):
        self.current_session.notes = st.session_state[str(event.payload)]

    def _disable_score_fields(self):
        if self.current_session.irrelevant_data or self.current_session.low_quality:
            self.current_session.render_score_box_mode = False
        else:
            self.current_session.render_score_box_mode = True

    def _handle_mark_irrelevant(self, event: Event):
        self.current_session.irrelevant_data = st.session_state[str(event.payload)]
        if self.current_session.irrelevant_data:
            for img in self.current_session.images_sessions:
                img.region = Region.None_
                self._reset_score_fields(Region.None_)
                self._reset_score_fields_in_session(Region.None_)
            self.current_session.slice_status_df = clear_all_slices()
            self.set_status_df = mark_status(
                self.set_status_df,
                self.current_session.uuid,
                SetStatus.VALID,
            )
        else:
            self.set_status_df = mark_status(
                self.set_status_df,
                self.current_session.uuid,
                SetStatus.INVALID,
            )

        self._disable_score_fields()

    def _handle_mark_low_quality(self, event: Event):
        self.current_session.low_quality = st.session_state[str(event.payload)]
        if self.current_session.low_quality:
            for img in self.current_session.images_sessions:
                img.region = Region.None_
                self._reset_score_fields(Region.None_)
                self._reset_score_fields_in_session(Region.None_)
            self.current_session.slice_status_df = clear_all_slices()
            self.set_status_df = mark_status(
                self.set_status_df,
                self.current_session.uuid,
                SetStatus.VALID,
            )
        else:
            self.set_status_df = mark_status(
                self.set_status_df,
                self.current_session.uuid,
                SetStatus.INVALID,
            )
        self._disable_score_fields()

    def _handle_logout(self):
        reset()

    def _handle_submit(self):
        for image_set in self.labeling_session:
            submit_image_set_results(
                db_session=self.db_session,
                doctor_uuid=self.doctor_id,
                session_uuid=self.login_session,
                result=image_set,
            )
        reset()

    # --- Render Block ---
    def render_set_column(
        self,
        prev_key: Key,
        next_key: Key,
        jump_to_key: Key,
        current_index: int,
        num_sets: int,
    ) -> None:
        """Render a column with set navigation controls."""
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            st.button(
                "Previous Set",
                key=str(prev_key),
                on_click=self.raise_event,
                args=(self.EventType.PREV_SET,),
            )
        with col2:
            st.button(
                "Next Set",
                key=str(next_key),
                on_click=self.raise_event,
                args=(self.EventType.NEXT_SET,),
            )
        with col3:
            st.slider(
                "Jump to set",
                1,
                num_sets,
                current_index + 1,
                key=str(jump_to_key),
                on_change=self.raise_event,
                args=(
                    self.EventType.JUMP_TO_SET,
                    jump_to_key,
                ),
            )

    def render_logout_button(self, key: Key) -> None:
        """Render a logout button."""
        st.button(
            "Logout",
            key=str(key),
            type="secondary",
            on_click=self.raise_event,
            args=(self.EventType.LOGOUT,),
        )

    def render_image_region_selection(self, key: Key) -> None:
        """Render a segmented control for region selection."""
        options = [
            "BasalGangliaCortex",
            "BasalGangliaCentral",
            "CoronaRadiata",
        ]
        st.pills(
            "Region",
            options=options,
            key=str(key),
            default=None,
            format_func=render_text,
            on_change=self.raise_event,
            args=(
                self.EventType.REGION_SELECTED,
                key,
            ),
        )

    def render_image_navigation_controls(
        self,
        next_img_key: Key,
        prev_img_key: Key,
        img_slider_key: Key,
        num_images: int,
        current_index: int,
        brightness: int,
        contrast: float,
        brightness_slider_key: Key,
        contrast_slider_key: Key,
        reset_key: Key,
        filter_selectbox_key: Key,
    ) -> None:
        """Render navigation controls for image selection."""
        with st.expander("Image Navigation and Adjustment Controls", expanded=True):
            st.write(f"Image {current_index + 1} of {num_images}")
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                st.button(
                    "Prev Image",
                    key=str(prev_img_key),
                    on_click=self.raise_event,
                    args=(self.EventType.PREV_IMAGE,),
                )
            with col2:
                st.button(
                    "Next Image",
                    key=str(next_img_key),
                    on_click=self.raise_event,
                    args=(self.EventType.NEXT_IMAGE,),
                )
            with col3:
                st.slider(
                    "Jump to image",
                    1,
                    num_images,
                    current_index + 1,
                    key=str(img_slider_key),
                    on_change=self.raise_event,
                    args=(
                        self.EventType.JUMP_TO_IMAGE,
                        img_slider_key,
                    ),
                )
            col1, col2 = st.columns(2)
            with col1:
                st.slider(
                    "Brightness",
                    -100,
                    100,
                    brightness,
                    key=str(brightness_slider_key),
                    on_change=self.raise_event,
                    args=(
                        self.EventType.BRIGHTNESS_CHANGED,
                        brightness_slider_key,
                    ),
                )
                st.button(
                    "Reset Adjustments",
                    key=str(reset_key),
                    on_click=self.raise_event,
                    args=(self.EventType.RESET_ADJUSTMENTS,),
                )
            with col2:
                st.slider(
                    "Contrast",
                    0.1,
                    3.0,
                    contrast,
                    key=str(contrast_slider_key),
                    on_change=self.raise_event,
                    args=(
                        self.EventType.CONTRAST_CHANGED,
                        contrast_slider_key,
                    ),
                )
                st.selectbox(
                    "Filter",
                    ["In Development"],
                    key=str(filter_selectbox_key),
                    on_change=self.raise_event,
                    disabled=True,
                    args=(self.EventType.FILTER_CHANGED, filter_selectbox_key),
                )

    def render_set_labeling_row(
        self, low_quality_key: Key, irrelevant_key: Key
    ) -> None:
        """Render checkboxes for marking low quality or irrelevant data."""
        acol1, acol2 = st.columns(2)
        with acol1:
            st.checkbox(
                "Low Quality",
                key=str(low_quality_key),
                on_change=self.raise_event,
                args=(self.EventType.MARK_LOW_QUALITY, low_quality_key),
            )
        with acol2:
            st.checkbox(
                "Irrelevant Data",
                key=str(irrelevant_key),
                on_change=self.raise_event,
                args=(self.EventType.MARK_IRRELEVANT, irrelevant_key),
            )

    def render_labeling_column(
        self,
        region_segmented_key: Key,
        key_basal_cortex_left: Key,
        key_basal_cortex_right: Key,
        key_basal_central_left: Key,
        key_basal_central_right: Key,
        key_corona_left: Key,
        key_corona_right: Key,
    ) -> None:
        """Render the labeling column with region selection and score inputs."""
        with st.expander("Image Annotation", expanded=True):
            if not self.current_session.render_score_box_mode:
                st.warning(
                    "Score inputs are disabled due to the image being marked as low quality or irrelevant."
                )
            else:
                self.render_image_region_selection(key=region_segmented_key)
                if self.current_session.current_image_session.region == Region.None_:
                    st.info("None region selected, no scores to display.")
                else:
                    acol1, acol2 = st.columns([1, 1])
                    with acol1:
                        if self.current_session.current_image_session.region in [
                            Region.BasalCortex,
                            Region.BasalCentral,
                        ]:
                            st.write("Left:")
                            st.number_input(
                                "Basal Cortex Score",
                                min_value=0,
                                max_value=BASAL_CORTEX_MAX,
                                step=1,
                                key=str(key_basal_cortex_left),
                                on_change=self.raise_event,
                                args=(
                                    self.EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED,
                                    key_basal_cortex_left,
                                ),
                            )
                        if (
                            self.current_session.current_image_session.region
                            == Region.BasalCentral
                        ):
                            st.number_input(
                                "Basal Central Score",
                                min_value=0,
                                max_value=BASAL_CENTRAL_MAX,
                                step=1,
                                key=str(key_basal_central_left),
                                on_change=self.raise_event,
                                args=(
                                    self.EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED,
                                    key_basal_central_left,
                                ),
                            )
                        if (
                            self.current_session.current_image_session.region
                            == Region.CoronaRadiata
                        ):
                            st.write("Left:")
                            st.number_input(
                                "Corona Radiata Score",
                                min_value=0,
                                max_value=CORONA_MAX,
                                step=1,
                                key=str(key_corona_left),
                                on_change=self.raise_event,
                                args=(
                                    self.EventType.CORONA_LEFT_SCORE_CHANGED,
                                    key_corona_left,
                                ),
                            )
                    with acol2:
                        if self.current_session.current_image_session.region in [
                            Region.BasalCortex,
                            Region.BasalCentral,
                        ]:
                            st.write("Right:")
                            st.number_input(
                                "Basal Cortex Score",
                                min_value=0,
                                max_value=BASAL_CORTEX_MAX,
                                step=1,
                                key=str(key_basal_cortex_right),
                                on_change=self.raise_event,
                                args=(
                                    self.EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED,
                                    key_basal_cortex_right,
                                ),
                            )
                        if (
                            self.current_session.current_image_session.region
                            == Region.BasalCentral
                        ):
                            st.number_input(
                                "Basal Central Score",
                                min_value=0,
                                max_value=BASAL_CENTRAL_MAX,
                                step=1,
                                key=str(key_basal_central_right),
                                on_change=self.raise_event,
                                args=(
                                    self.EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED,
                                    key_basal_central_right,
                                ),
                            )
                        if (
                            self.current_session.current_image_session.region
                            == Region.CoronaRadiata
                        ):
                            st.write("Right:")
                            st.number_input(
                                "Corona Radiata Score",
                                min_value=0,
                                max_value=CORONA_MAX,
                                step=1,
                                key=str(key_corona_right),
                                on_change=self.raise_event,
                                args=(
                                    self.EventType.CORONA_RIGHT_SCORE_CHANGED,
                                    key_corona_right,
                                ),
                            )

    def render(self):
        self.listen_events()
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            self.render_logout_button(
                key=self.key_manager.make(UIElementType.BUTTON, self.EventType.LOGOUT)
            )
            image = self.current_session.current_image_session.image_matrix
            processed_image = apply_brightness_contrast(
                image,
                self.brightness,
                self.contrast,
            )
            st.image(
                processed_image,
                caption=(
                    f"Set {self.session_index + 1} | "
                    f"Image {self.current_session.current_index + 1} of "
                    f"{self.current_session.num_images}"
                ),
                width="stretch",
                clamp=False,
            )
        with col2:
            self.render_image_navigation_controls(
                next_img_key=self.key_manager.make(
                    UIElementType.BUTTON, self.EventType.NEXT_IMAGE
                ),
                prev_img_key=self.key_manager.make(
                    UIElementType.BUTTON, self.EventType.PREV_IMAGE
                ),
                img_slider_key=self.key_manager.make(
                    UIElementType.SLIDER,
                    self.EventType.JUMP_TO_IMAGE,
                    self.current_session.uuid,
                ),
                num_images=self.current_session.num_images,
                current_index=self.current_session.current_index,
                brightness_slider_key=self.key_manager.make(
                    UIElementType.SLIDER,
                    self.EventType.BRIGHTNESS_CHANGED,
                    self.current_session.uuid,
                ),
                contrast=self.contrast,
                brightness=self.brightness,
                contrast_slider_key=self.key_manager.make(
                    UIElementType.SLIDER,
                    self.EventType.CONTRAST_CHANGED,
                    self.current_session.uuid,
                ),
                reset_key=self.key_manager.make(
                    UIElementType.BUTTON,
                    self.EventType.RESET_ADJUSTMENTS,
                ),
                filter_selectbox_key=self.key_manager.make(
                    UIElementType.SELECTBOX,
                    self.EventType.FILTER_CHANGED,
                    self.current_session.uuid,
                ),
            )

            self.render_labeling_column(
                region_segmented_key=self.key_manager.make(
                    UIElementType.SEGMENTED_CONTROL,
                    self.EventType.REGION_SELECTED,
                    self.current_session.current_image_session.image_uuid,
                ),
                key_basal_cortex_left=self.key_manager.make(
                    UIElementType.NUMBER_INPUT,
                    self.EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED,
                    self.current_session.current_image_session.image_uuid,
                ),
                key_basal_cortex_right=self.key_manager.make(
                    UIElementType.NUMBER_INPUT,
                    self.EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED,
                    self.current_session.current_image_session.image_uuid,
                ),
                key_basal_central_left=self.key_manager.make(
                    UIElementType.NUMBER_INPUT,
                    self.EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED,
                    self.current_session.current_image_session.image_uuid,
                ),
                key_basal_central_right=self.key_manager.make(
                    UIElementType.NUMBER_INPUT,
                    self.EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED,
                    self.current_session.current_image_session.image_uuid,
                ),
                key_corona_left=self.key_manager.make(
                    UIElementType.NUMBER_INPUT,
                    self.EventType.CORONA_LEFT_SCORE_CHANGED,
                    self.current_session.current_image_session.image_uuid,
                ),
                key_corona_right=self.key_manager.make(
                    UIElementType.NUMBER_INPUT,
                    self.EventType.CORONA_RIGHT_SCORE_CHANGED,
                    self.current_session.current_image_session.image_uuid,
                ),
            )

        with col3:
            tab1, tab2 = st.tabs(["Set Information", "All Sets Status"])
            with tab1:
                with st.expander("Set Navigation and Metadata", expanded=True):
                    st.write(
                        f"Set {self.session_index + 1} of {len(self.labeling_session)}"
                    )

                    self.render_set_column(
                        prev_key=self.key_manager.make(
                            UIElementType.BUTTON, self.EventType.PREV_SET
                        ),
                        next_key=self.key_manager.make(
                            UIElementType.BUTTON, self.EventType.NEXT_SET
                        ),
                        jump_to_key=self.key_manager.make(
                            UIElementType.SLIDER,
                            self.EventType.JUMP_TO_SET,
                        ),
                        current_index=self.session_index,
                        num_sets=len(self.labeling_session),
                    )
                with st.expander("Current Image Set Status", expanded=True):
                    if not self.current_session.render_score_box_mode:
                        st.info("This image set is valid for submission.")
                    else:
                        st.dataframe(
                            self.current_session.slice_status_df,
                            width="stretch",
                            hide_index=True,
                        )

                with st.expander("Set Annotations", expanded=True):
                    self.render_set_labeling_row(
                        low_quality_key=self.key_manager.make(
                            UIElementType.CHECKBOX,
                            self.EventType.MARK_LOW_QUALITY,
                            self.current_session.uuid,
                        ),
                        irrelevant_key=self.key_manager.make(
                            UIElementType.CHECKBOX,
                            self.EventType.MARK_IRRELEVANT,
                            self.current_session.uuid,
                        ),
                    )
                    st.text_area(
                        "Notes",
                        key=str(
                            self.key_manager.make(
                                UIElementType.TEXTAREA,
                                self.EventType.NOTES_CHANGED,
                                self.current_session.uuid,
                            )
                        ),
                        on_change=self.raise_event,
                        args=(
                            self.EventType.NOTES_CHANGED,
                            self.key_manager.make(
                                UIElementType.TEXTAREA,
                                self.EventType.NOTES_CHANGED,
                                self.current_session.uuid,
                            ),
                        ),
                    )
            with tab2:
                with st.expander("All image set statuses", expanded=False):
                    invalid_indices = get_invalid_indices(self.set_status_df)
                    if invalid_indices:
                        st.warning(
                            f"Some image sets are invalid. Invalid set indices: {", ".join(map(str, [i + 1 for i in invalid_indices]))}"
                        )
                    else:
                        st.success("All image sets are valid.")
                        st.success("You can proceed to submit your evaluations.")
                        st.button(
                            "Submit All Evaluations",
                            type="primary",
                            on_click=self.raise_event,
                            args=(self.EventType.SUBMIT,),
                        )
                    st.dataframe(
                        self.set_status_df,
                        width="stretch",
                        hide_index=True,
                    )
