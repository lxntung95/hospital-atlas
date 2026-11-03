import asyncio
import contextlib
import uuid
from pathlib import Path

import uvicorn
from agents import SQLiteSession, set_tracing_disabled
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from atlas import cms
from atlas.config import SESSIONS_DB
from atlas.http import get_client
from atlas.orchestrator import answer

# Traces upload to OpenAI by default, which needs an OpenAI key. We're on Gemini.
set_tracing_disabled(True)

# --- FastAPI App ---

async def warm_cache():
    """Fetch the NY slices in the background so the first question does not pay for them. Never blocks startup."""
    for fetch in (cms.general_info_ny, cms.ny_inpatient, cms.hrrp_ny, cms.complications_ny, cms.complications_national, cms.hcahps_star_ny):
        with contextlib.suppress(Exception):  # a failed warm-up just means the first request fetches (or falls back)
            await fetch()


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


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: list[dict]  # [{agent, name, args, result}]; sub-agent calls included


@app.exception_handler(Exception)
async def show_errors_in_chat(request: Request, exc: Exception):
    # Auth, billing, a model that is not running: show it in the chat, not as a 500.
    return JSONResponse({
        "response": f"Model call failed: {type(exc).__name__}: {str(exc)[:300]}",
        "session_id": request.query_params.get("session_id", ""),
        "tool_calls": [],
    })


@app.get("/")
async def index():
    return FileResponse(Path(__file__).parent / "web" / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "cache": get_client().status()}


@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or str(uuid.uuid4())
    try:
        result = await answer(request.message, session_id)
        return ChatResponse(response=result.text, session_id=session_id, tool_calls=result.tool_calls)
    except Exception as e:
        return ChatResponse(response=f"Model call failed: {type(e).__name__}: {str(e)[:300]}", session_id=session_id, tool_calls=[])


@app.post("/clear")
async def clear(session_id: str):
    await SQLiteSession(session_id, SESSIONS_DB).clear_session()
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
