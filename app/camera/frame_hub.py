"""
Holds the latest JPEG frame pushed by the LAN-side camera_service and fans it
out to any number of MJPEG stream viewers. No camera SDK involved at all here
-- frames arrive already encoded via POST /camera/ingest, so this module has
zero platform-specific dependencies and works identically on Linux/Docker.
"""

import asyncio
import threading
import time
from typing import Optional


class FrameHub:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest_jpeg: Optional[bytes] = None
        self._last_frame_at: float = 0.0

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._subs_lock = threading.Lock()
        self._subscribers: set[asyncio.Queue] = set()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    @property
    def connected(self) -> bool:
        # "connected" == camera_service has pushed a frame recently.
        return self._latest_jpeg is not None and (time.monotonic() - self._last_frame_at) < 5

    def get_latest_jpeg(self) -> Optional[bytes]:
        return self._latest_jpeg

    def ingest(self, jpeg_bytes: bytes) -> None:
        self._latest_jpeg = jpeg_bytes
        self._last_frame_at = time.monotonic()
        if self._loop is None:
            return
        with self._subs_lock:
            subscribers = list(self._subscribers)
        for queue in subscribers:
            self._loop.call_soon_threadsafe(self._put_latest, queue, jpeg_bytes)

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1)
        with self._subs_lock:
            self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        with self._subs_lock:
            self._subscribers.discard(queue)

    @staticmethod
    def _put_latest(queue: asyncio.Queue, jpeg_bytes: bytes) -> None:
        # Keep only the newest frame -- a slow viewer should skip frames, never
        # build up a backlog.
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            queue.put_nowait(jpeg_bytes)
        except asyncio.QueueFull:
            pass


frame_hub = FrameHub()
