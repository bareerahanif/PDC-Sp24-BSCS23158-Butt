# backend/breaker.py
# BSCS23158 - PDC Assignment 02
# Circuit Breaker state machine for LLM fault tolerance

import time
from enum import Enum


class State(Enum):
    CLOSED = "closed"       # Normal operation - requests flow through
    OPEN = "open"           # Failing fast - no requests attempted
    HALF_OPEN = "half_open" # Probing - one request allowed to test recovery


class BreakerTrippedError(Exception):
    """Raised when a request is rejected because the circuit is OPEN."""
    pass


class CircuitBreaker:
    """
    Three-state circuit breaker.

    CLOSED  ──(threshold failures)──▶  OPEN
    OPEN    ──(cooldown elapsed)───▶  HALF_OPEN
    HALF_OPEN ──(success)──────────▶  CLOSED
    HALF_OPEN ──(failure)──────────▶  OPEN
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: int = 30,
    ):
        self._state = State.CLOSED
        self._failures = 0
        self._threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._opened_at: float = 0.0
        self._total_requests = 0
        self._total_fallbacks = 0

    # ── public read-only properties ──────────────────────────────────────────

    @property
    def state(self) -> State:
        return self._state

    @property
    def failures(self) -> int:
        return self._failures

    @property
    def stats(self) -> dict:
        return {
            "state": self._state.value,
            "failures": self._failures,
            "threshold": self._threshold,
            "cooldown_seconds": self._cooldown,
            "seconds_until_probe": max(
                0.0,
                round(self._cooldown - (time.monotonic() - self._opened_at), 1)
            ) if self._state == State.OPEN else 0.0,
            "total_requests": self._total_requests,
            "total_fallbacks": self._total_fallbacks,
        }

    # ── core call wrapper ────────────────────────────────────────────────────

    async def call(self, coro_func, *args, **kwargs):
        """
        Attempt to call an async function through the circuit breaker.
        Raises BreakerTrippedError immediately if the circuit is OPEN.
        """
        self._total_requests += 1
        self._maybe_probe()

        if self._state == State.OPEN:
            self._total_fallbacks += 1
            raise BreakerTrippedError(
                f"Circuit OPEN – failing fast. "
                f"Retry in {self.stats['seconds_until_probe']}s."
            )

        try:
            result = await coro_func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as exc:
            self._record_failure()
            raise exc

    # ── internal state transitions ───────────────────────────────────────────

    def _maybe_probe(self):
        """If OPEN and cooldown has elapsed, move to HALF_OPEN."""
        if (
            self._state == State.OPEN
            and time.monotonic() - self._opened_at >= self._cooldown
        ):
            self._state = State.HALF_OPEN
            print("[BREAKER] → HALF_OPEN  (probing recovery)")

    def _record_success(self):
        if self._state in (State.HALF_OPEN, State.CLOSED):
            self._failures = 0
            self._state = State.CLOSED
            print("[BREAKER] → CLOSED  (healthy)")

    def _record_failure(self):
        self._failures += 1
        self._opened_at = time.monotonic()
        if self._failures >= self._threshold or self._state == State.HALF_OPEN:
            self._state = State.OPEN
            print(f"[BREAKER] → OPEN  ({self._failures} failures)")

    def reset(self):
        """Manually reset the breaker (useful for testing)."""
        self._state = State.CLOSED
        self._failures = 0
        self._opened_at = 0.0
        print("[BREAKER] Manual reset → CLOSED")
