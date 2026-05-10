# backend/llm.py
# BSCS23157 - PDC Assignment 02
# LLM service: wraps the external API call with circuit breaker + cache fallback

import asyncio
from breaker import CircuitBreaker, BreakerTrippedError
from response_cache import ResponseCache


# ── singletons shared across the app ─────────────────────────────────────────

breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=15)
cache = ResponseCache(capacity=256)


# ── simulated external LLM API ────────────────────────────────────────────────

async def _external_llm_call(prompt: str, fail: bool) -> str:
    """
    Simulates an external LLM API.
    When fail=True it hangs for 5 s then raises, mimicking a 60-second timeout
    in the real world (shortened here so demos don't take forever).
    """
    if fail:
        await asyncio.sleep(5)
        raise TimeoutError("LLM API did not respond within the deadline")

    await asyncio.sleep(0.15)   # realistic small network latency
    return f"[LLM] Here is a study tip for: '{prompt}'"


# ── public entry point ────────────────────────────────────────────────────────

async def ask_llm(prompt: str, simulate_failure: bool = False) -> dict:
    """
    Call the LLM with circuit-breaker protection.

    Returns a dict with:
      source  : "llm_api" | "cache" | "degraded"
      status  : "ok" | "fallback"
      response: str
    """
    try:
        answer = await breaker.call(_external_llm_call, prompt, simulate_failure)
        cache.put(prompt, answer)          # keep cache fresh on every success
        return {"source": "llm_api", "status": "ok", "response": answer}

    except BreakerTrippedError as exc:
        # Circuit is open — fail fast and serve from cache
        cached = cache.get(prompt)
        source = "cache" if cached != ResponseCache.DEGRADED_MSG else "degraded"
        return {
            "source": source,
            "status": "fallback",
            "response": cached,
            "reason": str(exc),
        }

    except Exception as exc:
        # Real failure (circuit recorded it) — also serve from cache
        cached = cache.get(prompt)
        source = "cache" if cached != ResponseCache.DEGRADED_MSG else "degraded"
        return {
            "source": source,
            "status": "fallback",
            "response": cached,
            "reason": str(exc),
        }
