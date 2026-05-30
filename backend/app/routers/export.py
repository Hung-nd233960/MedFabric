"""Export endpoint — admin downloads CSV/Excel of all annotations."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.deps import get_current_admin
from app.services.export import export_annotations

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/annotations")
def download_annotations(
    file_format: str = Query(default="xlsx", pattern="^(xlsx|csv)$"),
    dataset_uuid: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(get_current_admin),
):
    data = export_annotations(db, file_format=file_format, dataset_uuid=dataset_uuid)
    media_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if file_format == "xlsx"
        else "text/csv"
    )
    filename = f"medfabric_annotations.{file_format}"
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
