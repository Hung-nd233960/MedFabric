import uuid
from enum import Enum
import pandas as pd
from medfabric.db.orm_model import Region


# Enum for slice status
class SliceStatus(str, Enum):
    COMPLETED = "COMPLETED"
    INCOMPLETED = "INCOMPLETED"


def initialize_slice_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["slice_index", "image_uuid", "region", "status"])


def _reorder_slices(df: pd.DataFrame) -> pd.DataFrame:
    """Sort slices by slice_index but preserve original values."""
    return df.sort_values("slice_index")


def add_slice(
    df: pd.DataFrame,
    slice_index: int,
    image_uuid: uuid.UUID,
    region: Region,
    status: SliceStatus = SliceStatus.INCOMPLETED,
) -> pd.DataFrame:
    """Add a new slice row and keep slice_index ordered."""
    if not isinstance(image_uuid, uuid.UUID):
        raise TypeError("image_uuid must be a uuid.UUID")

    new_row = {
        "slice_index": slice_index + 1,
        "image_uuid": str(image_uuid),
        "region": region.value,
        "status": status.value,
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return _reorder_slices(df)


def delete_slice(df: pd.DataFrame, image_uuid: uuid.UUID) -> pd.DataFrame:
    """Delete a slice row based on image_uuid."""
    if not isinstance(image_uuid, uuid.UUID):
        raise TypeError("image_uuid must be a uuid.UUID")

    df = df[df["image_uuid"] != str(image_uuid)]
    return _reorder_slices(df)


def modify_status(
    df: pd.DataFrame, image_uuid: uuid.UUID, status: SliceStatus
) -> pd.DataFrame:
    """Modify status for a given image_uuid."""
    if not isinstance(image_uuid, uuid.UUID):
        raise TypeError("image_uuid must be a uuid.UUID")

    df.loc[df["image_uuid"] == str(image_uuid), "status"] = status.value
    return df


def modify_region(
    df: pd.DataFrame, image_uuid: uuid.UUID, region: Region
) -> pd.DataFrame:
    """Modify region for a given image_uuid."""
    if not isinstance(image_uuid, uuid.UUID):
        raise TypeError("image_uuid must be a uuid.UUID")

    df.loc[df["image_uuid"] == str(image_uuid), "region"] = region.value
    return df


def has_required_regions(df: pd.DataFrame) -> bool:
    """Check if all required regions (except None_) are present in df."""
    required_regions = {
        Region.BasalCentral.value,
        Region.BasalCortex.value,
        Region.CoronaRadiata.value,
    }
    regions_present = set(df["region"].unique())
    return required_regions.issubset(regions_present)


def all_completed(df: pd.DataFrame) -> bool:
    """Check if all rows have status COMPLETED."""
    return bool((df["status"] == SliceStatus.COMPLETED.value).all())


def validate_slices(df: pd.DataFrame) -> bool:
    """Return True if df has required regions and all rows completed."""
    return bool(has_required_regions(df) and all_completed(df))


def consecutive_slices(df: pd.DataFrame) -> bool:
    """
    Return True if df is not empty and `slice_index` values are consecutive integers.
    """
    if df.empty:
        return True
    if "slice_index" not in df.columns:
        raise ValueError("DataFrame must contain a 'slice_index' column")

    values = df["slice_index"].sort_values().to_numpy()
    return (values[-1] - values[0] + 1) == len(values) and len(set(values)) == len(
        values
    )


def clear_all_slices() -> pd.DataFrame:
    """Return an empty DataFrame with the correct columns."""
    return initialize_slice_df()


def handle_df_region_change(
    df: pd.DataFrame,
    slice_index: int,
    image_uuid: uuid.UUID,
    new_region: Region,
    status: SliceStatus = SliceStatus.INCOMPLETED,
) -> pd.DataFrame:
    """
    Update region if image_uuid exists, else create a new slice.
    Note: status is only applied when creating a new slice.
    """
    if not isinstance(image_uuid, uuid.UUID):
        raise TypeError("image_uuid must be a uuid.UUID")

    mask = df["image_uuid"] == str(image_uuid)
    if mask.any():
        # UUID already exists → update region only
        df.loc[mask, "region"] = new_region.value
    else:
        # UUID not found → add new slice (region + initial status)
        new_row = {
            "slice_index": slice_index + 1,
            "image_uuid": str(image_uuid),
            "region": new_region.value,
            "status": status.value,
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df = _reorder_slices(df)

    return df


if __name__ == "__main__":
    img1 = uuid.uuid4()
    img2 = uuid.uuid4()
    img3 = uuid.uuid4()
    slices_df = initialize_slice_df()
    # Add slices
    slices_df = add_slice(
        slices_df, 0, img1, Region.BasalCentral, SliceStatus.INCOMPLETED
    )
    slices_df = add_slice(slices_df, 1, img2, Region.BasalCortex, SliceStatus.COMPLETED)
    slices_df = add_slice(
        slices_df, 2, img3, Region.CoronaRadiata, SliceStatus.INCOMPLETED
    )

    # Modify
    slices_df = modify_status(slices_df, img1, SliceStatus.COMPLETED)
    slices_df = modify_region(slices_df, img3, Region.BasalCentral)

    # Delete
    slices_df = delete_slice(slices_df, img2)

    print(slices_df)

    slices_df = pd.DataFrame(
        [
            {
                "slice_index": 0,
                "image_uuid": str(uuid.uuid4()),
                "region": Region.BasalCentral.value,
                "status": SliceStatus.COMPLETED.value,
            },
            {
                "slice_index": 1,
                "image_uuid": str(uuid.uuid4()),
                "region": Region.BasalCortex.value,
                "status": SliceStatus.COMPLETED.value,
            },
            {
                "slice_index": 2,
                "image_uuid": str(uuid.uuid4()),
                "region": Region.CoronaRadiata.value,
                "status": SliceStatus.COMPLETED.value,
            },
        ]
    )

    print("Has required regions:", has_required_regions(slices_df))  # ✅ True
    print("All completed:", all_completed(slices_df))  # ✅ True
    print("Validation result:", validate_slices(slices_df))  # ✅ True
