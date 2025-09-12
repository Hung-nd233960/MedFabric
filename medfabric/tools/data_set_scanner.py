from pathlib import Path
import re
import uuid as uuid_lib
import pandas as pd
import pydicom


class ImageFileFormatError(Exception):
    """Custom exception for image file format errors."""


data_set_path_str: str = "data_sets/"
data_set_path: Path = Path(data_set_path_str).resolve()


data_set_df = pd.DataFrame(
    columns=[
        "index",
        "name",
        "uuid",
        "num_image_sets",
        "num_patients",
        "description",
    ]
)
data_set_df.set_index("index", inplace=True)


image_sets_df_framework = pd.DataFrame(
    columns=[
        "index",
        "uuid",
        "image_set_name",
        "patient_id",
        "num_images",
    ]
)
patients_df_framework = pd.DataFrame(
    columns=[
        "patient_id",
        "patient_uuid",
    ]
)
images_df_framework = pd.DataFrame(
    columns=[
        "uuid",
        "image_name",
        "image_set_uuid",
        "slice_index",
    ]
)


def extract_slice_index(file_path: Path) -> int:
    """Extract slice index from image file."""
    ext = file_path.suffix.lower()

    if ext == ".dcm":
        ds = pydicom.dcmread(str(file_path), stop_before_pixels=True)
        if hasattr(ds, "InstanceNumber"):
            return int(ds.InstanceNumber)
        if hasattr(ds, "SliceLocation"):
            return int(float(ds.SliceLocation))
        raise ImageFileFormatError(f"No slice index in {file_path}")

    if ext in (".png", ".jpg", ".jpeg"):
        name = file_path.stem
        m1 = re.fullmatch(r"(\d+)(?:[-_].+)?", name)
        if not m1:
            raise ImageFileFormatError(f"Invalid image filename: {file_path}")
        return int(m1.group(1).lstrip("0") or "0")

    raise ImageFileFormatError(f"Unsupported file type: {file_path}")


def analyze_and_export_data_sets_verbose(
    data_set_path: Path,
    export_path: Path,
) -> None:
    """
    Analyze datasets and export CSVs deterministically, with verbose progress output.
    """

    export_path.mkdir(parents=True, exist_ok=True)
    datasets_rows = []

    dataset_uuid_map = {}
    patient_uuid_map = {}
    image_set_uuid_map = {}

    print(f"Scanning datasets in {data_set_path}...")

    for data_set_dir in data_set_path.iterdir():
        if not data_set_dir.is_dir():
            continue

        data_set_name = data_set_dir.name
        data_set_uuid = uuid_lib.uuid4()
        dataset_uuid_map[data_set_name] = data_set_uuid
        datasets_rows.append({"name": data_set_name, "uuid": str(data_set_uuid)})

        print(f"\nProcessing dataset '{data_set_name}' (UUID: {data_set_uuid})...")
        dataset_export_dir = export_path / data_set_name
        dataset_export_dir.mkdir(exist_ok=True)

        patients_rows = []
        image_sets_rows = []
        images_rows = []

        for patient_dir in data_set_dir.iterdir():
            if not patient_dir.is_dir():
                continue
            patient_id = patient_dir.name
            patient_uuid = uuid_lib.uuid4()
            patient_uuid_map[patient_id] = patient_uuid
            patients_rows.append({"patient_id": patient_id, "uuid": str(patient_uuid)})

            print(f"  Patient '{patient_id}' (UUID: {patient_uuid})...")

            for image_set_dir in patient_dir.iterdir():
                if not image_set_dir.is_dir():
                    continue
                image_set_name = image_set_dir.name
                key = f"{data_set_name}/{patient_id}/{image_set_name}"
                image_set_uuid = uuid_lib.uuid4()
                image_set_uuid_map[key] = image_set_uuid

                image_files = [f for f in image_set_dir.iterdir() if f.is_file()]
                num_images = len(image_files)

                image_sets_rows.append(
                    {
                        "uuid": str(image_set_uuid),
                        "image_set_name": image_set_name,
                        "patient_uuid": str(patient_uuid),
                        "num_images": num_images,
                    }
                )

                print(
                    f"    Image set '{image_set_name}' (UUID: {image_set_uuid}) with {num_images} images..."
                )

                # Process images grouped by image_set_uuid
                images_rows_temp = []
                for image_file in image_files:
                    try:
                        slice_index = extract_slice_index(image_file)
                    except ImageFileFormatError:
                        slice_index = -1  # fallback
                        print(
                            f"      Warning: Could not extract slice_index for {image_file}, using -1"
                        )
                    rel_path = image_file.relative_to(
                        data_set_path
                    )  # relative inside dataset root
                    key = f"{data_set_name}/{rel_path.as_posix()}"
                    image_uuid = uuid_lib.uuid4()
                    images_rows_temp.append(
                        {
                            "uuid": str(image_uuid),
                            "image_name": image_file.name,
                            "image_set_uuid": str(image_set_uuid),
                            "slice_index": slice_index,
                        }
                    )

                    print(
                        f"      Image '{image_file.name}' (UUID: {image_uuid}, slice_index: {slice_index})"
                    )

                # Sort images **inside this image_set group** by slice_index
                images_rows.extend(
                    sorted(images_rows_temp, key=lambda x: x["slice_index"])
                )

        # Export per-dataset CSVs
        pd.DataFrame(patients_rows).to_csv(
            dataset_export_dir / "patients.csv", index=False
        )
        pd.DataFrame(image_sets_rows).to_csv(
            dataset_export_dir / "image_sets.csv", index=False
        )
        pd.DataFrame(images_rows).to_csv(dataset_export_dir / "images.csv", index=False)

        print(f"  Exported CSVs for dataset '{data_set_name}'")

    # Export datasets.csv
    pd.DataFrame(datasets_rows).to_csv(export_path / "datasets.csv", index=False)
    print(f"\nDeterministic export complete to {export_path}")


if __name__ == "__main__":
    analyze_and_export_data_sets_verbose(
        data_set_path=data_set_path,
        export_path=Path("exported_data_sets").resolve(),
    )
