from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Optional, TypeVar, Generic
from medfabric.pages.core.enum_key_manager import Key

EventTypeVar = TypeVar("EventTypeVar", bound=Enum)


@dataclass(frozen=True)
class Event(Generic[EventTypeVar]):
    """A user interaction event."""

    type_: EventTypeVar
    payload: Optional[Key] = None


class EventQueue(Generic[EventTypeVar]):
    """FIFO queue for events in a page."""

    def __init__(self):
        self._queue: deque[Event[EventTypeVar]] = deque()

    def push(self, event: Event[EventTypeVar]) -> None:
        """Add a new event to the queue."""
        self._queue.append(event)

    def pop(self) -> Optional[Event[EventTypeVar]]:
        """Get and remove the next event (if any)."""
        return self._queue.popleft() if self._queue else None

    def peek(self) -> Optional[Event[EventTypeVar]]:
        """Look at the next event without removing it."""
        return self._queue[0] if self._queue else None

    def clear(self) -> None:
        """Remove all events."""
        self._queue.clear()

    def has_events(self) -> bool:
        return bool(self._queue)

    def __len__(self) -> int:
        return len(self._queue)
