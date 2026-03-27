# pylint: disable=missing-module-docstring, missing-function-docstring
from typing import Callable, Dict, Optional, Union
import streamlit as st
from medfabric.pages.utils import reset
from medfabric.pages.dashboard_helper.state_management import (
    DashboardAppState,
    EventFlags,
    EventType,
    HalfEvent,
    CompletedEvent,
)


def handle_logout(_event: HalfEvent, _app_state: DashboardAppState):
    reset()


def handle_evaluate_selected_scans(_event: HalfEvent, app_state: DashboardAppState):
    if not app_state.selected_scan_uuids:
        st.warning("Please select at least one scan for evaluation.")
        return

    st.session_state.selected_scans = app_state.selected_scan_uuids.copy()
    st.switch_page("pages/label.py")


EVENT_DISPATCH: Dict[EventType, Callable] = {
    EventType.LOGOUT: handle_logout,
    EventType.EVALUATE_SELECTED_SCANS: handle_evaluate_selected_scans,
}


def flag_listener(flag: EventFlags, app_state: DashboardAppState):
    event: Optional[Union[HalfEvent, CompletedEvent]] = flag.pop()
    flag.clear()
    if not event:
        return

    handler = EVENT_DISPATCH.get(event.type)
    if handler is not None:
        handler(event, app_state)
