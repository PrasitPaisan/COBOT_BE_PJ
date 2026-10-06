import asyncio
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, Response
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from app.camera.frame_hub import frame_hub
from app.core.config import settings
from app.plc.client import get_read_connection, get_write_connection

router = APIRouter()
logger = logging.getLogger(__name__)

_BOUNDARY = "frame"


def _read_bit(mc, device: str) -> int:
    return mc.batchread_bitunits(headdevice=device, readsize=1)[0]


def _write_bit(mc, device: str, value: int) -> None:
    mc.batchwrite_bitunits(headdevice=device, values=[value])


class InspectionResult(BaseModel):
    result: str  # "OK" or "NG"


@router.get("/camera/trigger-status")
def camera_trigger_status():
    """Lets the operator check whether the PLC is currently asking for a capture (M370)."""
    try:
        with get_read_connection() as mc:
            triggered = _read_bit(mc, settings.CAM_TRIG_DEVICE) == 1
            return {"triggered": triggered, "timestamp": datetime.now(timezone.utc).isoformat()}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{e}")


def _reset_bit_after_hold(device: str) -> None:
    """
    Background follow-up: hold, then write 0 and read it back to confirm the reset
    landed. Runs after the response for /camera/inspection-result has already gone
    out, so a rapid double-click never has to wait for this -- failures here are
    just logged, since the OK/NG signal itself was already confirmed synchronously.
    """
    try:
        time.sleep(settings.HOLD_SECONDS)
        with get_write_connection() as mc:
            _write_bit(mc, device, 0)
        with get_read_connection() as mc:
            confirmed = _read_bit(mc, device)
        if confirmed != 0:
            logger.warning("Reset of %s did not land: readback=%s", device, confirmed)
    except Exception:
        logger.exception("Failed to reset %s after hold", device)


@router.post("/camera/inspection-result")
def camera_inspection_result(payload: InspectionResult, background_tasks: BackgroundTasks):
    """
    Operator confirms OK/NG while watching the live stream. Writes the bit and reads
    it back immediately to confirm the PLC actually latched it -- so a click is only
    ever reported as successful once we've verified it, not just because the write
    call didn't raise. Resetting the bit back to 0 after a hold happens in the
    background so rapid repeated clicks never have to wait on that.
    """
    result = payload.result.upper()
    if result == "OK":
        device = settings.CAM_RESULT_OK_DEVICE
    elif result == "NG":
        device = settings.CAM_RESULT_NG_DEVICE
    else:
        raise HTTPException(status_code=400, detail="result must be 'OK' or 'NG'")

    try:
        with get_write_connection() as mc:
            _write_bit(mc, device, 1)
        with get_read_connection() as mc:
            confirmed = _read_bit(mc, device)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"{e}")

    if confirmed != 1:
        raise HTTPException(status_code=502, detail=f"Write to {device} did not take effect (readback={confirmed})")

    background_tasks.add_task(_reset_bit_after_hold, device)
    return {
        "result": result,
        "device": device,
        "confirmed": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/camera/ingest")
async def camera_ingest(request: Request, x_camera_token: str = Header(default="")):
    """Receives one JPEG frame pushed by the LAN-side camera_service."""
    if not settings.CAMERA_INGEST_TOKEN or x_camera_token != settings.CAMERA_INGEST_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing camera token")
    jpeg_bytes = await request.body()
    frame_hub.ingest(jpeg_bytes)
    return {"ok": True}


@router.get("/camera/status")
def camera_status():
    return {"connected": frame_hub.connected}


@router.get("/camera/snapshot")
def camera_snapshot():
    jpeg_bytes = frame_hub.get_latest_jpeg()
    if jpeg_bytes is None:
        raise HTTPException(status_code=503, detail="No frame available yet")
    return Response(content=jpeg_bytes, media_type="image/jpeg")


async def _mjpeg_generator():
    queue = frame_hub.subscribe()
    try:
        while True:
            try:
                jpeg_bytes = await asyncio.wait_for(
                    queue.get(), timeout=settings.CAMERA_STREAM_IDLE_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                # No frame for a while -- if camera_service isn't even pushing, stop hanging
                # the connection open forever and let the client see the stream end.
                if not frame_hub.connected:
                    break
                continue
            yield (
                f"--{_BOUNDARY}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(jpeg_bytes)}\r\n\r\n"
            ).encode() + jpeg_bytes + b"\r\n"
    except asyncio.CancelledError:
        pass
    finally:
        frame_hub.unsubscribe(queue)


@router.get("/camera/stream")
async def camera_stream():
    return StreamingResponse(
        _mjpeg_generator(),
        media_type=f"multipart/x-mixed-replace; boundary={_BOUNDARY}",
    )
