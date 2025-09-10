import os
import pandas as pd
from medfabric.api.image_set_input import get_image_set_by_id_and_patient
from medfabric.api.utils.image_set_path_updater import update_image_set_folder_path
from medfabric.db.database import Session
from pathlib import Path

dataset_base_path = Path("public_data/data/")


def build_image_set_manifest(
    db_session, output_csv="image_set_manifest.csv", base_path=dataset_base_path
):
    records = []
    print(Path.cwd)
    # base_path = Path.cwd() / dataset_base_path
    # base_path = base_path.resolve()
    print(f"🔍 Scanning base path: {base_path}")
    for patient_id in os.listdir(base_path):
        patient_folder = os.path.join(base_path, patient_id)
        if not os.path.isdir(patient_folder):
            continue

        for image_set_id in os.listdir(patient_folder):
            set_folder = os.path.join(patient_folder, image_set_id)
            if not os.path.isdir(set_folder):
                continue

            try:
                image_set_uuid = get_image_set_by_id_and_patient(
                    db_session, image_set_id=image_set_id, patient_id=patient_id
                )
            except Exception as e:
                print(f"⚠️ No DB match for {patient_id}/{image_set_id}: {e}")
                image_set_uuid = None

            records.append(
                {
                    "patient_id": patient_id,
                    "image_set_id": image_set_id,
                    "image_set_uuid": str(image_set_uuid) if image_set_uuid else "",
                    "path": set_folder,
                }
            )

    # Convert to DataFrame
    df = pd.DataFrame(
        records, columns=["patient_id", "image_set_id", "image_set_uuid", "path"]
    )

    # Save to CSV
    df.to_csv(output_csv, index=False)

    print(f"✅ Manifest written to {output_csv} with {len(df)} entries")
    return df


def update_path_to_db(
    db_session, manifest_csv="public_data/eda_public_data/image_set_manifest.csv"
):
    """
    Update DB image_set.folder_path from a manifest CSV.

    Args:
        db_session: SQLAlchemy session object.
        manifest_csv: Path to manifest CSV with columns
                      [patient_id, image_set_id, image_set_uuid, path]
    """
    df = pd.read_csv(manifest_csv)

    updated, failed = 0, 0

    for _, row in df.iterrows():
        try:
            update_image_set_folder_path(
                db_session,
                image_set_uuid=row["image_set_uuid"],
                folder_path=row["path"],
            )
            updated += 1
        except Exception as e:
            print(
                f"❌ Failed to update {row['image_set_id']} ({row['patient_id']}): {e}"
            )
            failed += 1

    db_session.commit()
    print(f"✅ Updated {updated} image sets. ❌ Failed: {failed}")


if __name__ == "__main__":
    with Session() as db_session:
        #    build_image_set_manifest(db_session)
        update_path_to_db(db_session)
