"""Shared circuit breaker + health scoring (AIG-008, AIG-009), stored in Redis so all API/worker
instances agree. States: closed → open (after N failures in window) → half-open (one probe) → closed.
If Redis is unavailable the breaker fails open (allows calls) and logs — provider calls still have
timeouts and bounded retries, so this degrades to "no breaker", never to "no AI".
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import redis
import structlog

from app.core.metrics import AI_CIRCUIT_OPEN
from app.core.redis import get_redis

log = structlog.get_logger(__name__)


@dataclass
class BreakerConfig:
    failure_threshold: int = 5
    window_s: int = 60
    open_s: int = 30


class CircuitBreaker:
    def __init__(self, cfg: BreakerConfig, client: redis.Redis | None = None) -> None:
        self.cfg = cfg
        self._r = client

    @property
    def r(self) -> Any:  # sync client; typed Any because redis-py stubs union sync/async returns
        return self._r or get_redis()

    @staticmethod
    def _k(provider: str, model: str, part: str) -> str:
        return f"cb:{provider}:{model}:{part}"

    def state(self, provider: str, model: str) -> str:
        try:
            open_until = self.r.get(self._k(provider, model, "open_until"))
        except redis.RedisError:
            return "closed"
        if open_until is None:
            return "closed"
        return "open" if float(open_until) > time.time() else "half_open"

    def allow(self, provider: str, model: str) -> bool:
        st = self.state(provider, model)
        if st == "closed":
            return True
        if st == "open":
            return False
        try:  # half-open: exactly one probe at a time
            return bool(self.r.set(self._k(provider, model, "probe"), "1", nx=True, ex=self.cfg.open_s))
        except redis.RedisError:
            return True

    def record_success(self, provider: str, model: str, latency_ms: int) -> None:
        try:
            pipe = self.r.pipeline()
            pipe.delete(
                self._k(provider, model, "open_until"),
                self._k(provider, model, "probe"),
                self._k(provider, model, "failures"),
            )
            pipe.hincrby(self._k(provider, model, "health"), "ok", 1)
            pipe.hset(self._k(provider, model, "health"), "last_latency_ms", str(latency_ms))
            pipe.expire(self._k(provider, model, "health"), 3600)
            pipe.execute()
            AI_CIRCUIT_OPEN.labels(provider, model).set(0)
        except redis.RedisError:
            log.warning("circuit_redis_unavailable")

    def record_failure(self, provider: str, model: str) -> bool:
        """Returns True if this failure opened the circuit."""
        try:
            fk = self._k(provider, model, "failures")
            pipe = self.r.pipeline()
            pipe.incr(fk)
            pipe.expire(fk, self.cfg.window_s)
            pipe.hincrby(self._k(provider, model, "health"), "fail", 1)
            pipe.expire(self._k(provider, model, "health"), 3600)
            count = int(pipe.execute()[0])
            half_open = self.state(provider, model) == "half_open"
            if count >= self.cfg.failure_threshold or half_open:
                self.r.set(
                    self._k(provider, model, "open_until"),
                    time.time() + self.cfg.open_s,
                    ex=self.cfg.open_s * 10,
                )
                self.r.delete(self._k(provider, model, "probe"), fk)
                AI_CIRCUIT_OPEN.labels(provider, model).set(1)
                return True
        except redis.RedisError:
            log.warning("circuit_redis_unavailable")
        return False

    def health(self, provider: str, model: str) -> dict[str, object]:
        try:
            h = self.r.hgetall(self._k(provider, model, "health"))
        except redis.RedisError:
            return {"state": "unknown"}
        ok, fail = int(h.get("ok", 0)), int(h.get("fail", 0))
        total = ok + fail
        return {
            "state": self.state(provider, model),
            "success_rate_1h": round(ok / total, 3) if total else None,
            "attempts_1h": total,
            "last_latency_ms": int(h["last_latency_ms"]) if "last_latency_ms" in h else None,
        }

    def reset(self, provider: str, model: str) -> None:
        self.r.delete(*[self._k(provider, model, p) for p in ("open_until", "probe", "failures", "health")])
