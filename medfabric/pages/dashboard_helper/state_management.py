# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
import uuid as uuid_lib
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Union
import pandas as pd


class EventType(Enum):
    EDIT_SELECTION = auto()
    EVALUATE_SELECTED_SCANS = auto()
    LOGOUT = auto()


class UIElementType(Enum):
    BUTTON = "button"
    DATA_EDITOR = "data_editor"


@dataclass(frozen=True)
class ParsedKey:
    element_type: UIElementType
    use: EventType | str
    uuid: Optional[str]


@dataclass
class DashboardAppState:
    doctor_uuid: uuid_lib.UUID
    all_sets_df: pd.DataFrame
    dataset_evaluated_count: int
    dataset_total_count: int
    dataset_progress: float
    evaluated_count: int
    total_count: int
    progress: float
    selected_scan_uuids: List[uuid_lib.UUID] = field(default_factory=list)


@dataclass
class CompletedEvent:
    type: EventType
    payload: str


@dataclass
class HalfEvent:
    type: EventType


class EventFlags:
    def __init__(self):
        self._queue: List[Union[HalfEvent, CompletedEvent]] = []

    def push(self, event: Union[HalfEvent, CompletedEvent]):
        self._queue.append(event)

    def pop(self) -> Optional[Union[HalfEvent, CompletedEvent]]:
        return self._queue.pop(0) if self._queue else None

    def has_events(self) -> bool:
        return bool(self._queue)

    def clear(self):
        self._queue.clear()


@dataclass(frozen=True)
class EnumKeyManager:
    separator: str = "_"

    def make(
        self,
        element_type: UIElementType,
        use: EventType | str,
        obj_uuid: Optional[str | uuid_lib.UUID] = None,
    ) -> str:
        if isinstance(obj_uuid, uuid_lib.UUID):
            obj_uuid = str(obj_uuid)
        use_val = use.name if isinstance(use, EventType) else str(use)
        return f"{element_type.value}{self.separator}{use_val}" + (
            f"{self.separator}{obj_uuid}" if obj_uuid else ""
        )

    def parse(self, key: str) -> ParsedKey:
        parts = key.split(self.separator)

        try:
            element_type = UIElementType(parts[0])
        except ValueError as exc:
            raise ValueError(f"Unknown UIElementType: {parts[0]}") from exc

        try:
            use = EventType[parts[1]]
        except KeyError as exc:
            raise ValueError(f"Unknown EventType: {parts[1]}") from exc

        obj_uuid = parts[2] if len(parts) == 3 else None
        return ParsedKey(element_type=element_type, use=use, uuid=obj_uuid)


def raise_flag(
    flag: EventFlags,
    event_type: EventType,
    payload: Optional[str] = None,
):
    if payload is None:
        flag.push(HalfEvent(type=event_type))
    else:
        flag.push(CompletedEvent(type=event_type, payload=payload))
