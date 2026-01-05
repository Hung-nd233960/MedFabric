# pylint: disable=missing-module-docstring, missing-function-docstring, unused-argument
# medfabric/pages/label_helper/dispatcher.py

from typing import Optional, Union, Callable, Dict
import streamlit as st
from medfabric.pages.label_helper.state_management import (
    HalfEvent,
    CompletedEvent,
    EventType,
    LabelingAppState,
    EventFlags,
    UIElementType,
)
from medfabric.db.orm_model import Region, ImageSetUsability
from medfabric.pages.utils import reset
from medfabric.pages.label_helper.submit_results import submit_image_set_results
from medfabric.pages.label_helper.unsatisfactory_sessions import (
    score_based_evaluation,
)
from medfabric.pages.label_helper.image_session_status import (
    SliceStatus,
    delete_slice,
    modify_status,
    handle_df_region_change,
    clear_all_slices,
    validate_slices,
    consecutive_slices,
)
from medfabric.pages.label_helper.image_set_session_status import (
    SetStatus,
    mark_status,
)
from medfabric.api.config import DEFAULT_BRIGHTNESS, DEFAULT_CONTRAST, DEFAULT_FILTER
from medfabric.db.engine import get_session_factory


def reimplement_score_fields_in_session(
    app_state: LabelingAppState, app=st.session_state
):
    """Reimplement score fields for the current image session."""
    img_session = app_state.current_session.current_image_session
    app[
        app.key_mngr.make(
            UIElementType.NUMBER_INPUT,
            EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED,
            app_state.current_session.uuid,
        )
    ] = img_session.basal_score_central_left
    app[
        app.key_mngr.make(
            UIElementType.NUMBER_INPUT,
            EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED,
            app_state.current_session.uuid,
        )
    ] = img_session.basal_score_central_right
    app[
        app.key_mngr.make(
            UIElementType.NUMBER_INPUT,
            EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED,
            app_state.current_session.uuid,
        )
    ] = img_session.basal_score_cortex_left
    app[
        app.key_mngr.make(
            UIElementType.NUMBER_INPUT,
            EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED,
            app_state.current_session.uuid,
        )
    ] = img_session.basal_score_cortex_right
    app[
        app.key_mngr.make(
            UIElementType.NUMBER_INPUT,
            EventType.CORONA_LEFT_SCORE_CHANGED,
            app_state.current_session.uuid,
        )
    ] = img_session.corona_score_left
    app[
        app.key_mngr.make(
            UIElementType.NUMBER_INPUT,
            EventType.CORONA_RIGHT_SCORE_CHANGED,
            app_state.current_session.uuid,
        )
    ] = img_session.corona_score_right


def reset_score_fields_in_session(
    mode: Region,
    app=st.session_state,
):
    """Reset score fields for the current image session."""
    if mode == Region.BasalCentral:
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.CORONA_LEFT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.CORONA_RIGHT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None
    elif mode == Region.CoronaRadiata:
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None
    elif mode == Region.BasalCortex:
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.CORONA_LEFT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.CORONA_RIGHT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None
    elif mode == Region.None_:
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.CORONA_LEFT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.CORONA_RIGHT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None
        app[
            app.key_mngr.make(
                UIElementType.NUMBER_INPUT,
                EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED,
                app.app_state.current_session.uuid,
            )
        ] = None


def reset_score_fields(app_state: LabelingAppState, mode: Region):
    """Reset score fields for the current image session."""
    img_session = app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ]
    if mode == Region.BasalCentral:
        img_session.corona_score_left = None
        img_session.corona_score_right = None
    elif mode == Region.CoronaRadiata:
        img_session.basal_score_central_left = None
        img_session.basal_score_central_right = None
        img_session.basal_score_cortex_left = None
        img_session.basal_score_cortex_right = None
    elif mode == Region.BasalCortex:
        img_session.corona_score_left = None
        img_session.corona_score_right = None
        img_session.basal_score_central_left = None
        img_session.basal_score_central_right = None
    elif mode == Region.None_:
        img_session.corona_score_left = None
        img_session.corona_score_right = None
        img_session.basal_score_central_left = None
        img_session.basal_score_central_right = None
        img_session.basal_score_cortex_left = None
        img_session.basal_score_cortex_right = None


