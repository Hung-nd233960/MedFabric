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
from medfabric.db.models import Region
from medfabric.pages.utils import reset
from medfabric.pages.label_helper.submit_results import submit_image_set_results
from medfabric.pages.label_helper.unsatisfactory_sessions import (
    find_unsatisfactory_sessions,
)
from medfabric.api.config import DEFAULT_BRIGHTNESS, DEFAULT_CONTRAST, DEFAULT_FILTER


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


def update_unsatisfactory_sessions(app_state: LabelingAppState):
    """Update the list of unsatisfactory sessions in the app state."""
    unsat_sessions = find_unsatisfactory_sessions(app_state.labeling_session)
    app_state.unsatisfactory_sessions = unsat_sessions
    app_state.all_sessions_satisfactory = len(unsat_sessions) == 0


def handle_next_image(event: HalfEvent, app_state: LabelingAppState):
    app_state.current_session.current_index = (
        app_state.current_session.current_index + 1
    ) % app_state.current_session.num_images
    print(app_state.current_session.current_index)


def handle_prev_image(event: HalfEvent, app_state: LabelingAppState):
    app_state.current_session.current_index = (
        app_state.current_session.current_index - 1
    ) % app_state.current_session.num_images
    print(app_state.current_session.current_index)


def handle_jump_to_image(event: CompletedEvent, app_state: LabelingAppState):
    if event.payload:
        app_state.current_session.current_index = st.session_state[event.payload] - 1
    print(app_state.current_session.current_index)


def handle_brightness_changed(event: CompletedEvent, app_state: LabelingAppState):
    app_state.brightness = st.session_state[event.payload]


def handle_contrast_changed(event: CompletedEvent, app_state: LabelingAppState):
    app_state.contrast = st.session_state[event.payload]


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


def handle_prev_set(event: HalfEvent, app_state: LabelingAppState):
    app_state.session_index = (app_state.session_index - 1) % len(
        app_state.labeling_session
    )


def handle_region_selected(event: CompletedEvent, app_state: LabelingAppState):
    if event.payload:
        payload_content = st.session_state.get(event.payload)
    else:
        return
    img_session = app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ]

    if payload_content is None:
        img_session.region = Region.None_
        reset_score_fields(app_state, Region.None_)
        reset_score_fields_in_session(Region.None_)
        app_state.score_box_render_mode = Region.None_
    elif payload_content == "Basal Ganglia (Central)":
        img_session.region = Region.BasalCentral
        reset_score_fields(app_state, Region.BasalCentral)
        reset_score_fields_in_session(Region.BasalCentral)
        app_state.score_box_render_mode = Region.BasalCentral
    elif payload_content == "Basal Ganglia (Cortex)":
        img_session.region = Region.BasalCortex
        reset_score_fields(app_state, Region.BasalCortex)
        reset_score_fields_in_session(Region.BasalCortex)
        app_state.score_box_render_mode = Region.BasalCortex
    elif payload_content == "Corona Radiata":
        img_session.region = Region.CoronaRadiata
        reset_score_fields(app_state, Region.CoronaRadiata)
        reset_score_fields_in_session(Region.CoronaRadiata)
        app_state.score_box_render_mode = Region.CoronaRadiata

    update_unsatisfactory_sessions(app_state)


def handle_basal_central_left_score(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ].basal_score_central_left = st.session_state[event.payload]
    update_unsatisfactory_sessions(app_state)


def handle_basal_central_right_score(
    event: CompletedEvent, app_state: LabelingAppState
):
    app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ].basal_score_central_right = st.session_state[event.payload]
    update_unsatisfactory_sessions(app_state)


def handle_basal_cortex_left_score(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ].basal_score_cortex_left = st.session_state[event.payload]
    update_unsatisfactory_sessions(app_state)


def handle_basal_cortex_right_score(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ].basal_score_cortex_right = st.session_state[event.payload]
    update_unsatisfactory_sessions(app_state)


