"""Bug report / feature request endpoint — appends to a JSONL log file."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.about import get_about
from app.deps import get_current_doctor
from app.db.models import Doctors

router = APIRouter(prefix="/bug-reports", tags=["bug-reports"])

LOG_PATH = Path("/data/bug_reports.jsonl")


class BugReportContext(BaseModel):
    annotation_session_uuid: Optional[str] = None
    image_set_uuid: Optional[str] = None
    image_set_name: Optional[str] = None
    image_index: Optional[int] = None


class BugReportRequest(BaseModel):
    type: Literal["bug", "feature"]
    text: str
    page: str
    context: Optional[BugReportContext] = None


@router.post("", status_code=204)
def submit_bug_report(
    body: BugReportRequest,
    doctor: Doctors = Depends(get_current_doctor),
) -> None:
    about = get_about()

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": body.type,
        "text": body.text.strip(),
        "user": {
            "uuid": str(doctor.uuid),
            "username": doctor.username,
            "full_name": doctor.full_name or None,
            "role": doctor.role.value,
        },
        "app_version": about.get("version", "unknown"),
        "page": body.page,
        "context": body.context.model_dump() if body.context else None,
    }

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
