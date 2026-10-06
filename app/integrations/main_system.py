import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def notify_task_result(task_no: str, status: str) -> None:
    """Tell the main system a task has finished, so it can move the basket along.

    Best-effort: the endpoint/spec isn't finalized yet, and a failure to notify must never
    surface as an error to the caller of /send-prescription -- the dispensing outcome is
    already persisted regardless of whether this call succeeds.
    """
    if not settings.MAIN_SYSTEM_CALLBACK_URL:
        logger.info("MAIN_SYSTEM_CALLBACK_URL not configured; skipping notify for %s (%s)", task_no, status)
        return

    try:
        httpx.post(
            settings.MAIN_SYSTEM_CALLBACK_URL,
            json={"TaskNo": task_no, "Status": status},
            timeout=5.0,
        )
    except Exception:
        logger.exception("Failed to notify main system for task %s", task_no)
