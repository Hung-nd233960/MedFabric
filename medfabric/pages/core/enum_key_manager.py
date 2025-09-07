# pylint: disable=missing-class-docstring,missing-function-docstring,missing-module-docstring
# medfabric/pages/core/enum_key_manager.py
from dataclasses import dataclass, field
from enum import Enum
import uuid as uuid_lib
from typing import Optional, Type, TypeVar, Generic

EventTypeVar = TypeVar("EventTypeVar", bound=Enum)


class UIElementType(Enum):
    """Defines types of UI elements."""

    BUTTON = "button"
    SLIDER = "slider"
    SELECTBOX = "selectbox"
    SEGMENTED_CONTROL = "segmented_control"
    NUMBER_INPUT = "number_input"
    TEXTAREA = "textarea"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    DATA_EDITOR = "data_editor"


@dataclass(frozen=True)
class Key(Generic[EventTypeVar]):
    """Unique key object for Streamlit widgets, round-trippable."""

    element_type: UIElementType
    use: EventTypeVar
    uuid: Optional[uuid_lib.UUID] = None
    separator: str = "_"

    def __str__(self) -> str:
        """String form (Streamlit-compatible)."""
        use_val = self.use.name if isinstance(self.use, Enum) else str(self.use)
        return f"{self.element_type.value}{self.separator}{use_val}" + (
            f"{self.separator}{self.uuid}" if self.uuid else ""
        )

    @classmethod
    def from_str(
        cls, key_str: str, event_enum: Type[EventTypeVar], sep: str = "_"
    ) -> "Key[EventTypeVar]":
        """Parse from string back into a Key object."""

        parts = key_str.split(sep)

        # Validate element type
        try:
            element_type = UIElementType(parts[0])
        except ValueError as e:
            raise ValueError(f"Unknown UIElementType: {parts[0]}") from e

        try:
            use = event_enum[parts[1]]
        except KeyError as e1:
            raise ValueError(f"Unknown EventType: {parts[1]}") from e1

        # UUID is optional
        uuid_str = parts[2] if len(parts) == 3 else None
        uuid = uuid_lib.UUID(uuid_str) if uuid_str else None

        return cls(element_type=element_type, use=use, uuid=uuid, separator=sep)


@dataclass
class EnumKeyManager(Generic[EventTypeVar]):
    """Manages unique keys for one EventType enum."""

    use_enum: Type[EventTypeVar]
    separator: str = "_"
    _registry: set[Key[EventTypeVar]] = field(
        default_factory=set, init=False, repr=False
    )

    def make(
        self,
        element_type: UIElementType,
        use: EventTypeVar,
        obj_uuid: Optional[uuid_lib.UUID] = None,
    ) -> Key[EventTypeVar]:
        """Create and register a new Key."""
        key = Key(element_type, use, obj_uuid, separator=self.separator)
        self._registry.add(key)
        return key

    def parse(self, key_str: str) -> Key[EventTypeVar]:
        """Parse string back into Key."""
        return Key.from_str(key_str, self.use_enum, self.separator)

    def all_keys(self) -> frozenset[Key[EventTypeVar]]:
        return frozenset(self._registry)

    def clear(self):
        """Clear registry of tracked keys."""
        self._registry.clear()
