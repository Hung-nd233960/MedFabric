from pathlib import Path
import uuid as uuid_lib
import pandas as pd
from medfabric.db.engine_without_st import get_session_factory_bare
from medfabric.api.data_sets import add_data_set
from medfabric.api.patients import add_patient
from medfabric.api.image_set_input import add_image_set
from medfabric.api.image_input import add_image


def import_dataset_to_db(export_path: Path, data_path: Path):
    """
    Import exported dataset folders into the database.
    - Reads datasets.csv from export_path
    - Each dataset has its own subfolder with patients.csv, image_sets.csv, images.csv
    - data_path is used for folder_path in image_sets (where real image folders live)
    """

    Session = get_session_factory_bare()
    session = Session()

    # --- Load datasets.csv ---
    datasets_df = pd.read_csv(export_path / "datasets.csv")
    dataset_map = {
        row["name"]: uuid_lib.UUID(str(row["uuid"]).strip())
        for _, row in datasets_df.iterrows()
    }

    for name, uuid in dataset_map.items():
        add_data_set(session, name=name, dataset_uuid=uuid)
        print(f"📁 Added dataset: {name} ({uuid})")

    # --- Loop over each dataset folder in export_path ---
    for dataset_dir in export_path.iterdir():
        if not dataset_dir.is_dir():
            continue

        dataset_name = dataset_dir.name
        current_dataset_uuid = dataset_map.get(dataset_name)

        if current_dataset_uuid is None:
            print(f"⚠️ Warning: Dataset '{dataset_name}' not in datasets.csv")
            continue

        print(f"\nProcessing dataset folder: {dataset_name}")

        # --- Patients ---
        patients_df = pd.read_csv(dataset_dir / "patients.csv")
        patient_map = {}
        for _, p_row in patients_df.iterrows():
            patient_uuid = uuid_lib.UUID(str(p_row["uuid"]).strip())
            patient_id = str(p_row["patient_id"]).strip()

            add_patient(
                session,
                patient_uuid=patient_uuid,
                patient_id=patient_id,
                data_set_uuid=current_dataset_uuid,
            )
            patient_map[str(patient_uuid)] = patient_id
            print(f"  👤 Added patient: {patient_id} ({patient_uuid})")

        # --- Image Sets ---
        image_sets_df = pd.read_csv(dataset_dir / "image_sets.csv")
        for _, is_row in image_sets_df.iterrows():
            patient_uuid_str = str(is_row["patient_uuid"]).strip()
            patient_id = patient_map.get(patient_uuid_str)

            if not patient_id:
                print(f"  ⚠️ No patient_id for patient_uuid {patient_uuid_str}")
                continue

            image_set_uuid = uuid_lib.UUID(str(is_row["uuid"]).strip())
            image_set_name = is_row["image_set_name"]

            # folder_path is built from data_path, not export_path
            folder_path = str(data_path / dataset_name / patient_id / image_set_name)

            add_image_set(
                session,
                image_set_uuid=image_set_uuid,
                image_set_name=image_set_name,
                patient_uuid=uuid_lib.UUID(patient_uuid_str),
                num_images=int(is_row["num_images"]),
                dataset_uuid=current_dataset_uuid,
                folder_path=folder_path,
            )
            print(f"  📑 Added image set: {image_set_name} ({image_set_uuid})")

        # --- Images ---
        images_df = pd.read_csv(dataset_dir / "images.csv")
        images_df["slice_index"] = pd.to_numeric(
            images_df["slice_index"], errors="coerce"
        )
        images_df = images_df.sort_values("slice_index", ascending=True)

        for _, img_row in images_df.iterrows():
            raw_index = img_row["slice_index"]
            slice_index = (
                int(raw_index) - 1 if pd.notna(raw_index) and raw_index >= 0 else -1
            )

            image_uuid = uuid_lib.UUID(str(img_row["uuid"]).strip())
            image_set_uuid = uuid_lib.UUID(str(img_row["image_set_uuid"]).strip())

            add_image(
                session,
                image_uuid=image_uuid,
                image_name=img_row["image_name"],
                image_set_uuid=image_set_uuid,
                slice_index=slice_index,
            )
            print(
                f"    🖼️ Added image: {img_row['image_name']} "
                f"({image_uuid}, slice_index={slice_index})"
            )

    # --- Commit ---
    session.commit()
    print("\n✅ Import complete!")


if __name__ == "__main__":
    import_dataset_to_db(Path("exported_data_sets"), Path("data_sets"))
