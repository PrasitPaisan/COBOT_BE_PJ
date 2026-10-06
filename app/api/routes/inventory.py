from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.tray import Tray
from app.plc.client import get_read_connection
from app.plc.codec import decode_model_name
from app.plc.devices import MED_NAME_START, MED_QUAN, TRAY_STATUS

router = APIRouter()


def _read_tray(mc, tray: int) -> dict:
    tray_status = mc.batchread_bitunits(headdevice=TRAY_STATUS[tray], readsize=1)[0]
    quantity = mc.batchread_wordunits(headdevice=MED_QUAN[tray], readsize=1)[0]
    name_words = mc.batchread_wordunits(headdevice=MED_NAME_START[tray], readsize=settings.MODEL_NAME_WORDS)
    name = decode_model_name(name_words)

    return {
        "tray_no": tray,
        "name": name,
        "tray_status": tray_status,
        "quantity": quantity,
    }


@router.get("/get-inventory")
def get_inventory_all():
    try:
        with get_read_connection() as mc:
            return [
                _read_tray(mc, tray)
                for tray in range(settings.MIN_TRAY_NO, settings.MAX_TRAY_NO + 1)
            ]
    except Exception as e:
        return {"message": f"{e}"}


@router.get("/get-inventory-db")
def get_inventory_db(db: Session = Depends(get_db)):
    trays = db.query(Tray).order_by(Tray.tray_no).all()
    return [
        {
            "tray_no": tray.tray_no,
            "med_his_id": tray.med_his_id,
            "name": tray.medicine.name if tray.medicine else None,
            "name20": tray.medicine.name20 if tray.medicine else None,
            "tray_status": tray.status,
            "quantity": tray.quantity,
            "last_synced_at": tray.last_synced_at,
        }
        for tray in trays
    ]
