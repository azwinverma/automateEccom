"""UUIDv7 (RFC 9562): time-ordered IDs → index-friendly primary keys, sortable cursors.

Monotonic within a process (RFC 9562 §6.2 method 1): IDs created in the same millisecond use a
12-bit counter in ``rand_a`` seeded randomly each new millisecond, so rows written in one request
(e.g. an order's timeline events) sort in creation order. Counter overflow borrows the next ms.
"""

from __future__ import annotations

import os
import threading
import time
import uuid

_lock = threading.Lock()
_last_ms = 0
_counter = 0


def uuid7() -> uuid.UUID:
    global _last_ms, _counter
    with _lock:
        ts_ms = time.time_ns() // 1_000_000
        if ts_ms <= _last_ms:
            ts_ms = _last_ms
            _counter += 1
            if _counter > 0xFFF:
                ts_ms += 1
                _counter = int.from_bytes(os.urandom(2), "big") & 0x7FF
        else:
            _counter = int.from_bytes(os.urandom(2), "big") & 0x7FF  # headroom for same-ms increments
        _last_ms = ts_ms
        rand_a = _counter
    rand_b = int.from_bytes(os.urandom(8), "big") & ((1 << 62) - 1)
    value = (ts_ms & ((1 << 48) - 1)) << 80
    value |= 0x7 << 76
    value |= rand_a << 64
    value |= 0b10 << 62
    value |= rand_b
    return uuid.UUID(int=value)
