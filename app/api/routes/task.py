from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.routes.prescription import build_task_response
from app.db.session import get_db
from app.models.prescription import Prescription
from app.schemas.task import TaskLookupRequest

router = APIRouter()


@router.post("/get-prescription-state")
def get_task(task: TaskLookupRequest, db: Session = Depends(get_db)):
    prescription = db.query(Prescription).filter(Prescription.task_no == task.TaskNo).one_or_none()
    if prescription is None:
        return {"message": f"Task '{task.TaskNo}' not found"}
    return build_task_response(prescription)
