"""Backfill patient age/gender from DICOM headers.

For every patient missing ``age`` and/or ``gender``, locate a DICOM file in one
of the patient's image sets and read ``PatientAge`` / ``PatientSex`` (with
``PatientBirthDate`` vs ``StudyDate`` as an age fallback). Only NULL columns are
filled, so any explicitly-set value is preserved.

Run inside the backend container (it has the DB connection and the dataset
volume mounted at ``DATASET_ROOT``)::

    docker exec docker-backend-1 python -m scripts.backfill_patient_demographics --dry-run
    docker exec docker-backend-1 python -m scripts.backfill_patient_demographics
"""

import argparse
from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.db.models import ImageFormat, ImageSet, Patient
from app.services.image_loader.dicom_processing import extract_patient_demographics

settings = get_settings()

_DICOM_SUFFIXES = {".dcm", ".dicom", ""}


def _resolve_folder(folder_path: str) -> Path:
    path = Path(folder_path)
    if not path.is_absolute():
        path = settings.dataset_root / folder_path
    return path


def _first_dicom(folder: Path) -> Optional[Path]:
    if not folder.is_dir():
        return None
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in _DICOM_SUFFIXES:
            return p
    return None


def backfill(dry_run: bool) -> None:
    db = SessionLocal()
    try:
        patients = (
            db.query(Patient)
            .filter((Patient.age.is_(None)) | (Patient.gender.is_(None)))
            .all()
        )
        print(f"{len(patients)} patient(s) missing age and/or gender.")

        updated = no_imageset = no_dicom = no_data = 0
        for patient in patients:
            image_set = (
                db.query(ImageSet)
                .filter(
                    ImageSet.patient_uuid == patient.patient_uuid,
                    ImageSet.image_format == ImageFormat.DICOM,
                )
                .first()
            )
            if image_set is None:
                no_imageset += 1
                continue

            sample = _first_dicom(_resolve_folder(image_set.folder_path))
            if sample is None:
                no_dicom += 1
                print(f"  ! {patient.patient_id}: no DICOM under {image_set.folder_path}")
                continue

            age, gender = extract_patient_demographics(sample)
            new_age = age if patient.age is None else None
            new_gender = gender if patient.gender is None else None
            if new_age is None and new_gender is None:
                no_data += 1
                continue

            if new_age is not None:
                patient.age = new_age
            if new_gender is not None:
                patient.gender = new_gender
            updated += 1
            g = patient.gender.value if patient.gender else None
            print(f"  + {patient.patient_id}: age={patient.age} gender={g}")

        if dry_run:
            db.rollback()
            print("\nDRY RUN — no changes committed.")
        else:
            db.commit()
            print("\nCommitted.")

        print(
            f"updated={updated} no_imageset={no_imageset} "
            f"no_dicom={no_dicom} no_demographics={no_data}"
        )
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing to the database.",
    )
    args = parser.parse_args()
    backfill(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
