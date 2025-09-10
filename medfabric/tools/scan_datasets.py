# medfabric/tools/scan_datasets.py
import sys
from pathlib import Path
import pandas as pd


class InvalidImageSetError(Exception):
    pass


def scan_dataset(dataset_dir: Path, export_base: Path):
    """Scans a single dataset directory and exports patients.csv and image_sets.csv."""
    dataset_name = dataset_dir.name
    patients, image_sets = [], []

    for patient_dir in dataset_dir.iterdir():
        if not patient_dir.is_dir():
            continue
        patient_id = patient_dir.name
        patients.append({"patient_id": patient_id})

        for set_dir in patient_dir.iterdir():
            if not set_dir.is_dir():
                continue

            files = [f for f in set_dir.iterdir() if f.is_file()]
            if not files:
                continue

            exts = {f.suffix.lower() for f in files}
            valid_exts = {".dcm", ".png", ".jpg", ".jpeg"}
            exts = {e for e in exts if e in valid_exts}
            if len(exts) > 1:
                raise InvalidImageSetError(f"Mixed image formats in {set_dir}: {exts}")

            image_sets.append(
                {
                    "image_set_name": set_dir.name,
                    "patient_id": patient_id,
                    "dataset_name": dataset_name,
                    "folder_path": str(set_dir),
                    "num_images": len(files),
                }
            )

    export_dir = export_base / dataset_name
    export_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(patients).to_csv(export_dir / "patients.csv", index=False)
    pd.DataFrame(image_sets).to_csv(export_dir / "image_sets.csv", index=False)

    print(f"✓ Exported {dataset_name} to {export_dir}")


def scan_datasets(base_path: str, export_path: str):
    """Scans all datasets in the base_path and exports their metadata."""
    base = Path(base_path)
    export = Path(export_path)
    for dataset_dir in base.iterdir():
        if dataset_dir.is_dir():
            scan_dataset(dataset_dir, export)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scan_datasets.py /path/to/data_sets [export_dir]")
        sys.exit(1)

    base_path = sys.argv[1]
    export_path = sys.argv[2] if len(sys.argv) > 2 else "exports"
    scan_datasets(base_path, export_path)
