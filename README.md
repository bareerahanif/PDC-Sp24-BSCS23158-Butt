# Bia [Last Name] — BSCS23157
# PDC-Sp24-BSCS23157-[YourLastName]

## StudySync — Circuit Breaker for LLM Fault Tolerance

### Problem Solved
**Fault Tolerance (Problem 3):** The LLM API is a synchronous blocking call.
When the external service hangs (60-second timeout), FastAPI worker threads
stall, the connection pool exhausts, and the entire server becomes unresponsive.

### Solution
A three-state **Circuit Breaker** (CLOSED → OPEN → HALF_OPEN) wraps every
outbound LLM call. After `failure_threshold` consecutive failures the circuit
opens and subsequent requests receive an instant cached/degraded fallback —
no thread is ever blocked waiting on a dead API.

```
CLOSED ──(3 failures)──▶ OPEN ──(15s cooldown)──▶ HALF_OPEN
  ▲                                                     │
  └─────────────────(probe succeeds)───────────────────┘
```

### File Structure
```
backend/
├── main.py            # FastAPI app + routes
├── middleware.py      # X-Student-ID header injection
├── breaker.py         # Circuit breaker state machine
├── llm.py             # LLM service layer (breaker + cache)
├── response_cache.py  # LRU prompt → response cache
├── test_circuit.py    # End-to-end demo test
└── requirements.txt
```

### How to Run

**1. Install dependencies**
```bash
cd backend
pip install -r requirements.txt
```

**2. Start the server**
```bash
uvicorn main:app --reload
```

Server starts at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

**3. Run the demo test** (in a second terminal)
```bash
python test_circuit.py
```

The test script will:
1. Verify `X-Student-ID: BSCS23157` header on every response
2. Show a normal request succeeding through the LLM
3. Show the BEFORE state — one failing call blocks for ~5 s
4. Trip the circuit with 3 consecutive failures
5. Show the AFTER state — instant fallback with circuit OPEN
6. Confirm `/health` stays responsive throughout

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness + circuit state |
| GET | `/breaker/status` | Full breaker diagnostics |
| POST | `/breaker/reset` | Reset to CLOSED (testing) |
| POST | `/ask` | Send a prompt to the LLM |

### Custom Header
Every response includes:
```
X-Student-ID: BSCS23157
```
Implemented in `middleware.py` via `StudentHeaderMiddleware`.
