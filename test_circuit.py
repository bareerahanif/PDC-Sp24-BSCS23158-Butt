# backend/test_circuit.py
# BSCS23158 - PDC Assignment 02
# Automated test: proves the circuit breaker works end-to-end

import asyncio
import time
import httpx

BASE = "http://localhost:8000"
OK = "✅"
FAIL = "❌"


def section(title: str):
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


async def reset_breaker(client: httpx.AsyncClient):
    r = await client.post(f"{BASE}/breaker/reset")
    assert r.json()["state"] == "closed"


# ── individual tests ──────────────────────────────────────────────────────────

async def test_student_header(client: httpx.AsyncClient):
    section("TEST 1 · X-Student-ID header present on every response")
    for path in ["/health", "/breaker/status"]:
        r = await client.get(f"{BASE}{path}")
        sid = r.headers.get("x-student-id")
        assert sid == "BSCS23158", f"Missing or wrong header on {path}: {sid!r}"
        print(f"  {OK}  {path}  →  X-Student-ID: {sid}")


async def test_healthy_request(client: httpx.AsyncClient):
    section("TEST 2 · Normal request succeeds (circuit CLOSED)")
    r = await client.post(f"{BASE}/ask", json={"prompt": "what is recursion?"})
    data = r.json()
    print(f"  Response: {data}")
    assert data["status"] == "ok", f"Expected ok, got {data['status']}"
    assert data["source"] == "llm_api"
    print(f"  {OK}  Got real LLM response in < 1 s")


async def test_before_circuit_breaker(client: httpx.AsyncClient):
    """
    Show the PROBLEM: without a circuit breaker the server hangs.
    We do ONE simulated failure so the audience can see the delay.
    """
    section("TEST 3 · BEFORE fix — single failing call blocks for ~5 s")
    print("  Sending 1 request with simulate_failure=True ...")
    t0 = time.perf_counter()
    r = await client.post(
        f"{BASE}/ask",
        json={"prompt": "help", "simulate_failure": True},
        timeout=30,
    )
    elapsed = time.perf_counter() - t0
    data = r.json()
    print(f"  Response: {data}")
    print(f"  ⏱  Took {elapsed:.2f}s  (simulates real 60-second hang)")
    # Circuit now has 1 failure recorded
    await reset_breaker(client)   # clean slate before next test


async def test_circuit_trips(client: httpx.AsyncClient):
    section("TEST 4 · Circuit trips after 3 failures → OPEN")
    print("  Sending 3 failing requests to trip the breaker...")

    for i in range(1, 4):
        t0 = time.perf_counter()
        r = await client.post(
            f"{BASE}/ask",
            json={"prompt": "study tip", "simulate_failure": True},
            timeout=30,
        )
        elapsed = time.perf_counter() - t0
        data = r.json()
        status_r = await client.get(f"{BASE}/breaker/status")
        state = status_r.json()["state"]
        print(f"  Failure {i}: source={data['source']}  ⏱ {elapsed:.2f}s  circuit={state}")

    status_r = await client.get(f"{BASE}/breaker/status")
    state = status_r.json()["state"]
    assert state == "open", f"Expected open, got {state}"
    print(f"\n  {OK}  Circuit is now OPEN")


async def test_fallback_instant(client: httpx.AsyncClient):
    section("TEST 5 · AFTER fix — circuit OPEN, fallback returns instantly")
    print("  Sending normal request while circuit is OPEN ...")
    t0 = time.perf_counter()
    r = await client.post(
        f"{BASE}/ask",
        json={"prompt": "study tip", "simulate_failure": False},
        timeout=5,
    )
    elapsed = time.perf_counter() - t0
    data = r.json()
    print(f"  Response: {data}")
    print(f"  ⏱  Took {elapsed*1000:.0f} ms  (should be < 50 ms)")
    assert data["status"] == "fallback", f"Expected fallback, got {data['status']}"
    assert elapsed < 1.0, f"Fallback too slow: {elapsed:.2f}s"
    print(f"  {OK}  Fallback served instantly — server never blocked")


async def test_health_stays_up(client: httpx.AsyncClient):
    section("TEST 6 · /health stays responsive while circuit is OPEN")
    r = await client.get(f"{BASE}/health")
    data = r.json()
    print(f"  /health: {data}")
    assert data["status"] == "healthy"
    assert data["circuit"] == "open"
    print(f"  {OK}  Server healthy even though LLM backend is down")


# ── runner ────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "═" * 55)
    print("  StudySync Circuit Breaker — End-to-End Demo")
    print("  BSCS23157  ·  PDC Assignment 02")
    print("═" * 55)

    async with httpx.AsyncClient(timeout=60) as client:
        # Sanity check: is the server running?
        try:
            await client.get(f"{BASE}/health")
        except httpx.ConnectError:
            print(f"\n{FAIL}  Could not reach {BASE}. Is the server running?")
            print("  Run:  uvicorn main:app --reload\n")
            return

        await reset_breaker(client)

        await test_student_header(client)
        await test_healthy_request(client)
        await test_before_circuit_breaker(client)
        await test_circuit_trips(client)
        await test_fallback_instant(client)
        await test_health_stays_up(client)

    print("\n" + "═" * 55)
    print(f"  {OK}  ALL TESTS PASSED")
    print("═" * 55 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
