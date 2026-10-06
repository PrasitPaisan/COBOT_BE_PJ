from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.medicine import Medicine
from app.models.tray import Tray
from app.plc.client import get_write_connection
from app.plc.codec import encode_model_name
from app.plc.devices import MED_NAME_START, MED_QUAN
from app.schemas.tray import MedicineDictionary

router = APIRouter()


@router.post("/send-medicine")
def set_tray_medicine(task: MedicineDictionary, db: Session = Depends(get_db)):
    if task.Quantity < 0:
        return {"message": "Quantity cannot be negative"}

    max_chars = settings.MODEL_NAME_WORDS * 2
    name20 = task.MedName[:max_chars]

    medicine = db.query(Medicine).filter(Medicine.med_his_id == task.MedId).one_or_none()
    is_new = medicine is None
    if is_new:
        medicine = Medicine(med_his_id=task.MedId)

    if task.TrayNo is not None:
        if task.TrayNo < settings.MIN_TRAY_NO or task.TrayNo > settings.MAX_TRAY_NO:
            return {"message": f"Tray number must be between {settings.MIN_TRAY_NO} and {settings.MAX_TRAY_NO}"}
        tray_no = task.TrayNo
        # Explicit placement replaces whichever medicine currently holds that tray.
        occupant = (
            db.query(Medicine)
            .filter(Medicine.tray_no == tray_no, Medicine.med_his_id != task.MedId)
            .one_or_none()
        )
        if occupant is not None:
            occupant.tray_no = None
            db.flush()
    else:
        tray_no = medicine.tray_no
        if tray_no is None:
            used = {t for (t,) in db.query(Medicine.tray_no).filter(Medicine.tray_no.isnot(None))}
            free = [t for t in range(settings.MIN_TRAY_NO, settings.MAX_TRAY_NO + 1) if t not in used]
            if not free:
                return {"message": f"All {settings.MAX_TRAY_NO} trays are currently occupied"}
            tray_no = free[0]

    medicine.name = task.MedName
    medicine.name20 = name20
    medicine.specs = task.Specs
    medicine.factory_name = task.FactoryName
    medicine.tray_no = tray_no
    if is_new:
        db.add(medicine)
    db.flush()

    try:
        with get_write_connection() as mc:
            mc.batchwrite_wordunits(headdevice=MED_NAME_START[tray_no], values=encode_model_name(name20))
            mc.batchwrite_wordunits(headdevice=MED_QUAN[tray_no], values=[task.Quantity])
    except Exception as e:
        db.rollback()
        return {"message": f"{e}"}

    tray = db.get(Tray, tray_no) or Tray(tray_no=tray_no)
    tray.med_his_id = medicine.med_his_id
    tray.quantity = task.Quantity
    tray.last_synced_at = datetime.now(timezone.utc)
    db.add(tray)
    db.commit()

    return {
        "MedId": medicine.med_his_id,
        "MedName": medicine.name,
        "Name20": medicine.name20,
        "Specs": medicine.specs,
        "FactoryName": medicine.factory_name,
        "TrayNo": tray_no,
        "Quantity": task.Quantity,
        "message": f"Medicine '{medicine.name}' saved to tray {tray_no} (qty {task.Quantity})",
    }
