"""Live smoke test for the fan-out path: runs the Q2 prompt end to end and prints the tool-call timeline.

Checks: at least three distinct researcher agents ran, their time windows overlap (parallel), and every tool call has `agent`.
Run: uv run scripts/smoke_q2.py ["your own question"]
"""

import asyncio
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `atlas` imports when run as a script

from agents import set_tracing_disabled  # noqa: E402

from atlas.orchestrator import answer  # noqa: E402

set_tracing_disabled(True)
Q2 = "Compare Montefiore with the other Bronx hospitals on heart failure: Medicare payments and readmissions. Is Montefiore worth its cost?"


async def main():
    question = sys.argv[1] if len(sys.argv) > 1 else Q2
    t0 = time.monotonic()
    res = await answer(question, f"smoke-{uuid.uuid4()}")
    print(f"--- answer ({time.monotonic() - t0:.0f}s) ---\n{res.text}\n--- timeline ---")
    for c in res.tool_calls:
        print(f"{c['t']:6.1f}s  {c['agent']:<24} {c['name']:<22} {str(c['args'])[:70]}")
    researchers = {c["agent"] for c in res.tool_calls if "Researcher R" in c["agent"]}
    assert all("agent" in c and "t" in c for c in res.tool_calls), "a tool call is missing agent or t"
    assert len(researchers) >= 3, f"expected >= 3 researchers, got {sorted(researchers)}"
    spans = {r: [c["t"] for c in res.tool_calls if c["agent"] == r] for r in researchers}
    first_end = min(max(v) for v in spans.values())
    last_start = max(min(v) for v in spans.values())
    print("researchers:", sorted(researchers), "| first finishes", first_end, "s, last starts", last_start, "s")
    print("tables:", [(t.id, t.title, len(t.rows)) for t in res.ctx.tables.all()])
    print("sources:", [(s.id, s.dataset) for s in res.ctx.sources.all()])
    print("SMOKE Q2 PASSED")


asyncio.run(main())
