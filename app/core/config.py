import os

from dotenv import load_dotenv

load_dotenv()


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


class Settings:
    HOST = os.getenv("PLC_HOST", "192.168.3.250")
    READ_PORT = _env_int("PLC_READ_PORT", 5000)
    WRITE_PORT = _env_int("PLC_WRITE_PORT", 4999)

    MIN_TRAY_NO = _env_int("MIN_TRAY_NO", 1)
    MAX_TRAY_NO = _env_int("MAX_TRAY_NO", 8)

    SELECT_TRAY_BIT = os.getenv("SELECT_TRAY_BIT", "D420")
    QUANTITY_DEVICE = os.getenv("QUANTITY_DEVICE", "D421")
    START_DEVICE = os.getenv("START_DEVICE", "M283")
    RUNNING_DEVICE = os.getenv("RUNNING_DEVICE", "M286")
    READY_DEVICE = os.getenv("READY_DEVICE", "M287")

    MANUAL_MODE_DEVICE = os.getenv("MANUAL_MODE_DEVICE", "M0")
    AUTO_MODE_DEVICE = os.getenv("AUTO_MODE_DEVICE", "M1")

    EMERGENCY_STOP_DEVICE = os.getenv("EMERGENCY_STOP_DEVICE", "M800")

    HOLD_SECONDS = _env_float("HOLD_SECONDS", 2)
    MODEL_NAME_WORDS = _env_int("MODEL_NAME_WORDS", 10)  # 10 words = 20 characters

    TASK_POLL_SECONDS = _env_float("TASK_POLL_SECONDS", 2)
    TASK_TIMEOUT_SECONDS = _env_float("TASK_TIMEOUT_SECONDS", 60)

    # READY_DEVICE must read 1 (and RUNNING_DEVICE must read 0) this many consecutive
    # polls before we trust the cobot is truly idle -- guards against a bit that
    # flickers to 1 briefly before the machine has actually settled.
    TASK_READY_DEBOUNCE_READS = _env_int("TASK_READY_DEBOUNCE_READS", 2)

    # Extra pause after the cobot reports ready, before dispensing the next item in
    # the same prescription -- gives the machine a moment to physically settle even
    # though the status bits already say it's ready.
    INTER_TASK_SETTLE_SECONDS = _env_float("INTER_TASK_SETTLE_SECONDS", 1.0)

    LOGIN_DEVICE = os.getenv("LOGIN_DEVICE", "D15")

    DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://mcprotocol:mcprotocol@localhost:5432/mcprotocol"
    )

    MAIN_SYSTEM_CALLBACK_URL = os.getenv("MAIN_SYSTEM_CALLBACK_URL", "")

    # The camera SDK itself lives in the separate camera_service (LAN-side, near the
    # camera/PLC). This backend only receives already-encoded JPEG frames from it.
    CAMERA_INGEST_TOKEN = os.getenv("CAMERA_INGEST_TOKEN", "")
    CAMERA_STREAM_IDLE_TIMEOUT_SECONDS = _env_float("CAMERA_STREAM_IDLE_TIMEOUT_SECONDS", 10)

    CAM_TRIG_DEVICE = os.getenv("CAM_TRIG_DEVICE", "M370")
    CAM_RESULT_OK_DEVICE = os.getenv("CAM_RESULT_OK_DEVICE", "M372")
    CAM_RESULT_NG_DEVICE = os.getenv("CAM_RESULT_NG_DEVICE", "M373")


settings = Settings()
