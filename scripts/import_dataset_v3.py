"""
MedFabric 3.0 — CSV dataset importer.

Drop-in replacement for the old importer.py that works against the new
FastAPI/PostgreSQL backend schema.

Usage (run from project root):
    python scripts/import_dataset_v3.py \
        --dataset-name "E Hospital Dataset" \
        --dataset-desc  "Filtered E Hospital dataset" \
        --image-sets    data_sets/e_hospital/image_sets.csv \
        --images        data_sets/e_hospital/images.csv \
        [--prognosis    data_sets/e_hospital/prognosis.csv] \
        [--env          backend/.env]

CSV contracts (unchanged from v2):
  image_sets.csv : image_set_uuid, num_images, folder_path, image_format,
                   window_center, window_width, description, code
  images.csv     : file_name, image_set_uuid, slice_index
  prognosis.csv  : image_set_uuid, [any other columns merged to description]

Environment:
  DATABASE_URL must be set (reads from --env file or environment).
"""

import argparse
import os
import sys
import uuid as uuid_lib
from pathlib import Path

import pandas as pd

# Allow `app` imports — works both locally (backend/) and inside Docker (/app)
_script_dir = Path(__file__).resolve().parent
for _candidate in [_script_dir.parent / "backend", Path("/app")]:
    if (_candidate / "app").is_dir():
        sys.path.insert(0, str(_candidate))
        break

# Load .env before importing settings
def _load_env(env_path: str) -> None:
    p = Path(env_path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Import CSV dataset into MedFabric 3.0")
    parser.add_argument("--dataset-name", default="E Hospital Dataset")
    parser.add_argument("--dataset-desc", default="")
    parser.add_argument("--image-sets", default="data_sets/e_hospital/image_sets.csv")
    parser.add_argument("--images", default="data_sets/e_hospital/images.csv")
    parser.add_argument("--prognosis", default=None)
    parser.add_argument("--env", default="backend/.env")
    args = parser.parse_args()

    _load_env(args.env)

    # Import after env is loaded so DATABASE_URL is visible to pydantic-settings
    from app.core.database import SessionLocal
    from app.db.models import DataSet, Image, ImageFormat, ImageSet, Patient

    db = SessionLocal()

    try:
        # ── Dataset ──────────────────────────────────────────────────────────
        ds = db.query(DataSet).filter(DataSet.name == args.dataset_name).first()
        if ds is None:
            ds = DataSet(
                dataset_uuid=uuid_lib.uuid4(),
                name=args.dataset_name,
                description=args.dataset_desc or None,
            )
            db.add(ds)
            db.flush()
            print(f"Created dataset '{ds.name}'  uuid={ds.dataset_uuid}")
        else:
            print(f"Found existing dataset '{ds.name}'  uuid={ds.dataset_uuid}")

        dataset_uuid = ds.dataset_uuid

        # ── CSVs ─────────────────────────────────────────────────────────────
        image_set_df = pd.read_csv(args.image_sets)
        images_df = pd.read_csv(args.images)

        if args.prognosis:
            prognosis_df = pd.read_csv(args.prognosis)
            image_set_df = image_set_df.merge(prognosis_df, on="image_set_uuid", how="left")

        # ── Image sets ────────────────────────────────────────────────────────
        print(f"\nImporting {len(image_set_df)} image sets…")
        for _, row in image_set_df.iterrows():
            img_set_uuid = uuid_lib.UUID(str(row["image_set_uuid"]))

            # One synthetic patient per image set (original script pattern)
            patient_id = f"patient_{img_set_uuid}_e_hospital"
            patient = (
                db.query(Patient)
                .filter(Patient.patient_id == patient_id, Patient.dataset_uuid == dataset_uuid)
                .first()
            )
            if patient is None:
                patient = Patient(
                    patient_uuid=uuid_lib.uuid4(),
                    patient_id=patient_id,
                    dataset_uuid=dataset_uuid,
                )
                db.add(patient)
                db.flush()

            # Skip if already imported
            existing = db.query(ImageSet).filter(ImageSet.uuid == img_set_uuid).first()
            if existing:
                print(f"  [skip] {row['image_set_uuid']} — already exists")
                continue

            # Parse image format
            fmt_str = str(row.get("image_format", "DICOM")).upper().strip()
            fmt_map = {"DICOM": ImageFormat.DICOM, "JPEG": ImageFormat.JPEG, "JPG": ImageFormat.JPEG, "PNG": ImageFormat.PNG}
            image_format = fmt_map.get(fmt_str, ImageFormat.DICOM)

            # Parse window params (N/A → None)
            def _int_or_none(val) -> int | None:
                try:
                    if pd.isna(val) or str(val).upper() == "N/A":
                        return None
                    return int(float(val))
                except (TypeError, ValueError):
                    return None

            wl = _int_or_none(row.get("window_center"))
            ww = _int_or_none(row.get("window_width"))

            img_set = ImageSet(
                uuid=img_set_uuid,
                dataset_uuid=dataset_uuid,
                patient_uuid=patient.patient_uuid,
                image_set_name=str(row["image_set_uuid"]),
                image_format=image_format,
                image_window_level=wl,
                image_window_width=ww,
                num_images=int(row["num_images"]),
                folder_path=str(row["folder_path"]),
                description=str(row["description"]) if pd.notna(row.get("description")) else None,
                icd_code=str(row["code"]) if pd.notna(row.get("code")) else None,
            )
            db.add(img_set)
            print(f"  + {img_set.image_set_name}  fmt={image_format.value}  WL={wl}  WW={ww}")

        db.flush()

        # ── Images ────────────────────────────────────────────────────────────
        print(f"\nImporting {len(images_df)} images…")
        for _, row in images_df.iterrows():
            img_set_uuid = uuid_lib.UUID(str(row["image_set_uuid"]))

            existing = (
                db.query(Image)
                .filter(
                    Image.image_set_uuid == img_set_uuid,
                    Image.slice_index == int(row["slice_index"]),
                )
                .first()
            )
            if existing:
                continue  # idempotent

            image = Image(
                uuid=uuid_lib.uuid4(),
                image_name=str(row["file_name"]),
                image_set_uuid=img_set_uuid,
                slice_index=int(row["slice_index"]),
            )
            db.add(image)

        db.commit()
        print("\nImport complete!")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
