"""Phase 5: clarification guard, safety net, fault injection, litellm pass-through. Offline, stubbed model calls."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from atlas import config, orchestrator
from atlas.schemas import Finding
from tests.conftest import call
from tests.test_dispatch import prepare, task

OPTIONS = ["Hip replacement cost in Brooklyn", "Heart failure quality", "Compare the Bronx hospitals"]


async def test_clarify_tool_once_and_only_before_research(ctx):
    r = await call(orchestrator.ask_clarifying_question, ctx, question="What do you care about?", options=OPTIONS)
    assert r.startswith("## What do you care about?") and ctx.clarified and "- Hip replacement cost in Brooklyn" in r
    ctx.prev_clarified = True  # never twice in a row
    assert "already asked" in json.loads(await call(orchestrator.ask_clarifying_question, ctx, question="again?", options=OPTIONS))["error"]


async def test_clarify_refused_after_dispatch_or_with_too_few_options(ctx):
    ctx.rounds_used = 1
    assert "error" in json.loads(await call(orchestrator.ask_clarifying_question, ctx, question="q", options=OPTIONS))
    ctx.rounds_used = 0
    assert "error" in json.loads(await call(orchestrator.ask_clarifying_question, ctx, question="q", options=["a"]))


def test_vague_detection_is_deterministic(ctx):
    from atlas import crosswalk
    assert crosswalk.detect("Which NY hospitals are the best?").vague
    assert not crosswalk.detect("heart failure readmissions").vague
    assert not crosswalk.detect("Is Mass General in Boston good?").vague  # out of scope, not vague


async def test_fault_injection_timeout_and_error(ctx, monkeypatch):
    prepare(ctx)

    async def fake(agent, input, context, hooks, max_turns):
        return SimpleNamespace(final_output=Finding(task_id="x", summary="ok").model_dump_json())

    monkeypatch.setattr(orchestrator.Runner, "run", fake)
    for fault, word in (("timeout", "timed out"), ("error", "RuntimeError")):
        monkeypatch.setenv("ATLAS_FAULT", fault)
        ctx.rounds_used = 0
        out = json.loads(await call(orchestrator.dispatch_researchers, ctx, tasks=[task(1), task(2, "quality"), task(3, "quality")]))
        by = {f["task_id"]: f for f in out["findings"]}
        assert by["R1"]["status"] == "partial" and word in by["R1"]["summary"] and by["R2"]["status"] == "ok"


async def test_answer_timeout_returns_labelled_partial(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "SESSIONS_DB", str(tmp_path / "s.db"))
    monkeypatch.setattr(config, "REQUEST_S", 0.05)

    async def slow(*a, **k):
        await asyncio.sleep(5)

    monkeypatch.setattr(orchestrator.Runner, "run", slow)
    a = await orchestrator.answer("heart failure in the Bronx", "s-timeout")
    assert a.text and "could not finish" in a.text and "time limit" in a.text


async def test_answer_error_with_facts_writes_from_gathered_data(ctx, monkeypatch, tmp_path):
    from tests.test_analyst import hf_bronx
    monkeypatch.setattr(config, "SESSIONS_DB", str(tmp_path / "s.db"))
    await hf_bronx(ctx)
    ctx.rounds_used = 1
    text = await orchestrator._rescue(ctx, "boom", write=False)
    assert "Partial results" in text and "### Sources" in text


async def test_no_stack_trace_on_exception(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "SESSIONS_DB", str(tmp_path / "s.db"))

    async def boom(*a, **k):
        raise ValueError("secret internals")

    monkeypatch.setattr(orchestrator.Runner, "run", boom)
    a = await orchestrator.answer("hello there", "s-err")
    assert "Traceback" not in a.text and "secret internals" not in a.text


async def test_vague_first_turn_clarifies_then_never_twice(monkeypatch, tmp_path, ctx):
    monkeypatch.setattr(config, "SESSIONS_DB", str(tmp_path / "s.db"))
    seen = []

    async def fake(agent, input, context, hooks=None, session=None, max_turns=None):
        seen.append(agent.name + ":" + agent.tools[0].name)
        if agent is orchestrator.LEAD_CLARIFY:
            out = await call(orchestrator.ask_clarifying_question, context, question="Which?", options=OPTIONS)
            await session.add_items([{"role": "user", "content": input}])
            return SimpleNamespace(final_output=out)
        return SimpleNamespace(final_output="researched")

    monkeypatch.setattr(orchestrator.Runner, "run", fake)
    a1 = await orchestrator.answer("Which NY hospitals are the best?", "s-q3", client=ctx.client)
    assert a1.text.startswith("## Which?") and a1.ctx.clarified
    a2 = await orchestrator.answer("Which NY hospitals are best overall?", "s-q3", client=ctx.client)  # still vague, but we asked already
    assert a2.text == "researched" and seen[-1].startswith("Lead:resolve_cohort")


async def test_litellm_receives_timeout_and_retries(monkeypatch):
    import litellm
    from agents import Agent, Runner
    captured = {}

    async def fake_acompletion(**kw):
        captured.update(kw)
        raise RuntimeError("stop here")

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    with pytest.raises(Exception):
        await Runner.run(Agent(name="t", model=config.MODEL, model_settings=config.SETTINGS), "hi", max_turns=1)
    assert captured["timeout"] == 45 and captured["num_retries"] == 2 and captured["vertex_location"] == "global"


async def test_model_call_cap_is_four():
    assert config.MODEL_CALLS == 4
    gate = config._gate()
    assert gate._value == 4


async def test_partial_findings_are_labelled_in_report(ctx, monkeypatch):
    from atlas import render, validate
    from atlas.schemas import Report
    from tests.test_analyst import hf_bronx
    await hf_bronx(ctx)
    ctx.partials.append("cost task R1 (Cost Researcher R1) did not finish: timed out after 60s")
    from atlas import analyst
    await analyst.analyze(ctx)
    v = await validate.validate(Report(headline="h", claims=[], data_cannot_tell_you=["a", "b"]), ctx)
    md = render.render(v, ctx)
    assert "_Partial report:" in md and "Partial result:" in md
