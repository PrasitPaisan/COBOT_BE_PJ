import logging
import threading
import time
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.integrations.main_system import notify_task_result
from app.models.dispense_log import DispenseLog
from app.models.medicine import Medicine
from app.models.prescription import Prescription
from app.models.prescription_detail import PrescriptionDetail
from app.plc.client import get_read_connection, get_write_connection
from app.plc.devices import LOAD_TRAY_TO_COBOT
from app.schemas.cobot import COBOTTask
from app.schemas.prescription_task import PrescriptionTask

router = APIRouter()
logger = logging.getLogger(__name__)

# Serializes actual dispensing so two tasks arriving back-to-back never dispense concurrently.
_dispense_lock = threading.Lock()


def _is_ready() -> bool:
    with get_read_connection() as mc:
        return mc.batchread_bitunits(headdevice=settings.READY_DEVICE, readsize=1)[0] == 1


def _is_running() -> bool:
    with get_read_connection() as mc:
        return mc.batchread_bitunits(headdevice=settings.RUNNING_DEVICE, readsize=1)[0] == 1


def _wait_until_ready() -> bool:
    """
    Waits for the cobot to report idle. READY must read 1 (and RUNNING must read 0)
    for TASK_READY_DEBOUNCE_READS consecutive polls before we trust it -- a single
    read of READY==1 was found to sometimes fire while the cobot was still settling
    from the previous item, causing the next item's START pulse to be missed.
    """
    deadline = time.monotonic() + settings.TASK_TIMEOUT_SECONDS
    consecutive_ready = 0
    while time.monotonic() < deadline:
        ready = _is_ready()
        running = _is_running()
        logger.info("Waiting for cobot idle: ready=%s running=%s (streak=%d)", ready, running, consecutive_ready)

        if ready and not running:
            consecutive_ready += 1
            if consecutive_ready >= settings.TASK_READY_DEBOUNCE_READS:
                if settings.INTER_TASK_SETTLE_SECONDS > 0:
                    time.sleep(settings.INTER_TASK_SETTLE_SECONDS)
                return True
        else:
            consecutive_ready = 0

        time.sleep(settings.TASK_POLL_SECONDS)
    return False


def _send_single(task: COBOTTask) -> dict:
    if task.TrayNo < settings.MIN_TRAY_NO or task.TrayNo > settings.MAX_TRAY_NO:
        return {
            "TrayNo": task.TrayNo,
            "Quantity": task.Quantity,
            "message": f"Tray number must be between {settings.MIN_TRAY_NO} and {settings.MAX_TRAY_NO}",
        }

    if task.Quantity < 1:
        return {"TrayNo": task.TrayNo, "Quantity": task.Quantity, "message": "Quantity must be at least 1"}

    if not _is_ready():
        return {
            "TrayNo": task.TrayNo,
            "Quantity": task.Quantity,
            "message": "Machine is not ready to dispense",
        }

    # เขียน Tray No. และจำนวนยา แล้วสั่งเริ่มทำงานที่ M283 (hold 2 วินาทีแล้วปิด)
    with get_write_connection() as mc:
        mc.batchwrite_wordunits(headdevice=settings.SELECT_TRAY_BIT, values=[task.TrayNo, task.Quantity])
        mc.batchwrite_bitunits(headdevice="M280", values=list(LOAD_TRAY_TO_COBOT.values()))
        mc.batchwrite_bitunits(headdevice=settings.START_DEVICE, values=[1])
        time.sleep(settings.HOLD_SECONDS)
        mc.batchwrite_bitunits(headdevice=settings.START_DEVICE, values=[0])

    # รอจน cobot ทำ task นี้เสร็จ (READY_DEVICE กลับมาเป็น 1) ก่อนไป task ถัดไป
    if not _wait_until_ready():
        return {
            "TrayNo": task.TrayNo,
            "Quantity": task.Quantity,
            "message": f"Dispensing timed out for tray {task.TrayNo}",
        }

    return {
        "TrayNo": task.TrayNo,
        "Quantity": task.Quantity,
        "message": f"Successfully dispensed from tray {task.TrayNo} (qty {task.Quantity})",
    }


