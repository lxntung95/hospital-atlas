"""Analyst tests: deterministic facts from fixtures and from the shipped snapshot (offline)."""

import json


from atlas import analyst, tools
from atlas.analyst import fmt_int, fmt_ordinal, fmt_pct, fmt_period, fmt_ratio, fmt_usd, psi_signal, quartiles, weighted_mean
from tests.conftest import call


async def j(tool, ctx, **kw):
    return json.loads(await call(tool, ctx, **kw))


async def hf_bronx(ctx):
    h = (await j(tools.build_cohort, ctx, ccns=["330059"], counties=["Bronx"], label="Bronx"))["cohort_handle"]
    await j(tools.get_drg_costs, ctx, cohort_handle=h, drg_codes=[291])
    await j(tools.get_cost_benchmarks, ctx, drg_codes=[291])
    await j(tools.get_readmissions, ctx, cohort_handle=h, measure_ids=["READM-30-HF-HRRP"])
    await j(tools.get_outcomes, ctx, cohort_handle=h, measure_ids=["MORT_30_HF"])
    await j(tools.get_patient_experience, ctx, cohort_handle=h)
    return h


def test_formatters():
    assert fmt_usd(23235.41) == "$23,235" and fmt_usd(17364.02) == "$17,364"
    assert fmt_pct(33.8) == "33.8%" and fmt_pct(33.84, signed=True) == "+33.8%" and fmt_pct(-4.25, signed=True) == "-4.2%"
    assert fmt_ratio(1.0123) == "1.012" and fmt_int(6517) == "6,517"
    assert [fmt_ordinal(n) for n in (1, 2, 3, 4, 11, 12, 21, 92)] == ["1st", "2nd", "3rd", "4th", "11th", "12th", "21st", "92nd"]
    assert fmt_period("2021-07-01 to 2024-06-30") == "Jul 2021 to Jun 2024" and fmt_period("odd") == "odd"


def test_stats_helpers():
    assert weighted_mean([10, 20], [1, 3]) == 17.5 and weighted_mean([1], [0]) is None
    assert quartiles([1]) is None and quartiles([1, 2, 3, 4, 5]) == (2, 3, 4)
    assert psi_signal(1.0, 0.5, 0.9, 1.0) == "better"
    assert psi_signal(2.0, 1.5, 2.5, 1.0) == "worse"
    assert psi_signal(1.0, 0.5, 1.5, 1.0) == "not distinguishable" and psi_signal(1, None, None, 1) is None


async def test_facts_have_sources_and_display(ctx):
    await hf_bronx(ctx)
    res = await analyst.analyze(ctx)
    assert res.facts and ctx.facts is res.facts
    for f in res.facts:
        assert f.display and f.id and f.key
        if f.table_id:
            assert f.source_ids, f.key
    keys = {f.key for f in res.facts}
    assert {"cost.drg291.cohort_wmean", "cost.drg291.state_avg", "cost.drg291.national_avg"} <= keys
    assert len(keys) == len(res.facts)  # unique keys


async def test_benchmark_facts_for_drg_470(ctx):
    await j(tools.get_cost_benchmarks, ctx, drg_codes=[470])
    h = (await j(tools.build_cohort, ctx, ccns=["330059"], label="m"))["cohort_handle"]
    await j(tools.get_drg_costs, ctx, cohort_handle=h, drg_codes=[470])
    res = await analyst.analyze(ctx)
    by = {f.key: f for f in res.facts}
    assert by["cost.drg470.state_avg"].display == "$23,235" and by["cost.drg470.national_avg"].display == "$17,364"
    assert by["cost.drg470.330059.vs_state"].display.endswith("%")


async def test_idempotent_and_derived_tables(ctx):
    await hf_bronx(ctx)
    a = await analyst.analyze(ctx)
    n_tables = len(ctx.tables.all())
    b = await analyst.analyze(ctx)
    assert [f.model_dump() for f in a.facts] == [f.model_dump() for f in b.facts]
    assert len(ctx.tables.all()) == n_tables
    assert ctx.tables.get("T_rank").rows[0]["rank"] == 1
    q = ctx.tables.get("T_quadrant").rows
    assert q and all(r["quadrant"] for r in q)
    assert any("Analyst" == c["agent"] for c in ctx.tool_calls)


async def test_gaps_fillable_siblings_and_unfillable(ctx):
    await hf_bronx(ctx)
    res = await analyst.analyze(ctx)
    fill = [g for g in res.gaps if g.fillable]
    assert any(g.suggested_task and g.suggested_task["drg_codes"] == [292] for g in fill)  # sibling DRG 292, there is no 293
    assert not any(293 in (g.suggested_task or {}).get("drg_codes", []) for g in fill)
    assert any(g.kind == "period_mismatch" and not g.fillable for g in res.gaps)


async def test_quality_signals_direction_and_err(ctx):
    await hf_bronx(ctx)
    res = await analyst.analyze(ctx)
    errs = [f for f in res.facts if f.key.endswith(".err")]
    assert errs and all(f.display.count(".") == 1 and len(f.display.split(".")[1]) == 3 for f in errs)
    dirs = [f for f in res.facts if f.key.endswith(".direction")]
    assert dirs and all("direction only" in f.display for f in dirs)


async def test_empty_context_makes_no_facts(ctx):
    res = await analyst.analyze(ctx)
    assert res.facts == [] and res.gaps == []
    assert "T_rank" not in [t.id for t in ctx.tables.all()]


def test_table_put_replaces(ctx):
    ctx.tables.put("T_x", "a", [{"a": 1}])
    ctx.tables.put("T_x", "b", [{"a": 2}])
    assert len(ctx.tables.all()) == 1 and ctx.tables.get("T_x").rows == [{"a": 2}]
