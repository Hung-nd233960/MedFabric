# medfabric/pages/core/pages.py
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, TypeVar, Callable, Generic, Dict, Type

from medfabric.pages.core.enum_key_manager import EnumKeyManager, Key
from medfabric.pages.core.queue_manager import EventQueue, Event


# Generic type for event enums
EventTypeVar = TypeVar("EventTypeVar", bound=Enum)


class BasePage(Generic[EventTypeVar], ABC):
    # Subclasses must override this with their specific Enum type
    EventType: Type[EventTypeVar]

    def __init__(self):
        if not hasattr(self, "EventType") or self.EventType is None:
            raise ValueError("Each Page must define its own EventType enum")

        # Page-specific event system
        self.event_queue: EventQueue[EventTypeVar] = EventQueue()
        self.key_manager = EnumKeyManager(use_enum=self.EventType)

        # Maps events -> handler functions
        self.dispatch_table: Dict[
            EventTypeVar, Callable[[Event[EventTypeVar]], None]
        ] = {}

    # --- Event System ---
    def raise_event(self, event_type: EventTypeVar, payload: Optional[Key] = None):
        """Add a new event to the queue."""
        if not isinstance(event_type, self.EventType):
            raise ValueError(f"Unknown event type: {event_type}")
        event = Event(type_=event_type, payload=payload)
        self.event_queue.push(event)

    def listen_events(self):
        """Process all queued events through dispatch table."""
        while self.event_queue.has_events():
            event = self.event_queue.pop()
            if event is None:
                continue
            handler = self.dispatch_table.get(event.type_)
            self.event_queue.clear()  # Clear intermediate events
            if handler:
                handler(event)

    # --- Abstracts for Pages to implement ---
    @abstractmethod
    def setup_dispatch_table(self) -> None:
        """Each page defines its own event handlers."""

    @abstractmethod
    def render(self) -> None:
        """Page UI goes here."""


## # Example Page Implementation
# class ImagePage(BasePage):
#     class EventType(Enum):
#         NEXT_IMAGE = "NEXT_IMAGE"
#         PREV_IMAGE = "PREV_IMAGE"
#         SUBMIT = "SUBMIT"

#     EventType = EventType  # bind the enum

#     def __init__(self, state):
#         super().__init__()
#         self.state = state
#         self.setup_dispatch_table()

#     def setup_dispatch_table(self):
#         self.dispatch_table = {
#             self.EventType.NEXT_IMAGE: self.handle_next,
#             self.EventType.PREV_IMAGE: self.handle_prev,
#             self.EventType.SUBMIT: self.handle_submit,
#         }

#     # --- Handlers ---
#     def handle_next(self, event):
#         session = self.state.current_session
#         session.current_index = (session.current_index + 1) % session.num_images

#     def handle_prev(self, event):
#         session = self.state.current_session
#         session.current_index = (session.current_index - 1) % session.num_images

#     def handle_submit(self, event):
#         print("Submitting session...")

#    # --- UI ---
#    def render(self):
#        import streamlit as st
#
#        if st.button("Next"):
#            self.raise_event(self.EventType.NEXT_IMAGE)
#
#       if st.button("Prev"):
#            self.raise_event(self.EventType.PREV_IMAGE)
#
#
#         if st.button("Submit"):
#            self.raise_event(self.EventType.SUBMIT)
#
#        # Process any raised events
#        self.listen_events()
