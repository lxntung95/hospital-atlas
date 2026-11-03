import asyncio
import contextlib
import json
import uuid
from pathlib import Path

import uvicorn
from agents import Agent, RunHooks, Runner, SQLiteSession, set_tracing_disabled
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from atlas import cms
from atlas.config import MODEL, SETTINGS
from atlas.http import get_client

# Traces upload to OpenAI by default, which needs an OpenAI key. We're on Gemini.
set_tracing_disabled(True)

# --- Config (model and settings live in atlas/config.py) ---

SESSIONS_DB = "conversations.db"  # in memory on Cloud Run, so it lasts as long as the instance (we run one instance)

# --- The Agent (M0 placeholder: the Lead and its researchers replace this) ---

agent = Agent(
    name="Lead",
    instructions="You are Hospital Atlas, a placeholder while the research agents are being built. Reply briefly.",
    model=MODEL,
    model_settings=SETTINGS,
)


class RecordToolCalls(RunHooks):
    """Records each tool call for the page to show, tagged with the agent that made it.

    Make a new one per request: it holds this run's calls.
    """

    def __init__(self):
        self.tool_calls = []

    async def on_tool_end(self, context, agent, tool, result):
        try:
            args = json.loads(context.tool_arguments)
        except (TypeError, ValueError):
            args = {"raw": str(context.tool_arguments)}
        self.tool_calls += [{"agent": agent.name, "name": tool.name, "args": args, "result": str(result)[:800]}]


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
    hooks = RecordToolCalls()
    try:
        result = await Runner.run(
            agent, request.message, session=SQLiteSession(session_id, SESSIONS_DB), hooks=hooks, max_turns=8
        )
        response = str(result.final_output)
    except Exception as e:
        response = f"Model call failed: {type(e).__name__}: {str(e)[:300]}"
    return ChatResponse(response=response, session_id=session_id, tool_calls=hooks.tool_calls)


@app.post("/clear")
async def clear(session_id: str):
    await SQLiteSession(session_id, SESSIONS_DB).clear_session()
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
