import asyncio
import contextlib
import time
import uuid
from pathlib import Path

import uvicorn
from agents import SQLiteSession, set_tracing_disabled
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from atlas import cms, config
from atlas.config import SESSIONS_DB
from atlas.http import get_client
from atlas.orchestrator import answer
from atlas.progress import REGISTRY

# Traces upload to OpenAI by default, which needs an OpenAI key. We're on Gemini.
set_tracing_disabled(True)

# --- FastAPI App ---

async def warm_cache():
    """Fetch the NY slices in the background so the first question does not pay for them. Never blocks startup."""
    for spec in cms.NY_SLICES:
        with contextlib.suppress(Exception):  # a failed warm-up just means the first request fetches (or falls back)
            await get_client().get_slice(spec)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(warm_cache())
    yield
    task.cancel()
    await get_client().aclose()


app = FastAPI(lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    model: str | None = None  # must be one of GET /models
    effort: str | None = None  # low | medium | high
    run_id: str | None = None  # lets the client poll GET /progress while this request runs
    history: list[dict] | None = None  # [{role, content}] to restore a saved chat into a fresh session


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: list[dict]  # [{agent, name, args, result, t}]; sub-agent calls included
    artifacts: dict | None = None  # cohort (with coordinates), tables, charts, benchmarks, sources, facts: all derived from Facts
    meta: dict | None = None  # {model, model_label, effort, elapsed_s, rounds, served_from, notes, audit}


MAX_CONCURRENT_RUNS = 4  # model calls are capped separately (config.MODEL_CALLS); a run waits its turn rather than failing
BUSY_WAIT_S = 120  # well under Cloud Run's 600 s timeout and the graders' 5 minute wait


def message_only(text: str, session_id: str, model: str | None = None, effort: str | None = None) -> ChatResponse:
    return ChatResponse(response=text, session_id=session_id, tool_calls=[], artifacts=None, meta={"model": model, "effort": effort, "error": True})


@app.exception_handler(Exception)
async def show_errors_in_chat(request: Request, exc: Exception):
    # Auth, billing, a model that is not running: show it in the chat, not as a 500.
    return JSONResponse(message_only(f"Model call failed: {type(exc).__name__}: {str(exc)[:300]}", request.query_params.get("session_id", "")).model_dump())


@app.get("/")
async def index():
    return FileResponse(Path(__file__).parent / "web" / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "cache": get_client().status()}


@app.get("/models")
async def models():
    return {"models": [{"id": k, "label": v} for k, v in config.MODEL_CHOICES.items()],
            "efforts": [{"id": k, "label": v} for k, v in config.EFFORT_LEVELS.items()],
            "default": {"model": config.DEFAULT_MODEL, "effort": config.DEFAULT_EFFORT}}


@app.get("/progress")
async def progress(run_id: str, since: int = 0):
    return REGISTRY.get(run_id, since)


@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or str(uuid.uuid4())
    if request.model and request.model not in config.MODEL_CHOICES:
        return message_only(f"Unknown model {request.model!r}. Choose one of: {', '.join(config.MODEL_CHOICES)}.", session_id, request.model, request.effort)
    if request.effort and request.effort not in config.EFFORT_LEVELS:
        return message_only(f"Unknown effort {request.effort!r}. Choose one of: {', '.join(config.EFFORT_LEVELS)}.", session_id, request.model, request.effort)
    gate = config.loop_semaphore("runs", MAX_CONCURRENT_RUNS)
    try:
        await asyncio.wait_for(gate.acquire(), BUSY_WAIT_S)
    except asyncio.TimeoutError:
        return message_only("The service is busy with other research requests. Please try again in a minute.", session_id, request.model, request.effort)
    started = time.monotonic()
    try:
        result = await answer(request.message, session_id, model_id=request.model, effort=request.effort, history=request.history,
                              on_start=lambda ctx: REGISTRY.start(request.run_id, ctx))
        REGISTRY.finish(request.run_id, "done")
        ctx = result.ctx
        notes = sorted({s.note for s in ctx.sources.all() if s.note})
        meta = {"model": request.model or config.DEFAULT_MODEL, "model_label": config.MODEL_CHOICES.get(request.model or config.DEFAULT_MODEL, ""),
                "effort": request.effort or "default", "elapsed_s": round(time.monotonic() - started, 1), "rounds": ctx.rounds_used,
                "served_from": "degraded" if notes else "live", "notes": notes, "audit": ctx.audit}
        return ChatResponse(response=result.text, session_id=session_id, tool_calls=result.tool_calls, artifacts=ctx.artifacts, meta=meta)
    except Exception as e:
        REGISTRY.finish(request.run_id, "error")
        return message_only(f"Model call failed: {type(e).__name__}: {str(e)[:300]}", session_id, request.model, request.effort)
    finally:
        gate.release()


@app.post("/clear")
async def clear(session_id: str):
    await SQLiteSession(session_id, SESSIONS_DB).clear_session()
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
