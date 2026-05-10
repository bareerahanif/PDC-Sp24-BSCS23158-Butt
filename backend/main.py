# backend/main.py
# BSCS23157 - PDC Assignment 02
# StudySync FastAPI app — circuit breaker demo

from fastapi import FastAPI
from pydantic import BaseModel

from middleware import StudentHeaderMiddleware
from llm import ask_llm, breaker, cache

app = FastAPI(
    title="StudySync API",
    description="PDC A02 — Circuit Breaker demo (BSCS23157)",
    version="1.0.0",
)
app.add_middleware(StudentHeaderMiddleware)


# ── request/response models ───────────────────────────────────────────────────

class PromptRequest(BaseModel):
    prompt: str
    simulate_failure: bool = False


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Quick liveness check — stays responsive even when LLM is down."""
    return {
        "status": "healthy",
        "circuit": breaker.state.value,
        "cache_entries": cache.size(),
    }


@app.get("/breaker/status")
async def breaker_status():
    """Detailed circuit breaker diagnostics."""
    return breaker.stats


@app.post("/breaker/reset")
async def breaker_reset():
    """Manually reset the circuit breaker (for testing/ops)."""
    breaker.reset()
    return {"message": "Circuit breaker reset to CLOSED", "state": breaker.state.value}


@app.post("/ask")
async def ask(req: PromptRequest):
    """
    Send a prompt to the LLM.
    Pass simulate_failure=true to trigger the circuit breaker during a demo.
    """
    result = await ask_llm(req.prompt, req.simulate_failure)
    return result
