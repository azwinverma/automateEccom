"""Redis fixed-window rate limiting. Fails open (logged) if Redis is unavailable so auth stays up,
while the account lockout in the database remains the hard brute-force control."""

from __future__ import annotations

import time

import redis
import structlog

from app.core.errors import RateLimited
from app.core.redis import get_redis

log = structlog.get_logger(__name__)


def hit(key: str, limit: int, window_seconds: int) -> int:
    """Increment the counter for ``key``; raise RateLimited when over ``limit``. Returns count."""
    bucket = int(time.time() // window_seconds)
    rkey = f"rl:{key}:{bucket}"
    try:
        r = get_redis()
        pipe = r.pipeline()
        pipe.incr(rkey)
        pipe.expire(rkey, window_seconds + 1)
        count = int(pipe.execute()[0])
    except redis.RedisError:
        log.warning("rate_limit_redis_unavailable", key_prefix=key.split(":")[0])
        return 0
    if count > limit:
        retry_after = window_seconds - int(time.time() % window_seconds)
        raise RateLimited(details={"retry_after": retry_after}, headers={"Retry-After": str(retry_after)})
    return count
