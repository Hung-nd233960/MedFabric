# medfabric/tools/scan_images.py
import sys
import re
from pathlib import Path
import pandas as pd

try:
    import pydicom
except ImportError:
    pydicom = None


class ImageFileFormatError(Exception):
    pass


def extract_slice_index(file_path: Path) -> int:
    ext = file_path.suffix.lower()

    if ext == ".dcm":
        if not pydicom:
            raise RuntimeError("pydicom is required for DICOM files")
        ds = pydicom.dcmread(str(file_path), stop_before_pixels=True)
        if hasattr(ds, "InstanceNumber"):
            return int(ds.InstanceNumber)
        elif hasattr(ds, "SliceLocation"):
            return int(float(ds.SliceLocation))
        else:
            raise ImageFileFormatError(f"No slice index in {file_path}")

    elif ext in (".png", ".jpg", ".jpeg"):
        name = file_path.stem
        m1 = re.fullmatch(r"(\d+)(?:[-_].+)?", name)
        if not m1:
            raise ImageFileFormatError(f"Invalid image filename: {file_path}")
        return int(m1.group(1).lstrip("0") or "0")

    else:
        raise ImageFileFormatError(f"Unsupported file type: {file_path}")


def scan_dataset(dataset_dir: Path, export_base: Path):
    dataset_name = dataset_dir.name
    images = []

    for patient_dir in dataset_dir.iterdir():
        if not patient_dir.is_dir():
            continue
        patient_id = patient_dir.name

        for set_dir in patient_dir.iterdir():
            if not set_dir.is_dir():
                continue
            image_set_name = set_dir.name

            for file in set_dir.iterdir():
                if not file.is_file():
                    continue
                slice_index = extract_slice_index(file)
                images.append(
                    {
                        "image_id": file.name,
                        "image_set_name": image_set_name,
                        "patient_id": patient_id,
                        "dataset_name": dataset_name,
                        "slice_index": slice_index,
                    }
                )

    export_dir = export_base / dataset_name
    export_dir.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(images).sort_values(
        ["patient_id", "image_set_name", "slice_index"]
    )
    df.to_csv(export_dir / "images.csv", index=False)

    print(f"✓ Exported {dataset_name}/images.csv ({len(df)} images)")


def scan_images(base_path: str, export_path: str):
    base = Path(base_path)
    export = Path(export_path)
    for dataset_dir in base.iterdir():
        if dataset_dir.is_dir():
            scan_dataset(dataset_dir, export)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scan_images.py /path/to/data_sets [export_dir]")
        sys.exit(1)

    base_path = sys.argv[1]
    export_path = sys.argv[2] if len(sys.argv) > 2 else "exports"
    scan_images(base_path, export_path)
