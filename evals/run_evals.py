"""End-to-end evals E1-E8. String/regex/structural checks only, no LLM judge.

Local (default):  uv run python -m evals.run_evals [--only E2]
Deployed:         uv run python -m evals.run_evals --url https://<service> --token "$(gcloud auth print-identity-token)"
  (IAP usually rejects CLI tokens; for the deployed app click through in a signed-in browser instead.)
Set ATLAS_FAULT=timeout|error to check the partial-report path.
"""

import argparse
import asyncio
import json
import re
import sys
import time
import uuid
from pathlib import Path

from evals.common import auth_headers

CASES = Path(__file__).with_name("cases.jsonl")


def researcher_calls(calls):
    return [c for c in calls if "Researcher" in c["agent"]]


def dispatches(calls):
    return [c for c in calls if c["name"] in ("dispatch_researchers", "auto_gap_round")]  # an automatic gap round counts as a round


def check(name: str, text: str, calls: list[dict]) -> tuple[bool, str]:
    kind, _, arg = name.partition(":")
    if kind == "contains":
        return arg in text, f"contains {arg!r}"
    if kind == "regex":
        return re.search(arg, text) is not None, f"regex {arg!r}"
    if kind == "called":
        return any(c["name"] == arg for c in calls), f"called {arg}"
    if kind == "not_called":
        return not any(c["name"] == arg for c in calls), f"not called {arg}"
    if kind == "no_researchers":
        return not researcher_calls(calls), "no researcher calls"
    if kind == "no_audit":
        return "_Audit:" not in text, "audit clean"
    if kind == "has_sources":
        return "### Sources" in text, "Sources section"
    if kind == "every_call_has_agent":
        return all(c.get("agent") for c in calls), "every tool call has agent"
    if kind == "citations_resolve":
        listed = set(re.findall(r"^- \[(S\d+)\]", text, re.M))
        cited = set(re.findall(r"\[(S\d+)\]", text))
        return cited <= listed and bool(listed), f"all {len(cited)} cited ids listed ({len(listed)} sources)"
    if kind == "parallel_researchers":
        rs = researcher_calls(calls)
        order = [c["agent"] for c in rs]
        names = list(dict.fromkeys(order))
        # interleaved calls (A ... B ... A) can only happen if the runs overlap in time
        interleaved = any(order.index(a) < order.index(b) < len(order) - 1 - order[::-1].index(a) for a in names for b in names if a != b)
        return len(names) >= 3 and interleaved, f"{len(names)} researchers, interleaved={interleaved}"
    if kind == "rounds_ok":
        n = len(dispatches(calls))
        reason_none_needed = any(c["agent"] == "Analyst" and "(0 fillable)" in c["result"] for c in calls)
        return (2 <= n <= 3) or (n == 1 and reason_none_needed), f"{n} dispatches, no-fillable-gap reason={reason_none_needed}"
    raise ValueError(f"unknown check {name}")


async def run_local(turns, session_id):
    from agents import set_tracing_disabled
    from atlas.orchestrator import answer
    set_tracing_disabled(True)
    for t in turns:
        a = await answer(t["say"], session_id)
        yield t, a.text, a.tool_calls


async def run_remote(turns, session_id, url, token):
    import httpx
    async with httpx.AsyncClient(timeout=300, headers=auth_headers(token)) as client:
        for t in turns:
            r = await client.post(url.rstrip("/") + "/chat", json={"message": t["say"], "session_id": session_id})
            r.raise_for_status()
            d = r.json()
            yield t, d["response"], d["tool_calls"]


async def run_case(case, url, token):
    sid = f"eval-{case['id']}-{uuid.uuid4().hex[:6]}"
    results, t0 = [], time.monotonic()
    gen = run_remote(case["turns"], sid, url, token) if url else run_local(case["turns"], sid)
    try:
        async for turn, text, calls in gen:
            for name in turn["checks"]:
                ok, label = check(name, text, calls)
                results.append((ok, label))
    except Exception as exc:
        results.append((False, f"exception {type(exc).__name__}: {str(exc)[:120]}"))
    elapsed = time.monotonic() - t0
    results.append((elapsed < 240, f"latency {elapsed:.0f}s < 240s"))
    return results, elapsed


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated case ids")
    ap.add_argument("--url")
    ap.add_argument("--token")
    args = ap.parse_args()
    cases = [json.loads(line) for line in CASES.read_text().splitlines() if line.strip()]
    if args.only:
        cases = [c for c in cases if c["id"] in args.only.split(",")]
    failed = 0
    print(f"{'case':<5} {'result':<6} {'time':>6}  checks")
    for case in cases:
        results, elapsed = await run_case(case, args.url, args.token)
        good = all(ok for ok, _ in results)
        failed += not good
        print(f"{case['id']:<5} {'PASS' if good else 'FAIL':<6} {elapsed:>5.0f}s  " + "; ".join(("ok " if ok else "FAIL ") + label for ok, label in results))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