def build_task_response(prescription: Prescription) -> dict:
    return {
        "TaskNo": prescription.task_no,
        "PreHisId": prescription.pre_his_id,
        "PatId": prescription.pat_id,
        "PatName": prescription.pat_name,
        "status": prescription.status,
        "results": [
            {
                "MedHisId": d.med_his_id,
                "TrayNo": d.tray_no,
                "Quantity": d.requested_quantity,
                "status": d.status,
                "message": d.message,
            }
            for d in prescription.details
        ],
    }


def _process_prescription(prescription_id: int, task: PrescriptionTask) -> None:
    db = SessionLocal()
    try:
        prescription = db.get(Prescription, prescription_id)
        details = (
            db.query(PrescriptionDetail)
            .filter(PrescriptionDetail.prescription_id == prescription_id)
            .order_by(PrescriptionDetail.id)
            .all()
        )

        try:
            for detail, item in zip(details, task.MedicineList):
                medicine = db.get(Medicine, detail.med_his_id)
                if medicine is None or medicine.tray_no is None:
                    detail.status = "unmatched"
                    detail.message = f"No tray registered for medicine '{item.MedName}'"
                    continue

                detail.tray_no = medicine.tray_no
                outcome = _send_single(COBOTTask(TrayNo=medicine.tray_no, Quantity=item.MedNumber))
                detail.message = outcome["message"]
                if detail.message.startswith("Successfully dispensed"):
                    detail.status = "dispensed"
                    detail.dispensed_at = datetime.now(timezone.utc)
                elif detail.message.startswith("Dispensing timed out"):
                    detail.status = "timeout"
                else:
                    detail.status = "failed"

                db.add(DispenseLog(
                    prescription_detail_id=detail.id,
                    tray_no=medicine.tray_no,
                    requested_quantity=item.MedNumber,
                    success=detail.status == "dispensed",
                    message=detail.message,
                ))
        except Exception as e:
            for detail in details:
                if detail.status == "pending":
                    detail.status = "failed"
                    detail.message = f"PLC connection error: {e}"
            prescription.status = "failed"
            prescription.completed_at = datetime.now(timezone.utc)
            db.commit()
            notify_task_result(task.TaskNo, "failed")
            return

        statuses = {d.status for d in details}
        prescription.status = (
            "completed" if statuses == {"dispensed"}
            else "failed" if statuses <= {"unmatched", "failed", "timeout"}
            else "partial"
        )
        prescription.completed_at = datetime.now(timezone.utc)
        db.commit()
        notify_task_result(task.TaskNo, prescription.status)
    finally:
        db.close()
        _dispense_lock.release()


@router.post("/send-prescription")
def send_prescription(task: PrescriptionTask, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    existing = db.query(Prescription).filter(Prescription.task_no == task.TaskNo).one_or_none()
    if existing is not None:
        return build_task_response(existing)

    if not _dispense_lock.acquire(blocking=False):
        return {"TaskNo": task.TaskNo, "message": "Machine is currently busy with another prescription"}

    try:
        ready = _is_ready()
    except Exception as e:
        _dispense_lock.release()
        notify_task_result(task.TaskNo, "failed")
        return {"TaskNo": task.TaskNo, "message": f"{e}"}

    if not ready:
        _dispense_lock.release()
        notify_task_result(task.TaskNo, "failed")
        return {"TaskNo": task.TaskNo, "message": "Machine is not ready to accept a new prescription"}

    prescription = Prescription(
        task_no=task.TaskNo,
        pre_his_id=task.PreHisId,
        pre_id=task.PreId,
        basket_id=task.BasketId,
        split_id=task.SplitId,
        pat_id=task.PatId,
        pat_name=task.PatName,
        pat_age=task.PatAge,
        pat_sex=task.PatSex,
        status="in_progress",
    )
    db.add(prescription)
    db.flush()

    details = [
        PrescriptionDetail(
            prescription_id=prescription.id,
            med_his_id=item.MedHisId,
            requested_quantity=item.MedNumber,
            status="pending",
        )
        for item in task.MedicineList
    ]
    db.add_all(details)
    db.commit()  # must be a real commit -- the background task opens its own DB session

    background_tasks.add_task(_process_prescription, prescription.id, task)
    return build_task_response(prescription)