def handle_corona_left_score(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ].corona_score_left = st.session_state[event.payload]
    update_unsatisfactory_sessions(app_state)


def handle_corona_right_score(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.images_sessions[
        app_state.current_session.current_index
    ].corona_score_right = st.session_state[event.payload]
    update_unsatisfactory_sessions(app_state)


def handle_notes_changed(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.notes = st.session_state[event.payload]


def disable_score_fields(app_state: LabelingAppState):
    if (
        app_state.current_session.irrelevant_data
        or app_state.current_session.low_quality
    ):
        app_state.score_box_render_mode = None
    else:
        app_state.score_box_render_mode = Region.None_


def handle_mark_irrelevant(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.irrelevant_data = st.session_state[event.payload]
    if app_state.current_session.irrelevant_data:
        for img in app_state.current_session.images_sessions:
            img.region = Region.None_
            reset_score_fields(app_state, Region.None_)
            reset_score_fields_in_session(Region.None_)
    disable_score_fields(app_state)
    update_unsatisfactory_sessions(app_state)


def handle_mark_low_quality(event: CompletedEvent, app_state: LabelingAppState):
    app_state.current_session.low_quality = st.session_state[event.payload]
    if app_state.current_session.low_quality:
        for img in app_state.current_session.images_sessions:
            img.region = Region.None_
            reset_score_fields(app_state, Region.None_)
            reset_score_fields_in_session(Region.None_)
    disable_score_fields(app_state)
    update_unsatisfactory_sessions(app_state)


def handle_logout(event: HalfEvent, app_state: LabelingAppState):
    reset()


def handle_submit(event: HalfEvent, app_state: LabelingAppState):
    for image_set in app_state.labeling_session:
        submit_image_set_results(
            db_session=app_state.db_session,
            doctor_uuid=app_state.doctor_id,
            session_uuid=app_state.login_session,
            result=image_set,
        )


EVENT_DISPATCH: Dict[EventType, Callable] = {
    EventType.NEXT_IMAGE: handle_next_image,
    EventType.PREV_IMAGE: handle_prev_image,
    EventType.JUMP_TO_IMAGE: handle_jump_to_image,
    EventType.BRIGHTNESS_CHANGED: handle_brightness_changed,
    EventType.CONTRAST_CHANGED: handle_contrast_changed,
    EventType.RESET_ADJUSTMENTS: handle_reset_adjustments,
    EventType.NEXT_SET: handle_next_set,
    EventType.PREV_SET: handle_prev_set,
    EventType.REGION_SELECTED: handle_region_selected,
    EventType.BASAL_CENTRAL_LEFT_SCORE_CHANGED: handle_basal_central_left_score,
    EventType.BASAL_CENTRAL_RIGHT_SCORE_CHANGED: handle_basal_central_right_score,
    EventType.BASAL_CORTEX_LEFT_SCORE_CHANGED: handle_basal_cortex_left_score,
    EventType.BASAL_CORTEX_RIGHT_SCORE_CHANGED: handle_basal_cortex_right_score,
    EventType.CORONA_LEFT_SCORE_CHANGED: handle_corona_left_score,
    EventType.CORONA_RIGHT_SCORE_CHANGED: handle_corona_right_score,
    EventType.NOTES_CHANGED: handle_notes_changed,
    EventType.MARK_IRRELEVANT: handle_mark_irrelevant,
    EventType.MARK_LOW_QUALITY: handle_mark_low_quality,
    EventType.LOGOUT: handle_logout,
    EventType.SUBMIT: handle_submit,
}


def flag_listener(flag: EventFlags, app_state: LabelingAppState):
    """Process one event (if any) using the dispatch table."""
    event: Optional[Union[HalfEvent, CompletedEvent]] = flag.pop()
    if not event:
        return

    handler = EVENT_DISPATCH.get(event.type)
    if handler is not None:
        handler(event, app_state)
