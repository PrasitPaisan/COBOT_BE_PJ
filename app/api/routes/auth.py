from fastapi import APIRouter

from app.core.config import settings
from app.plc.client import get_write_connection
from app.schemas.auth import LoginRequest

router = APIRouter()

MIN_LEVEL = 0
MAX_LEVEL = 2

LEVEL_NAMES = {0: "Unlogin", 1: "Pharmacist", 2: "Engineer"}


@router.post("/login")
def login(task: LoginRequest):
    if task.level < MIN_LEVEL or task.level > MAX_LEVEL:
        return {"success": False, "message": f"level must be between {MIN_LEVEL}-{MAX_LEVEL}"}

    level_name = LEVEL_NAMES[task.level]

    try:
        with get_write_connection() as mc:
            mc.batchwrite_wordunits(headdevice=settings.LOGIN_DEVICE, values=[task.level])
    except Exception as e:
        return {"success": False, "message": f"{e}"}

    if task.level == 0:
        return {"success": True, "message": "Logged out"}

    return {"success": True, "message": f"{level_name} logged in successfully"}
