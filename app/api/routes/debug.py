from fastapi import APIRouter

from app.plc.client import get_read_connection, get_write_connection

router = APIRouter()


def _is_word_device(regis: str) -> bool:
    # D = data register (word), everything else here (M, X, Y, ...) is a bit device.
    return regis.strip().upper().startswith("D")


@router.get("/readOnePoint")
def read_one_point(regis: str):
    try:
        with get_read_connection() as mc:
            if _is_word_device(regis):
                return mc.batchread_wordunits(headdevice=regis, readsize=1)
            return mc.batchread_bitunits(headdevice=regis, readsize=1)
    except Exception as e:
        return {"message": f"{e}"}


@router.post("/writeOnePoint")
def write_one_point(regis: str, value: int):
    """
    Isolated write+readback for wiring/mapping debugging -- bypasses any
    application-level pulse/reset logic so you can see exactly what a bare
    write to a given device does on this PLC. Works for bit devices (M) and
    word/register devices (D).
    """
    try:
        word = _is_word_device(regis)
        with get_write_connection() as mc:
            if word:
                mc.batchwrite_wordunits(headdevice=regis, values=[value])
            else:
                mc.batchwrite_bitunits(headdevice=regis, values=[value])
        with get_read_connection() as mc:
            if word:
                readback = mc.batchread_wordunits(headdevice=regis, readsize=1)[0]
            else:
                readback = mc.batchread_bitunits(headdevice=regis, readsize=1)[0]
        return {"regis": regis, "written": value, "readback": readback}
    except Exception as e:
        return {"message": f"{e}"}
