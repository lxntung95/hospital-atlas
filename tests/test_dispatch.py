"""dispatch_researchers with stubbed researcher runs: parallelism, partial findings, validation and round limits."""

import asyncio
import json
import time
from types import SimpleNamespace

from atlas import config, orchestrator
from atlas.schemas import Finding, ResearchTask
from tests.conftest import call


def task(i, kind="cost"):
    return ResearchTask(id=f"R{i}", kind=kind, question="q", cohort_handle="C1", drg_codes=[291], measure_ids=[]).model_dump()


def prepare(ctx):
    ctx.cohorts["C1"] = {"ccns": ["330059"], "label": "x"}


def stub_run(monkeypatch, behaviour):
    async def fake(agent, input, context, hooks, max_turns):
        await behaviour(agent, context)
        t = ResearchTask.model_validate_json(input)
        return SimpleNamespace(final_output=Finding(task_id=t.id, summary=f"done by {agent.name}").model_dump_json())
    monkeypatch.setattr(orchestrator.Runner, "run", fake)


async def test_three_researchers_run_in_parallel(ctx, monkeypatch):
    prepare(ctx)

    async def work(agent, context):
        await asyncio.sleep(0.3)

    stub_run(monkeypatch, work)
    t0 = time.monotonic()
    out = json.loads(await call(orchestrator.dispatch_researchers, ctx, tasks=[task(1), task(2, "quality"), task(3, "quality")]))
    assert time.monotonic() - t0 < 0.8  # sequential would be >= 0.9
    assert [f["agent"] for f in out["findings"]] == ["Cost Researcher R1", "Quality Researcher R2", "Quality Researcher R3"]
    assert out["round"] == 1 and out["rounds_left"] == 2 and all(f["status"] == "ok" for f in out["findings"])


async def test_error_and_timeout_become_partial_findings(ctx, monkeypatch):
    prepare(ctx)
    monkeypatch.setattr(config, "RESEARCHER_S", 0.2)

    async def work(agent, context):
        if "R1" in agent.name:
            raise RuntimeError("boom")
        if "R2" in agent.name:
            await asyncio.sleep(5)
        context.tables.add("kept", [{"a": 1}], owner=context.owner, source_ids=[])

    stub_run(monkeypatch, work)
    out = json.loads(await call(orchestrator.dispatch_researchers, ctx, tasks=[task(1), task(2), task(3)]))
    by = {f["task_id"]: f for f in out["findings"]}
    assert by["R1"]["status"] == "partial" and "RuntimeError" in by["R1"]["summary"]
    assert by["R2"]["status"] == "partial" and "timed out" in by["R2"]["summary"]
    assert by["R3"]["status"] == "ok"


async def test_partial_keeps_tables_stored_before_failure(ctx, monkeypatch):
    prepare(ctx)

    async def work(agent, context):
        context.tables.add("kept", [{"a": 1}], owner=context.owner, source_ids=["S1"])
        raise RuntimeError("late failure")

    stub_run(monkeypatch, work)
    out = json.loads(await call(orchestrator.dispatch_researchers, ctx, tasks=[task(1), task(2), task(3)]))
    assert all(f["status"] == "partial" and len(f["table_handles"]) == 1 for f in out["findings"])


async def test_validation_errors(ctx, monkeypatch):
    prepare(ctx)
    stub_run(monkeypatch, lambda a, c: asyncio.sleep(0))
    assert "error" in json.loads(await call(orchestrator.dispatch_researchers, ctx, tasks=[task(1), task(2)]))  # round 1 needs 3
    assert "error" in json.loads(await call(orchestrator.dispatch_researchers, ctx, tasks=[task(i) for i in range(5)]))  # too many
    bad = task(1) | {"cohort_handle": "C9"}
    assert "error" in json.loads(await call(orchestrator.dispatch_researchers, ctx, tasks=[bad, task(2)]))
    assert ctx.rounds_used == 0  # rejected calls do not use a round


async def test_round_cap_and_budget(ctx, monkeypatch):
    prepare(ctx)
    stub_run(monkeypatch, lambda a, c: asyncio.sleep(0))
    assert "findings" in json.loads(await call(orchestrator.dispatch_researchers, ctx, tasks=[task(1), task(2), task(3)]))
    for _ in range(config.MAX_GAP_ROUNDS):  # gap rounds may be a single task
        assert "findings" in json.loads(await call(orchestrator.dispatch_researchers, ctx, tasks=[task(1)]))
    r = json.loads(await call(orchestrator.dispatch_researchers, ctx, tasks=[task(1), task(2), task(3)]))
    assert "round limit" in r["error"]
    ctx.rounds_used = 0
    ctx.budget_s = 10  # less than the writer reserve
    assert "budget exhausted" in json.loads(await call(orchestrator.dispatch_researchers, ctx, tasks=[task(1), task(2), task(3)]))["error"]


async def test_hooks_record_agent_and_time(ctx):
    from atlas.context import RecordToolCalls
    tc = SimpleNamespace(tool_arguments='{"q": 1}', context=ctx)
    await RecordToolCalls().on_tool_end(tc, SimpleNamespace(name="Cost Researcher R1"), SimpleNamespace(name="get_drg_costs"), "x" * 2000)
    c = ctx.tool_calls[0]
    assert c["agent"] == "Cost Researcher R1" and c["args"] == {"q": 1} and len(c["result"]) == 800 and "t" in c


async def test_deterministic_cohort_fallback_when_retriever_fails(ctx, monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("model down")

    monkeypatch.setattr(orchestrator.Runner, "run", boom)
    out = json.loads(await call(orchestrator.resolve_cohort, ctx, request="Compare Montefiore with other Bronx hospitals on heart failure"))
    assert out["focus_hospitals"][0]["ccn"] == "330059" and 291 in out["drg_codes"] and "MORT_30_HF" in out["measure_ids"]
    assert "330059" in ctx.cohorts[out["cohort_handle"]]["ccns"] and out["n"] >= 3


async def test_deterministic_fallback_flags_out_of_scope(ctx, monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("model down")

    monkeypatch.setattr(orchestrator.Runner, "run", boom)
    out = json.loads(await call(orchestrator.resolve_cohort, ctx, request="How does Boston do on knee replacement?"))
    assert out["unresolved"] and "boston" in out["unresolved"][0]
