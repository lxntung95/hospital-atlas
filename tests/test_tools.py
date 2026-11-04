"""Tool contract tests: compact JSON, clamps, NY enforcement, error shape. Offline (shipped fallback data)."""

import json

from atlas import tools
from tests.conftest import bronx, call, j


async def test_find_hospitals_and_out_of_scope(ctx):
    r = await j(tools.find_hospitals, ctx, query="Montefiore")
    assert r["matches"][0]["ccn"] == "330059"
    r = await j(tools.find_hospitals, ctx, query="Mass General")
    assert r["matches"] == [] and "outside NY scope" in r["unresolved"]


async def test_find_services_heart_failure(ctx):
    r = await j(tools.find_services, ctx, query="heart failure")
    s = r["services"][0]
    assert 291 in s["drg_codes"] and "MORT_30_HF" in s["measure_ids"] and "READM-30-HF-HRRP" in s["measure_ids"]


async def test_build_cohort_rejects_non_ny_and_empty(ctx):
    r = await j(tools.build_cohort, ctx, ccns=["220071"])  # a Massachusetts CCN
    assert "error" in r and "advice" in r
    r = await j(tools.build_cohort, ctx)
    assert "error" in r


async def test_build_cohort_bronx_acute_care_only(ctx):
    r = await j(tools.build_cohort, ctx, counties=["bronx"])
    ccns = ctx.cohorts[r["cohort_handle"]]["ccns"]
    assert "330059" in ccns and "33016F" not in ccns and "334053" not in ccns  # no VA, no psychiatric


async def test_submit_cohort_validates_handle_and_focus(ctx):
    assert "error" in await j(tools.submit_cohort, ctx, cohort_handle="C9")
    h = await bronx(ctx)
    spec = await j(tools.submit_cohort, ctx, cohort_handle=h, focus_ccns=["330059", "999999"], drg_codes=[291])
    assert spec["focus_ccns"] == ["330059"] and spec["drg_codes"] == [291]


async def test_get_drg_costs_is_compact_and_stores_table(ctx):
    h = await bronx(ctx)
    raw = await call(tools.get_drg_costs, ctx, cohort_handle=h, drg_codes=[291, 292])
    r = json.loads(raw)
    assert r["table_handle"] == "T1" and len(r["preview"]) <= 5 and len(raw) < 4000
    assert r["by_drg"]["291"]["hospitals"] >= 3 and r["source_ids"]
    table = ctx.tables.get("T1")
    assert table.meta["owner"] == "Lead" and all(row["ccn"] in ctx.cohorts[h]["ccns"] for row in table.rows)
    assert any("suppressed" in c for c in r["caveats"])


async def test_get_drg_costs_clamps_to_six_drgs_and_errors(ctx):
    h = await bronx(ctx)
    r = await j(tools.get_drg_costs, ctx, cohort_handle=h, drg_codes=[190, 191, 192, 193, 194, 195, 280, 281])
    assert sorted(r["by_drg"]) == ["190", "191", "192", "193", "194", "195"]
    assert "error" in await j(tools.get_drg_costs, ctx, cohort_handle=h, drg_codes=[])
    assert "error" in await j(tools.get_drg_costs, ctx, cohort_handle="C9", drg_codes=[470])


async def test_benchmarks_match_known_values(ctx):
    r = await j(tools.get_cost_benchmarks, ctx, drg_codes=[470])
    rows = ctx.tables.get(r["table_handle"]).rows
    ny = next(x for x in rows if x["geo"] == "New York")
    nat = next(x for x in rows if x["level"] == "National")
    assert round(ny["avg_total_payment"]) == 23235 and round(nat["avg_total_payment"]) == 17364


async def test_readmissions_validates_measure_ids(ctx):
    h = await bronx(ctx)
    r = await j(tools.get_readmissions, ctx, cohort_handle=h, measure_ids=["READM-30-HF-HRRP", "MORT_30_HF", "made-up"])
    assert r["measures"] == ["READM-30-HF-HRRP"] and set(r["ignored_measures"]) == {"MORT_30_HF", "made-up"}
    assert "error" in await j(tools.get_readmissions, ctx, cohort_handle=h, measure_ids=["READM-30-STK-HRRP"])


async def test_outcomes_join_national_rate_and_flag_direction_only(ctx):
    h = await bronx(ctx)
    r = await j(tools.get_outcomes, ctx, cohort_handle=h, measure_ids=["MORT_30_HF"])
    rows = ctx.tables.get(r["table_handle"]).rows
    assert rows and all(x["national_rate"] is not None for x in rows) and len(r["source_ids"]) == 2
    assert any("direction only" in c for c in r["caveats"])


async def test_patient_experience(ctx):
    h = await bronx(ctx)
    r = await j(tools.get_patient_experience, ctx, cohort_handle=h)
    assert r["n"] >= 3 and "table_handle" in r


async def test_submit_finding_rejects_made_up_handles(ctx):
    r = await j(tools.submit_finding, ctx, task_id="R1", summary="x", table_handles=["T9"], source_ids=[])
    assert "error" in r
    h = await bronx(ctx)
    t = await j(tools.get_patient_experience, ctx, cohort_handle=h)
    assert "error" in await j(tools.submit_finding, ctx, task_id="R1", summary="x", table_handles=[t["table_handle"]], source_ids=["S99"])
    f = await j(tools.submit_finding, ctx, task_id="R1", summary="ok", table_handles=[t["table_handle"]], source_ids=t["source_ids"], gaps=["thin"])
    assert f["status"] == "ok" and f["gaps"][0]["detail"] == "thin"
