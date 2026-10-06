import threading
from contextlib import contextmanager

import pymcprotocol

from app.core.config import settings

# The PLC's Ethernet module only tolerates a small number of simultaneous
# connections -- opening more than it supports causes silent corruption (a
# write "succeeds" but reads back as if it never happened, or vice versa: a
# read returns stale/zeroed data) instead of a clean error. It's configured
# with two separate connection slots, one per port: PLC_WRITE_PORT for writes,
# PLC_READ_PORT for reads. Each lock below ensures at most one connection per
# port is ever open at a time, matching that capacity -- reads and writes can
# still happen concurrently (different ports), but two reads (or two writes)
# never race each other.
_read_lock = threading.Lock()
_write_lock = threading.Lock()


def _connect(port: int):
    mc = pymcprotocol.Type3E()
    mc.setaccessopt(commtype="binary")
    mc.connect(settings.HOST, port)
    return mc


@contextmanager
def get_read_connection():
    with _read_lock:
        mc = _connect(settings.READ_PORT)
        try:
            yield mc
        finally:
            mc.close()


@contextmanager
def get_write_connection():
    with _write_lock:
        mc = _connect(settings.WRITE_PORT)
        try:
            yield mc
        finally:
            mc.close()
