"""In-memory registry of running requests, read by GET /progress. One instance (Cloud Run max 1), so memory is enough."""

import re
import time

from atlas.context import RequestContext

MAX_RUNS = 20
TTL_S = 600  # finished runs stay readable this long
RUN_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class RunRegistry:
    def __init__(self):
        self._runs: dict[str, tuple[RequestContext, list[float]]] = {}  # run_id -> (ctx, [finished_at or 0])

    def _prune(self):
        now = time.monotonic()
        for k in [k for k, (_c, fin) in self._runs.items() if fin[0] and now - fin[0] > TTL_S]:
            del self._runs[k]
        while len(self._runs) > MAX_RUNS:  # oldest first (dicts keep insertion order)
            del self._runs[next(iter(self._runs))]

    def start(self, run_id: str | None, ctx: RequestContext) -> None:
        if run_id and RUN_ID.match(run_id):
            self._runs[run_id] = (ctx, [0.0])
            self._prune()

    def finish(self, run_id: str | None, status: str = "done") -> None:
        if run_id in self._runs:
            ctx, fin = self._runs[run_id]
            fin[0] = time.monotonic()
            ctx.run.status = status
            ctx.run.stage = "done" if status == "done" else "failed"

    def get(self, run_id: str, since: int = 0) -> dict:
        self._prune()
        if run_id not in self._runs:
            return {"status": "unknown", "stage": "", "elapsed_s": 0, "rounds": 0, "tool_calls": [], "next": since}
        ctx, _ = self._runs[run_id]
        calls = list(ctx.tool_calls)
        since = max(0, since)
        return {"status": ctx.run.status, "stage": ctx.run.stage, "elapsed_s": round(ctx.elapsed(), 1), "rounds": ctx.rounds_used,
                "tool_calls": calls[since:], "next": len(calls)}


REGISTRY = RunRegistry()
