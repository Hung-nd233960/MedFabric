"""Dashboard endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import Doctors
from app.db.schemas import DashboardStats
from app.deps import get_current_doctor
from app.services.dashboard import get_dashboard_stats

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/", response_model=DashboardStats)
def dashboard(
    db: Session = Depends(get_db),
    doctor: Doctors = Depends(get_current_doctor),
):
    return get_dashboard_stats(db, doctor.uuid)
