"""CSV/Excel export service for admin data download."""

import io
import uuid
from typing import Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session


_EXPORT_QUERY = """
SELECT
    ds.name                         AS dataset_name,
    p.patient_id,
    p.age,
    p.gender,
    p.category,
    ims.image_set_name,
    ims.icd_code,
    d.username                      AS doctor_username,
    d.role                          AS doctor_role,
    ann.annotation_session_uuid,
    ann.started_at,
    ann.submitted_at,
    ise.image_set_usability,
    ise.ischemic_low_quality,
    ise.notes                       AS set_notes,
    img.image_name,
    img.slice_index,
    ie.region,
    ie.c_left_score,
    ie.c_right_score,
    ie.ic_left_score,
    ie.ic_right_score,
    ie.l_left_score,
    ie.l_right_score,
    ie.i_left_score,
    ie.i_right_score,
    ie.m1_left_score,
    ie.m1_right_score,
    ie.m2_left_score,
    ie.m2_right_score,
    ie.m3_left_score,
    ie.m3_right_score,
    ie.m4_left_score,
    ie.m4_right_score,
    ie.m5_left_score,
    ie.m5_right_score,
    ie.m6_left_score,
    ie.m6_right_score,
    ie.notes                        AS image_notes
FROM annotation_sessions ann
JOIN doctors d       ON d.uuid            = ann.doctor_uuid
JOIN image_sets ims  ON ims.uuid          = ann.image_set_uuid
JOIN datasets ds     ON ds.dataset_uuid   = ims.dataset_uuid
JOIN patients p      ON p.patient_uuid    = ims.patient_uuid
LEFT JOIN image_set_evaluations ise ON ise.annotation_session_uuid = ann.annotation_session_uuid
LEFT JOIN image_evaluations ie      ON ie.annotation_session_uuid  = ann.annotation_session_uuid
LEFT JOIN images img                ON img.uuid                     = ie.image_uuid
WHERE ann.submitted_at IS NOT NULL
  AND (:dataset_uuid IS NULL OR ims.dataset_uuid = :dataset_uuid::uuid)
ORDER BY ds.name, p.patient_id, ims.image_set_name, d.username, img.slice_index
"""


def export_annotations(
    db: Session,
    format: str = "xlsx",
    dataset_uuid: Optional[uuid.UUID] = None,
) -> bytes:
    result = db.execute(
        text(_EXPORT_QUERY),
        {"dataset_uuid": str(dataset_uuid) if dataset_uuid else None},
    )
    rows = result.mappings().all()
    df = pd.DataFrame([dict(r) for r in rows])

    buf = io.BytesIO()
    if format == "csv":
        df.to_csv(buf, index=False)
    else:
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Annotations")
    buf.seek(0)
    return buf.read()
