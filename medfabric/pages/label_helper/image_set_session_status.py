import pandas as pd
import uuid
from enum import Enum


# Enum for status
class SetStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"


# Initialize empty DataFrame
def create_set_status_dataframe() -> pd.DataFrame:
    return pd.DataFrame(columns=["index", "set_uuid", "status"])


def add_row(df: pd.DataFrame, set_uuid: uuid.UUID, status: SetStatus) -> pd.DataFrame:
    """Add a new row with auto-increment index, UUID, and status (enum)."""
    if not isinstance(set_uuid, uuid.UUID):
        raise TypeError("set_uuid must be a uuid.UUID")

    next_index = 0 if df.empty else df["index"].max() + 1
    new_row = {"index": next_index, "set_uuid": str(set_uuid), "status": status.value}
    return pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)


def mark_status(
    df: pd.DataFrame, set_uuid: uuid.UUID, status: SetStatus
) -> pd.DataFrame:
    """Update status for a given set_uuid (UUID + enum)."""
    if not isinstance(set_uuid, uuid.UUID):
        raise TypeError("set_uuid must be a uuid.UUID")

    df.loc[df["set_uuid"] == str(set_uuid), "status"] = status.value
    return df


def get_invalid_indices(df: pd.DataFrame) -> list[int]:
    """Return indices of rows with INVALID status."""
    return df.loc[df["status"] == SetStatus.INVALID.value, "index"].tolist()


if __name__ == "__main__":
    df = create_set_status_dataframe()
    # Add new rows
    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    df = add_row(df, id1, SetStatus.VALID)
    df = add_row(df, id2, SetStatus.INVALID)

    # Mark status
    df = mark_status(df, id1, SetStatus.INVALID)

    # Get invalid indices
    print(df)
    print("Invalid indices:", get_invalid_indices(df))
