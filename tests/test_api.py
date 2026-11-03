"""Phase 6: request/response additions, allowlist, effort mapping, progress registry, history seeding, artifacts. Offline."""

import time
from types import SimpleNamespace

import httpx
import pytest
from agents import SQLiteSession

import app as app_module
from atlas import analyst, cms, config, orchestrator, progress, render
from atlas.context import RequestContext
from tests.test_analyst import hf_bronx


@pytest.fixture
def api():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app_module.app), base_url="http://t")


@pytest.fixture
def stub_answer(monkeypatch, ctx):
    seen = {}

    async def fake(message, session_id, client=None, model_id=None, effort=None, history=None, on_start=None):
        seen.update(model_id=model_id, effort=effort, history=history)
        c = RequestContext(client=ctx.client)
        c.tool_calls.append({"agent": "Lead", "name": "x", "args": {}, "result": "", "t": 0.1})
        if on_start:
            on_start(c)
        return orchestrator.Answer("hello", c.tool_calls, c)

    monkeypatch.setattr(app_module, "answer", fake)
    return seen


async def test_old_request_shape_still_works(api, stub_answer):
    r = (await api.post("/chat", json={"message": "hi"})).json()
    assert {"response", "session_id", "tool_calls", "artifacts", "meta"} <= set(r) and r["tool_calls"][0]["agent"] == "Lead"
    assert r["meta"]["model"] == config.DEFAULT_MODEL and r["meta"]["effort"] == "default" and "elapsed_s" in r["meta"]


async def test_models_endpoint(api):
    d = (await api.get("/models")).json()
    assert d["default"]["model"] in [m["id"] for m in d["models"]]
    assert [e["id"] for e in d["efforts"]] == ["low", "medium", "high"]


async def test_unknown_model_or_effort_is_a_chat_message_not_a_500(api, stub_answer):
    r = await api.post("/chat", json={"message": "hi", "model": "nope"})
    assert r.status_code == 200 and "Unknown model" in r.json()["response"] and r.json()["meta"]["error"]
    r = await api.post("/chat", json={"message": "hi", "effort": "extreme"})
    assert "Unknown effort" in r.json()["response"] and stub_answer == {}


async def test_known_model_and_effort_forwarded(api, stub_answer):
    mid = list(config.MODEL_CHOICES)[-1]
    await api.post("/chat", json={"message": "hi", "model": mid, "effort": "high", "history": [{"role": "user", "content": "a"}]})
    assert stub_answer == {"model_id": mid, "effort": "high", "history": [{"role": "user", "content": "a"}]}


def test_build_model_allowlist_and_effort_mapping():
    with pytest.raises(ValueError):
        config.build_model("vertex_ai/not-a-model")
    assert config.build_model(config.DEFAULT_MODEL) is config.build_model(config.DEFAULT_MODEL)
    for e in config.EFFORT_LEVELS:
        assert config.effort_settings(config.SETTINGS, e).reasoning.effort == e
    with pytest.raises(ValueError):
        config.effort_settings(config.SETTINGS, "x")


def test_tuned_clones_without_mutating_shared_agents(ctx):
    base_model, base_settings = orchestrator.LEAD.model, orchestrator.LEAD.model_settings
    assert orchestrator.tuned(orchestrator.LEAD, ctx) is orchestrator.LEAD  # no overrides -> same object
    ctx.model, ctx.effort = config.build_model(list(config.MODEL_CHOICES)[-1]), "high"
    a = orchestrator.tuned(orchestrator.LEAD, ctx)
    assert a is not orchestrator.LEAD and a.model_settings.reasoning.effort == "high" and a.model_settings.tool_choice == "required"
    assert orchestrator.LEAD.model is base_model and orchestrator.LEAD.model_settings is base_settings
    assert orchestrator.turns(6, ctx) == 8


async def test_progress_registry_append_since_ttl(api, ctx):
    reg = progress.RunRegistry()
    assert reg.get("nope")["status"] == "unknown"
    reg.start("r1", ctx)
    ctx.record("Lead", "resolve_cohort", {}, "x")
    ctx.stage("researching")
    g = reg.get("r1")
    assert g["status"] == "running" and g["stage"] == "researching" and len(g["tool_calls"]) == 1 and g["next"] == 1
    ctx.record("Cost Researcher R1", "get_drg_costs", {}, "y")
    assert [c["name"] for c in reg.get("r1", since=1)["tool_calls"]] == ["get_drg_costs"]
    reg.finish("r1")
    assert reg.get("r1")["status"] == "done"
    reg._runs["r1"][1][0] = time.monotonic() - progress.TTL_S - 1
    assert reg.get("r1")["status"] == "unknown"
    reg.start("bad id!", ctx)  # invalid ids are ignored
    assert reg.get("bad id!")["status"] == "unknown"
    for i in range(progress.MAX_RUNS + 5):
        reg.start(f"x{i}", ctx)
    assert len(reg._runs) == progress.MAX_RUNS


async def test_progress_endpoint(api):
    assert (await api.get("/progress", params={"run_id": "unknown"})).json()["status"] == "unknown"


async def test_history_seeding_only_into_empty_sessions(tmp_path):
    s = SQLiteSession("h1", str(tmp_path / "h.db"))
    hist = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(20)]
    hist.insert(5, {"role": "system", "content": "no"})  # ignored, and outside the last 12 anyway
    assert await orchestrator.seed_history(s, hist) == orchestrator.HISTORY_MAX
    assert len(await s.get_items()) == orchestrator.HISTORY_MAX
    assert await orchestrator.seed_history(s, hist) == 0  # a live conversation is never overwritten


async def test_artifacts_match_facts_and_tables(ctx):
    await hf_bronx(ctx)
    ctx.rounds_used = 1
    await analyst.analyze(ctx)
    hospitals = {h.ccn: h for h in (await cms.general_info_ny(ctx.client)).rows}
    art = render.build_artifacts(ctx, hospitals)
    assert art["cohort"] and art["tables"] and art["sources"]
    fact = {f.key: f for f in ctx.facts}
    for row in art["cohort"]:
        f = fact.get(f"cost.drg291.{row['ccn']}.avg_total_payment")
        if f:  # featured hospitals: the artifact number IS the fact value and display
            assert row["avg_total_payment"] == f.value and row["payment_display"] == f.display
        assert (row["lat"] is None) == (row["lon"] is None)
    assert any(r["lat"] for r in art["cohort"])  # at least some hospitals have centroids
    ref = art["benchmarks"]["ny"]
    assert ref["value"] == fact["cost.drg291.state_avg"].value and ref["display"] == fact["cost.drg291.state_avg"].display
    assert art["charts"]["payment_bars"]["references"]["national"]["display"] == fact["cost.drg291.national_avg"].display
    assert all(p["x_display"] and p["y_display"] for p in art["charts"]["cost_quality_scatter"]["points"])
    assert {s["id"] for s in art["sources"]} <= {s.id for s in ctx.sources.all()}


async def test_artifacts_with_no_facts_do_not_raise(ctx):
    art = render.build_artifacts(ctx, {})
    assert art["cohort"] == [] and art["charts"]["payment_bars"]["items"] == [] and art["benchmarks"]["ny"] is None


def test_centroid_file_shape():
    c = render.zip_centroids()
    assert 100 < len(c) < 400 and all(len(k) == 5 and 40 < v[0] < 46 and -80 < v[1] < -71 for k, v in c.items())