def update_region_value(app_state: LabelingAppState, app=st.session_state):
    """Update the region value in the session state."""
    region = app_state.current_session.current_image_session.region
    if region == Region.BasalCortex:
        app[
            app.key_mngr.make(
                UIElementType.SEGMENTED_CONTROL,
                EventType.REGION_SELECTED,
                app_state.current_session.current_image_session.image_uuid,
            )
        ] = "BasalGangliaCortex"

    elif region == Region.BasalCentral:
        app[
            app.key_mngr.make(
                UIElementType.SEGMENTED_CONTROL,
                EventType.REGION_SELECTED,
                app_state.current_session.current_image_session.image_uuid,
            )
        ] = "BasalGangliaCentral"
    elif region == Region.CoronaRadiata:
        app[
            app.key_mngr.make(
                UIElementType.SEGMENTED_CONTROL,
                EventType.REGION_SELECTED,
                app_state.current_session.current_image_session.image_uuid,
            )
        ] = "CoronaRadiata"
    else:
        app[
            app.key_mngr.make(
                UIElementType.SEGMENTED_CONTROL,
                EventType.REGION_SELECTED,
                app_state.current_session.current_image_session.image_uuid,
            )
        ] = None


def handle_next_image(event: HalfEvent, app_state: LabelingAppState):
    app_state.current_session.current_index = (
        app_state.current_session.current_index + 1
    ) % app_state.current_session.num_images
    update_region_value(app_state)
    reimplement_score_fields_in_session(app_state)


def handle_prev_image(event: HalfEvent, app_state: LabelingAppState):
    app_state.current_session.current_index = (
        app_state.current_session.current_index - 1
    ) % app_state.current_session.num_images
    update_region_value(app_state)
    reimplement_score_fields_in_session(app_state)


def handle_jump_to_image(event: CompletedEvent, app_state: LabelingAppState):
    if event.payload:
        app_state.current_session.current_index = st.session_state[event.payload] - 1
    # print(app_state.current_session.current_index)
    update_region_value(app_state)
    reimplement_score_fields_in_session(app_state)


def handle_brightness_changed(event: CompletedEvent, app_state: LabelingAppState):
    app_state.brightness = st.session_state[event.payload]


def handle_contrast_changed(event: CompletedEvent, app_state: LabelingAppState):
    app_state.contrast = st.session_state[event.payload]


