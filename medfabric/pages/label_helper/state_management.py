# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
# medfabric/pages/label_helper/state_management.py
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
from typing import Optional, List, Union
import pandas as pd
from medfabric.pages.label_helper.session_initialization import (
    ImageSetEvaluationSession,
)
from medfabric.pages.label_helper.image_set_session_status import (
    create_set_status_dataframe,
)
from medfabric.api.config import DEFAULT_BRIGHTNESS, DEFAULT_CONTRAST


class EventType(Enum):
    """Types of user interaction events."""

    LOGIN = auto()
    # Image Controls
    NEXT_IMAGE = auto()
    PREV_IMAGE = auto()
    JUMP_TO_IMAGE = auto()
    # Set Controls
    NEXT_SET = auto()
    PREV_SET = auto()
    JUMP_TO_SET = auto()
    # Image Adjustments
    BRIGHTNESS_CHANGED = auto()
    CONTRAST_CHANGED = auto()
    FILTER_CHANGED = auto()
    RESET_ADJUSTMENTS = auto()
    # Region Selection
    WINDOWING_LEVEL_CHANGED = auto()
    WINDOWING_WIDTH_CHANGED = auto()
    RESET_WINDOWING = auto()

    REGION_SELECTED = auto()
    # Scoring Changes
    BASAL_CORTEX_LEFT_SCORE_CHANGED = auto()
    BASAL_CORTEX_RIGHT_SCORE_CHANGED = auto()
    BASAL_CENTRAL_LEFT_SCORE_CHANGED = auto()
    BASAL_CENTRAL_RIGHT_SCORE_CHANGED = auto()
    CORONA_LEFT_SCORE_CHANGED = auto()
    CORONA_RIGHT_SCORE_CHANGED = auto()
    NOTES_CHANGED = auto()
    # Set Markings
    MARK_IRRELEVANT_CHANGED = auto()
    MARK_LOW_QUALITY_CHANGED = auto()
    # Session Controls
    SAVE = auto()
    CANCEL = auto()
    SUBMIT = auto()
    LOGOUT = auto()


class FilterType(Enum):
    NONE = "None"
    GAUSSIAN = "Gaussian_Blur"
    SHARPEN = "Sharpen"
    EDGE_DETECTION = "Edge_Detect"


class UIElementType(Enum):
    BUTTON = "button"
    SLIDER = "slider"
    SELECTBOX = "selectbox"
    SEGMENTED_CONTROL = "segmented_control"
    NUMBER_INPUT = "number_input"
    TEXTAREA = "textarea"
    CHECKBOX = "checkbox"
    RADIO = "radio"


@dataclass(frozen=True)
class ParsedKey:
    element_type: UIElementType
    use: EventType | str
    uuid: Optional[str]


@dataclass
class LabelingAppState:
    """Class to hold the state of the labeling application."""

    labeling_session: List[ImageSetEvaluationSession]
    doctor_id: uuid_lib.UUID
    login_session: uuid_lib.UUID
    brightness: int = DEFAULT_BRIGHTNESS
    contrast: float = DEFAULT_CONTRAST
    filter_type: FilterType = FilterType.NONE
    session_index: int = 0
    set_status_df: pd.DataFrame = field(default_factory=create_set_status_dataframe)
    all_sessions_satisfactory: bool = False

    @property
    def current_session(self) -> ImageSetEvaluationSession:
        return self.labeling_session[self.session_index]


@dataclass
class CompletedEvent:
    """A user interaction event with optional payload.
    Payload is the key of the interacted element."""

    type: EventType
    payload: str


@dataclass
class HalfEvent:
    """A user interaction event with optional payload."""

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
    """Key manager aware of enums (UIElementType + EventType)."""

    separator: str = "_"

    def make(
        self,
        element_type: UIElementType,
        use: EventType | str,
        obj_uuid: Optional[str | uuid_lib.UUID] = None,
    ) -> str:
        """Generate a key string using enums or strings."""
        if isinstance(obj_uuid, uuid_lib.UUID):
            obj_uuid = str(obj_uuid)
        use_val = use.name if isinstance(use, EventType) else str(use)
        return f"{element_type.value}{self.separator}{use_val}" + (
            f"{self.separator}{obj_uuid}" if obj_uuid else ""
        )

    def parse(self, key: str) -> ParsedKey:
        """Parse a key string into its components."""
        parts = key.split(self.separator)

        # Validate element type
        try:
            element_type = UIElementType(parts[0])
        except ValueError as e:
            raise ValueError(f"Unknown UIElementType: {parts[0]}") from e

        # Validate event type
        try:
            use = EventType[parts[1]]
        except KeyError as e1:
            raise ValueError(f"Unknown EventType: {parts[1]}") from e1

        # UUID is optional
        uuid = parts[2] if len(parts) == 3 else None

        return ParsedKey(element_type=element_type, use=use, uuid=uuid)


def raise_flag(
    flag: EventFlags,
    event_type: EventType,
    payload: Optional[str] = None,
):

    if payload is None:
        flag.push(HalfEvent(type=event_type))
    else:
        flag.push(CompletedEvent(type=event_type, payload=payload))
    # print(flag._queue)
