from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import settings
from app.plc.client import get_read_connection

router = APIRouter()


def _read_bit(mc, device: str) -> int:
    return mc.batchread_bitunits(headdevice=device, readsize=1)[0]


@router.get("/get-status")
def get_status():
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        with get_read_connection() as mc:
            running = _read_bit(mc, settings.RUNNING_DEVICE)
            ready = _read_bit(mc, settings.READY_DEVICE)
            auto_mode = _read_bit(mc, settings.AUTO_MODE_DEVICE)
            manual_mode = _read_bit(mc, settings.MANUAL_MODE_DEVICE)

            if running == 1:
                status, message = 1, "Running"
            elif ready == 1:
                status, message = 0, "Ready"
            else:
                status, message = 3, "Error"

            if auto_mode == 1 and manual_mode == 0:
                mode = "auto"
            elif manual_mode == 1 and auto_mode == 0:
                mode = "manual"
            else:
                mode = None

            return {
                "status": status,
                "message": message,
                "mode": mode,
                "ready_bit": ready,
                "running_bit": running,
                "timestamp": timestamp,
            }
    except Exception as e:
        return {"status": None, "message": f"{e}", "timestamp": timestamp}