def handle_windowing_level_changed(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.window_level_current = st.session_state[event.payload]


def handle_windowing_width_changed(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.window_width_current = st.session_state[event.payload]


def handle_reset_windowing(
    event: HalfEvent, app_state: LabelingAppState, app=st.session_state
):
    app_state.current_session.window_level_current = (
        app_state.current_session.window_level_default
    )
    app_state.current_session.window_width_current = (
        app_state.current_session.window_width_default
    )
    app[
        app.key_mngr.make(
            UIElementType.NUMBER_INPUT,
            EventType.WINDOWING_WIDTH_CHANGED,
            app.app_state.current_session.uuid,
        )
    ] = app_state.current_session.window_width_default
    app[
        app.key_mngr.make(
            UIElementType.NUMBER_INPUT,
            EventType.WINDOWING_LEVEL_CHANGED,
            app.app_state.current_session.uuid,
        )
    ] = app_state.current_session.window_level_default


def handle_reset_adjustments(
    event: HalfEvent, app_state: LabelingAppState, app=st.session_state
):
    app_state.brightness = DEFAULT_BRIGHTNESS
    app_state.contrast = DEFAULT_CONTRAST
    app_state.filter_type = DEFAULT_FILTER
    app[app.key_mngr.make(UIElementType.SLIDER, EventType.BRIGHTNESS_CHANGED)] = (
        DEFAULT_BRIGHTNESS
    )
    app[app.key_mngr.make(UIElementType.SLIDER, EventType.CONTRAST_CHANGED)] = (
        DEFAULT_CONTRAST
    )


def handle_next_set(event: HalfEvent, app_state: LabelingAppState):
    app_state.session_index = (app_state.session_index + 1) % len(
        app_state.labeling_session
    )
    update_region_value(app_state)
    reimplement_score_fields_in_session(app_state)


def handle_prev_set(event: HalfEvent, app_state: LabelingAppState):
    app_state.session_index = (app_state.session_index - 1) % len(
        app_state.labeling_session
    )
    update_region_value(app_state)
    reimplement_score_fields_in_session(app_state)


def handle_jump_to_set(event: CompletedEvent, app_state: LabelingAppState):
    if event.payload:
        app_state.session_index = st.session_state[event.payload] - 1
    update_region_value(app_state)
    reimplement_score_fields_in_session(app_state)


def handle_region_selected(event: CompletedEvent, app_state: LabelingAppState):
    if event.payload:
        payload_content = st.session_state[event.payload]
    else:
        payload_content = None
    img_session = app_state.current_session.current_image_session

    if payload_content is None:
        img_session.region = Region.None_
        reset_score_fields(app_state, Region.None_)
        reset_score_fields_in_session(Region.None_)
        app_state.current_session.slice_status_df = delete_slice(
            app_state.current_session.slice_status_df, img_session.image_uuid
        )
        if validate_slices(app_state.current_session.slice_status_df):
            app_state.set_status_df = mark_status(
                app_state.set_status_df,
                app_state.current_session.uuid,
                SetStatus.VALID,
            )
            app_state.current_session.render_valid_message = True
        else:
            app_state.current_session.render_valid_message = False

    elif payload_content == "BasalGangliaCentral":
        img_session.region = Region.BasalCentral
        reset_score_fields(app_state, Region.BasalCentral)
        reset_score_fields_in_session(Region.BasalCentral)
        app_state.current_session.slice_status_df = handle_df_region_change(
            app_state.current_session.slice_status_df,
            app_state.current_session.current_index,
            img_session.image_uuid,
            Region.BasalCentral,
        )
    elif payload_content == "BasalGangliaCortex":
        img_session.region = Region.BasalCortex
        reset_score_fields(app_state, Region.BasalCortex)
        reset_score_fields_in_session(Region.BasalCortex)
        app_state.current_session.slice_status_df = handle_df_region_change(
            app_state.current_session.slice_status_df,
            app_state.current_session.current_index,
            img_session.image_uuid,
            Region.BasalCortex,
        )
        if score_based_evaluation(img_session):
            app_state.current_session.slice_status_df = modify_status(
                app_state.current_session.slice_status_df,
                img_session.image_uuid,
                SliceStatus.COMPLETED,
            )
        if validate_slices(app_state.current_session.slice_status_df):
            app_state.set_status_df = mark_status(
                app_state.set_status_df,
                app_state.current_session.uuid,
                SetStatus.VALID,
            )
            app_state.current_session.render_valid_message = True
        else:
            app_state.current_session.render_valid_message = False

    elif payload_content == "CoronaRadiata":
        img_session.region = Region.CoronaRadiata
        reset_score_fields(app_state, Region.CoronaRadiata)
        reset_score_fields_in_session(Region.CoronaRadiata)
        app_state.current_session.slice_status_df = handle_df_region_change(
            app_state.current_session.slice_status_df,
            app_state.current_session.current_index,
            img_session.image_uuid,
            Region.CoronaRadiata,
        )
    if consecutive_slices(app_state.current_session.slice_status_df):
        app_state.current_session.consecutive_slices = True
    else:
        app_state.current_session.consecutive_slices = False


def evaluate_score_and_update_status(app_state: LabelingAppState):
    img_session = app_state.current_session.current_image_session
    if score_based_evaluation(img_session):
        app_state.current_session.slice_status_df = modify_status(
            app_state.current_session.slice_status_df,
            img_session.image_uuid,
            SliceStatus.COMPLETED,
        )
    else:
        app_state.current_session.slice_status_df = modify_status(
            app_state.current_session.slice_status_df,
            img_session.image_uuid,
            SliceStatus.INCOMPLETED,
        )


def handle_basal_central_left_score(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ].basal_score_central_left = st.session_state[event.payload]
    evaluate_score_and_update_status(app_state)
    if validate_slices(app_state.current_session.slice_status_df):
        app_state.set_status_df = mark_status(
            app_state.set_status_df,
            app_state.current_session.uuid,
            SetStatus.VALID,
        )
        app_state.current_session.render_valid_message = True
    else:
        app_state.current_session.render_valid_message = False


def handle_basal_central_right_score(
    event: CompletedEvent, app_state: LabelingAppState
):
    app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ].basal_score_central_right = st.session_state[event.payload]
    evaluate_score_and_update_status(app_state)
    if validate_slices(app_state.current_session.slice_status_df):
        app_state.set_status_df = mark_status(
            app_state.set_status_df,
            app_state.current_session.uuid,
            SetStatus.VALID,
        )
        app_state.current_session.render_valid_message = True


def handle_basal_cortex_left_score(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ].basal_score_cortex_left = st.session_state[event.payload]
    evaluate_score_and_update_status(app_state)
    if validate_slices(app_state.current_session.slice_status_df):
        app_state.set_status_df = mark_status(
            app_state.set_status_df,
            app_state.current_session.uuid,
            SetStatus.VALID,
        )
        app_state.current_session.render_valid_message = True


def handle_basal_cortex_right_score(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ].basal_score_cortex_right = st.session_state[event.payload]
    evaluate_score_and_update_status(app_state)
    if validate_slices(app_state.current_session.slice_status_df):
        app_state.set_status_df = mark_status(
            app_state.set_status_df,
            app_state.current_session.uuid,
            SetStatus.VALID,
        )
        app_state.current_session.render_valid_message = True


def handle_corona_left_score(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ].corona_score_left = st.session_state[event.payload]
    evaluate_score_and_update_status(app_state)
    if validate_slices(app_state.current_session.slice_status_df):
        app_state.set_status_df = mark_status(
            app_state.set_status_df,
            app_state.current_session.uuid,
            SetStatus.VALID,
        )
        app_state.current_session.render_valid_message = True


def handle_corona_right_score(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ].corona_score_right = st.session_state[event.payload]
    evaluate_score_and_update_status(app_state)
    if validate_slices(app_state.current_session.slice_status_df):
        app_state.set_status_df = mark_status(
            app_state.set_status_df,
            app_state.current_session.uuid,
            SetStatus.VALID,
        )
        app_state.current_session.render_valid_message = True


def handle_notes_changed(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.notes = st.session_state[event.payload]


def disable_score_fields(app_state: LabelingAppState):
    if (
        app_state.current_session.image_set_usability
        != ImageSetUsability.IschemicAssessable
        or app_state.current_session.low_quality
    ):
        app_state.current_session.render_score_box_mode = False
    else:
        app_state.current_session.render_score_box_mode = True


image_set_usability_translation_dict = {
    "Ischemic": ImageSetUsability.IschemicAssessable,
    "Hemorrhagic": ImageSetUsability.HemorrhagicPresent,
    "Undertermined": ImageSetUsability.Indeterminate,
    "Normal": ImageSetUsability.Normal,
    "True Irrelevant": ImageSetUsability.TrueIrrelevant,
}


def handle_mark_irrelevant(event: CompletedEvent, app_state: LabelingAppState):

    raw_value = st.session_state[event.payload]
    # previous_value = app_state.current_session.image_set_usability
    app_state.current_session.image_set_usability = (
        image_set_usability_translation_dict[raw_value]
    )
    if (
        app_state.current_session.image_set_usability
        != ImageSetUsability.IschemicAssessable
    ):
        for img in app_state.current_session.images_sessions:
            img.region = Region.None_
            reset_score_fields(app_state, Region.None_)
            reset_score_fields_in_session(Region.None_)
        app_state.current_session.slice_status_df = clear_all_slices()
        app_state.set_status_df = mark_status(
            app_state.set_status_df,
            app_state.current_session.uuid,
            SetStatus.VALID,
        )
    else:
        app_state.set_status_df = mark_status(
            app_state.set_status_df,
            app_state.current_session.uuid,
            SetStatus.INVALID,
        )
    app_state.current_session.render_valid_message = False
    app_state.current_session.low_quality = False
    disable_score_fields(app_state)


def handle_mark_low_quality(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.low_quality = st.session_state[event.payload]
    if app_state.current_session.low_quality:
        for img in app_state.current_session.images_sessions:
            img.region = Region.None_
            reset_score_fields(app_state, Region.None_)
            reset_score_fields_in_session(Region.None_)
        app_state.current_session.slice_status_df = clear_all_slices()
        app_state.set_status_df = mark_status(
            app_state.set_status_df,
            app_state.current_session.uuid,
            SetStatus.VALID,
        )
    else:
        app_state.set_status_df = mark_status(
            app_state.set_status_df,
            app_state.current_session.uuid,
            SetStatus.INVALID,
        )
    app_state.current_session.render_valid_message = False
    disable_score_fields(app_state)


def handle_logout(event: HalfEvent, app_state: LabelingAppState):
    reset()


def handle_submit(event: HalfEvent, app_state: LabelingAppState):
    db_session = get_session_factory()()
    for image_set in app_state.labeling_session:
        submit_image_set_results(
            db_session=db_session,
            doctor_uuid=app_state.doctor_id,
            session_uuid=app_state.login_session,
            result=image_set,
        )
    db_session.close()
    reset()


EVENT_DISPATCH: Dict[EventType, Callable] = {
    EventType.NEXT_IMAGE: handle_next_image,
    EventType.PREV_IMAGE: handle_prev_image,
    EventType.JUMP_TO_IMAGE: handle_jump_to_image,
    EventType.BRIGHTNESS_CHANGED: handle_brightness_changed,
    EventType.CONTRAST_CHANGED: handle_contrast_changed,
    EventType.RESET_ADJUSTMENTS: handle_reset_adjustments,
    EventType.WINDOWING_LEVEL_CHANGED: handle_windowing_level_changed,
    EventType.WINDOWING_WIDTH_CHANGED: handle_windowing_width_changed,
    EventType.RESET_WINDOWING: handle_reset_windowing,
    EventType.NEXT_SET: handle_next_set,
    EventType.PREV_SET: handle_prev_set,
    EventType.JUMP_TO_SET: handle_jump_to_set,
    EventType.REGION_SELECTED: handle_region_selected,
    EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED: handle_basal_central_left_score,
    EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED: handle_basal_central_right_score,
    EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED: handle_basal_cortex_left_score,
    EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED: handle_basal_cortex_right_score,
    EventType.CORONA_LEFT_SCORE_CHANGED: handle_corona_left_score,
    EventType.CORONA_RIGHT_SCORE_CHANGED: handle_corona_right_score,
    EventType.NOTES_CHANGED: handle_notes_changed,
    EventType.MARK_IRRELEVANT_CHANGED: handle_mark_irrelevant,
    EventType.MARK_LOW_QUALITY_CHANGED: handle_mark_low_quality,
    EventType.LOGOUT: handle_logout,
    EventType.SUBMIT: handle_submit,
}


def flag_listener(flag: EventFlags, app_state: LabelingAppState):
    """Process one event (if any) using the dispatch table."""
    event: Optional[Union[HalfEvent, CompletedEvent]] = flag.pop()
    flag.clear()  # Ensure only one event is processed at a time
    if not event:
        return

    handler = EVENT_DISPATCH.get(event.type)
    if handler is not None:
        handler(event, app_state)
