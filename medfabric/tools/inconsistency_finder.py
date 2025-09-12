import pandas as pd
from pathlib import Path


def check_slice_index_from_csv(dataset_export_dir: Path) -> pd.DataFrame:
    """
    Check image sets for slice_index inconsistencies using exported CSVs.
    Returns DataFrame of inconsistent image sets.
    """

    # Load the CSVs
    image_sets_df = pd.read_csv(dataset_export_dir / "image_sets.csv")
    images_df = pd.read_csv(dataset_export_dir / "images.csv")

    # Compute max slice_index per image set
    # Compute max slice_index per image_set
    max_slice_df = (
        images_df.groupby("image_set_uuid")["slice_index"].max().reset_index()
    )
    max_slice_df.rename(columns={"slice_index": "max_slice_index"}, inplace=True)

    # Merge with image_sets: image_sets.uuid <-> images.image_set_uuid
    merged_df = pd.merge(
        image_sets_df,
        max_slice_df,
        left_on="uuid",  # column in image_sets.csv
        right_on="image_set_uuid",  # column in images.csv
    )

    # Find inconsistent sets
    inconsistent_df = merged_df[merged_df["max_slice_index"] > merged_df["num_images"]]

    # Optional: print a simple report
    for _, row in inconsistent_df.iterrows():
        print(
            f"Inconsistent image set '{row.image_set_name}' "
            f"(patient {row.patient_uuid}): max slice_index = {row.max_slice_index}, "
            f"num_images = {row.num_images}"
        )

    return inconsistent_df


def remove_inconsistent_image_sets(
    dataset_export_dir: Path, inconsistent_df: pd.DataFrame
) -> None:
    """
    Remove image sets listed in inconsistent_df and their images from CSVs.
    Overwrites images.csv and image_sets.csv in dataset_export_dir.
    """

    if inconsistent_df.empty:
        print("No inconsistent image sets to remove.")
        return

    # Load CSVs
    image_sets_df = pd.read_csv(dataset_export_dir / "image_sets.csv")
    images_df = pd.read_csv(dataset_export_dir / "images.csv")

    # Get list of bad image_set UUIDs
    bad_image_set_uuids = inconsistent_df["uuid"].tolist()

    # Filter out bad image sets
    image_sets_df_clean = image_sets_df[
        ~image_sets_df["uuid"].isin(bad_image_set_uuids)
    ]
    images_df_clean = images_df[~images_df["image_set_uuid"].isin(bad_image_set_uuids)]

    # Overwrite CSVs
    image_sets_df_clean.to_csv(dataset_export_dir / "image_sets.csv", index=False)
    images_df_clean.to_csv(dataset_export_dir / "images.csv", index=False)

    print(
        f"Removed {len(bad_image_set_uuids)} inconsistent image sets and their images from {dataset_export_dir.name}"
    )


if __name__ == "__main__":
    data_set_path = Path("").resolve()
    check_slice_index_from_csv(data_set_path / "exported_data_sets" / "public_dev")
    remove_inconsistent_image_sets(
        data_set_path / "exported_data_sets" / "png_data",
        check_slice_index_from_csv(data_set_path / "exported_data_sets" / "public_dev"),
    )
