"""Function tools the agents call. Every tool returns compact JSON (a table handle, counts, a 5-row preview, source ids,
caveats), never raw rows, and every failure is {"error", "advice"} so the model can recover instead of crashing."""

import json
import statistics
from functools import partial

from agents import RunContextWrapper, function_tool

from atlas import cms, crosswalk
from atlas import config
from atlas.context import RequestContext
from atlas.schemas import CohortSpec, Finding, Gap
from atlas.sources import data_api_url, provider_url

tool = partial(function_tool, strict_mode=False)  # tolerate defaults and nested models on Gemini

MAX_DRGS = 6
MAX_MEASURES = 8
PREVIEW_ROWS = 5
MAX_COHORT = 250

Ctx = RunContextWrapper[RequestContext]


def ok(**kw) -> str:
    return json.dumps(kw, default=str)


def err(message: str, advice: str) -> str:
    return json.dumps({"error": message, "advice": advice})


async def _hospitals(ctx: RequestContext) -> dict:
    return {h.ccn: h for h in (await cms.general_info_ny(ctx.client)).rows}


def _cohort(ctx: RequestContext, handle: str) -> dict | None:
    return ctx.cohorts.get(handle)


def _bad_cohort(ctx: RequestContext, handle: str) -> str:
    return err(f"unknown cohort handle {handle!r}", f"known handles: {', '.join(ctx.cohorts) or 'none'}; call resolve_cohort first")


def _caveats(*results) -> list[str]:
    return [r.note for r in results if r.note]


# ---------------------------------------------------------------- Cohort Retriever tools

@tool
async def find_hospitals(ctx: Ctx, query: str) -> str:
    """Find New York hospitals by name. Returns up to 5 matches with CCNs, or says why none matched.

    Args:
        query: Hospital name or part of it, e.g. "Montefiore" or "Mount Sinai".
    """
    c = ctx.context
    search = crosswalk.find_hospitals(query, list((await _hospitals(c)).values()))
    if not search.matches:
        return ok(matches=[], unresolved=search.unresolved)
    return ok(matches=[{"ccn": m.ccn, "name": m.name, "city": m.city, "county": m.county} for m in search.matches])


@tool
async def find_services(ctx: Ctx, query: str) -> str:
    """Map a condition or procedure (or a DRG number) to DRG codes and quality measure ids.

    Args:
        query: Free text such as "heart failure", "knee replacement" or "DRG 470".
    """
    c = ctx.context
    catalog = {r.drg: r.drg_desc for r in (await cms.ny_inpatient(c.client)).rows}
    found = crosswalk.find_services(query, catalog)
    if not found:
        return ok(services=[], advice="no match; try a condition name such as heart failure, pneumonia, hip/knee replacement, or a DRG number")
    return ok(services=[{"condition": s.condition, "label": s.label, "drg_codes": s.drgs, "measure_ids": s.measures, "notes": s.notes} for s in found])


async def make_cohort(c: RequestContext, ccns: list[str] | None, counties: list[str] | None, statewide: bool, label: str) -> tuple[str | None, list[str], list[str]]:
    """Create a cohort. Returns (handle or None if empty, invalid ccns, sample hospital names)."""
    hospitals = await _hospitals(c)
    chosen: dict[str, None] = {}
    invalid = []
    for ccn in ccns or []:
        if ccn in hospitals:
            chosen[ccn] = None
        else:
            invalid.append(ccn)
    wanted = {x.casefold() for x in counties or []}
    for h in hospitals.values():
        if h.type == "Acute Care Hospitals" and (statewide or h.county.casefold() in wanted):
            chosen[h.ccn] = None
    if not chosen or len(chosen) > MAX_COHORT:
        return None, invalid, []
    handle = f"C{len(c.cohorts) + 1}"
    c.cohorts[handle] = {"ccns": list(chosen), "label": label or handle}
    return handle, invalid, [hospitals[x].name for x in list(chosen)[:8]]


@tool
async def build_cohort(ctx: Ctx, ccns: list[str] | None = None, counties: list[str] | None = None, statewide: bool = False, label: str = "") -> str:
    """Create a cohort (a set of hospitals) and return its handle. Combine explicit CCNs with counties, or use statewide.

    Args:
        ccns: Hospital CCNs to include (from find_hospitals). Must be New York CCNs.
        counties: NY county names (e.g. ["Bronx"]) to include every acute care hospital in.
        statewide: True to include every New York acute care hospital.
        label: Short human label for the cohort, e.g. "Bronx acute care hospitals".
    """
    c = ctx.context
    handle, invalid, sample = await make_cohort(c, ccns, counties, statewide, label)
    if handle is None:
        return err("cohort is empty or too large", f"invalid or non-NY CCNs: {invalid}" if invalid else f"give ccns, counties, or statewide=true (max {MAX_COHORT} hospitals)")
    return ok(cohort_handle=handle, n=len(c.cohorts[handle]["ccns"]), sample=sample, invalid_ccns=invalid)


@tool
async def submit_cohort(ctx: Ctx, cohort_handle: str, focus_ccns: list[str] | None = None, drg_codes: list[int] | None = None,
                        measure_ids: list[str] | None = None, region_label: str = "", unresolved: list[str] | None = None) -> str:
    """Finish: submit the cohort. Always the last call.

    Args:
        cohort_handle: Handle returned by build_cohort.
        focus_ccns: The hospitals the user named (the ones to highlight), a subset of the cohort.
        drg_codes: DRG codes relevant to the question (from find_services).
        measure_ids: Quality measure ids relevant to the question (from find_services).
        region_label: Short label like "Bronx".
        unresolved: Names the user mentioned that could not be matched to a NY hospital, with the reason.
    """
    c = ctx.context
    cohort = _cohort(c, cohort_handle)
    if cohort is None:
        return _bad_cohort(c, cohort_handle)
    focus = [x for x in focus_ccns or [] if x in cohort["ccns"]]
    return CohortSpec(cohort_handle=cohort_handle, hospital_ccns=cohort["ccns"], focus_ccns=focus, drg_codes=drg_codes or [],
                      measure_ids=measure_ids or [], region_label=region_label or cohort["label"], unresolved=unresolved or []).model_dump_json()


# ---------------------------------------------------------------- Cost Researcher tools

def _median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


@tool
async def get_drg_costs(ctx: Ctx, cohort_handle: str, drg_codes: list[int]) -> str:
    """Average Medicare payments and discharges (CY2024) per hospital and DRG for a cohort. Stores a table.

    Args:
        cohort_handle: Cohort handle, e.g. C1.
        drg_codes: Up to 6 DRG codes, e.g. [470] or [291, 292].
    """
    c = ctx.context
    cohort = _cohort(c, cohort_handle)
    if cohort is None:
        return _bad_cohort(c, cohort_handle)
    drgs = sorted(set(drg_codes))[:MAX_DRGS]
    if not drgs:
        return err("no DRG codes given", "call with 1-6 DRG codes; find_services maps conditions to codes")
    res = await cms.ny_inpatient(c.client)
    members = set(cohort["ccns"])
    rows = [{"ccn": r.ccn, "name": r.name, "city": r.city, "drg": r.drg, "discharges": r.discharges, "avg_charge": r.avg_charge,
             "avg_total_payment": r.avg_total_payment, "avg_medicare_payment": r.avg_medicare_payment}
            for r in res.rows if r.ccn in members and r.drg in drgs]
    rows.sort(key=lambda r: (r["drg"], -(r["avg_total_payment"] or 0)))
    sources = [res.source(c.sources, data_api_url(config.INPATIENT_BY_PROVIDER, {"Rndrng_Prvdr_State_Abrvtn": config.STATE, "DRG_Cd": cms.drg_code(d)})) for d in drgs]
    table = c.tables.add(f"Medicare inpatient payments, DRG {', '.join(map(str, drgs))}", rows, source_id=sources[0].id, owner=c.owner,
                         source_ids=[s.id for s in sources], kind="drg_costs", cohort=cohort_handle, drgs=drgs)
    by_drg = {}
    for d in drgs:
        sub = [r for r in rows if r["drg"] == d]
        by_drg[d] = {"hospitals": len(sub), "discharges": sum(r["discharges"] or 0 for r in sub), "median_avg_total_payment": _median(r["avg_total_payment"] for r in sub)}
    with_data = {r["ccn"] for r in rows}
    hospitals = await _hospitals(c)
    missing = [hospitals[x].name for x in cohort["ccns"] if x not in with_data and x in hospitals]
    caveats = _caveats(res) + ["hospitals with fewer than 11 Medicare discharges for a DRG are suppressed by CMS"]
    return ok(table_handle=table.id, n=len(rows), by_drg=by_drg, preview=rows[:PREVIEW_ROWS], missing_hospitals=missing[:10],
              n_missing=len(missing), source_ids=[s.id for s in sources], caveats=caveats)


@tool
async def get_cost_benchmarks(ctx: Ctx, drg_codes: list[int]) -> str:
    """New York State and National average payments for DRGs (CY2024). Stores a table.

    Args:
        drg_codes: Up to 6 DRG codes.
    """
    c = ctx.context
    drgs = sorted(set(drg_codes))[:MAX_DRGS]
    if not drgs:
        return err("no DRG codes given", "call with 1-6 DRG codes")
    rows, sources, notes = [], [], []
    for d in drgs:
        res = await cms.geo_benchmark(d, c.client)
        sources.append(res.source(c.sources))
        notes += _caveats(res)
        rows += [{"drg": r.drg, "level": r.level, "geo": r.geo, "discharges": r.discharges, "avg_charge": r.avg_charge,
                  "avg_total_payment": r.avg_total_payment, "avg_medicare_payment": r.avg_medicare_payment} for r in res.rows]
    if not rows:
        return err("no benchmark rows", "check the DRG codes")
    table = c.tables.add(f"NY and national benchmarks, DRG {', '.join(map(str, drgs))}", rows, source_id=sources[0].id, owner=c.owner,
                         source_ids=[s.id for s in sources], kind="benchmarks", drgs=drgs)
    return ok(table_handle=table.id, n=len(rows), preview=rows[:PREVIEW_ROWS * 2], source_ids=[s.id for s in sources], caveats=sorted(set(notes)))


# ---------------------------------------------------------------- Quality Researcher tools

def _valid_measures(measure_ids: list[str], hrrp: bool) -> tuple[list[str], list[str]]:
    known = crosswalk.measures()
    good, bad = [], []
    for m in dict.fromkeys(measure_ids):
        is_hrrp = m.startswith("READM-30-")
        (good if m in known and is_hrrp == hrrp else bad).append(m)
    return good[:MAX_MEASURES], bad


@tool
async def get_readmissions(ctx: Ctx, cohort_handle: str, measure_ids: list[str]) -> str:
    """HRRP 30-day excess readmission ratios for a cohort (a ratio above 1.0 is worse than expected). Stores a table.

    Args:
        cohort_handle: Cohort handle, e.g. C1.
        measure_ids: HRRP measure names such as READM-30-HF-HRRP (from find_services).
    """
    c = ctx.context
    cohort = _cohort(c, cohort_handle)
    if cohort is None:
        return _bad_cohort(c, cohort_handle)
    measures, bad = _valid_measures(measure_ids, hrrp=True)
    if not measures:
        return err(f"no valid HRRP measures in {measure_ids}", "use ids like READM-30-HF-HRRP from find_services; stroke has no HRRP measure")
    res = await cms.hrrp_ny(c.client)
    members = set(cohort["ccns"])
    rows = [{"ccn": r.ccn, "name": r.name, "measure": r.measure, "cases": r.discharges, "excess_readmission_ratio": r.err,
             "predicted_rate": r.predicted, "expected_rate": r.expected, "readmissions": r.readmissions, "footnote": r.footnote, "period": r.period}
            for r in res.rows if r.ccn in members and r.measure in measures]
    src = res.source(c.sources, provider_url(config.HRRP, [("state", "=", config.STATE), ("measure_name", "IN", measures)]))
    table = c.tables.add("HRRP excess readmission ratios", rows, source_id=src.id, owner=c.owner, source_ids=[src.id], kind="hrrp", cohort=cohort_handle)
    return ok(table_handle=table.id, n=len(rows), measures=measures, ignored_measures=bad, preview=rows[:PREVIEW_ROWS], period=res.period,
              source_ids=[src.id], caveats=_caveats(res) + ["hospitals without enough cases for a measure have no row or a footnote"])


@tool
async def get_outcomes(ctx: Ctx, cohort_handle: str, measure_ids: list[str]) -> str:
    """Death and complication rates and patient-safety indicators for a cohort, joined to the national rate. Stores a table.

    Args:
        cohort_handle: Cohort handle, e.g. C1.
        measure_ids: Measure ids such as MORT_30_HF, COMP_HIP_KNEE, PSI_90 (from find_services). Up to 8.
    """
    c = ctx.context
    cohort = _cohort(c, cohort_handle)
    if cohort is None:
        return _bad_cohort(c, cohort_handle)
    measures, bad = _valid_measures(measure_ids, hrrp=False)
    if not measures:
        return err(f"no valid outcome measures in {measure_ids}", "use ids like MORT_30_HF, COMP_HIP_KNEE, PSI_90 from find_services")
    res = await cms.complications_ny(c.client)
    nat = await cms.complications_national(c.client)
    rate = {n.measure_id: n.national_rate for n in nat.rows}
    members = set(cohort["ccns"])
    rows = [{"ccn": r.ccn, "name": r.name, "measure_id": r.measure_id, "score": r.score, "national_rate": rate.get(r.measure_id),
             "compared_to_national": r.compared_to_national, "lower": r.lower, "upper": r.upper, "denominator": r.denominator,
             "footnote": r.footnote, "period": r.period} for r in res.rows if r.ccn in members and r.measure_id in measures]
    s1 = res.source(c.sources, provider_url(config.COMPLICATIONS, [("state", "=", config.STATE), ("measure_id", "IN", measures)]))
    s2 = nat.source(c.sources)
    table = c.tables.add("Outcome measures vs national", rows, source_id=s1.id, owner=c.owner, source_ids=[s1.id, s2.id], kind="outcomes", cohort=cohort_handle)
    caveats = _caveats(res, nat) + ["MORT and COMP measures publish no confidence interval or comparison: treat differences from the national rate as direction only"]
    return ok(table_handle=table.id, n=len(rows), measures=measures, ignored_measures=bad, preview=rows[:PREVIEW_ROWS], period=res.period,
              source_ids=[s1.id, s2.id], caveats=caveats)


@tool
async def get_patient_experience(ctx: Ctx, cohort_handle: str) -> str:
    """HCAHPS overall patient-survey star ratings (1-5) with number of completed surveys for a cohort. Stores a table.

    Args:
        cohort_handle: Cohort handle, e.g. C1.
    """
    c = ctx.context
    cohort = _cohort(c, cohort_handle)
    if cohort is None:
        return _bad_cohort(c, cohort_handle)
    res = await cms.hcahps_star_ny(c.client)
    members = set(cohort["ccns"])
    rows = [{"ccn": r.ccn, "name": r.name, "stars": r.stars, "surveys": r.surveys, "period": r.period} for r in res.rows if r.ccn in members]
    src = res.source(c.sources)
    table = c.tables.add("HCAHPS star ratings", rows, source_id=src.id, owner=c.owner, source_ids=[src.id], kind="hcahps", cohort=cohort_handle)
    rated = [r["stars"] for r in rows if r["stars"]]
    return ok(table_handle=table.id, n=len(rows), n_rated=len(rated), median_stars=_median(rated), preview=rows[:PREVIEW_ROWS], period=res.period,
              source_ids=[src.id], caveats=_caveats(res) + ["star ratings come from patient surveys, not clinical quality"])


# ---------------------------------------------------------------- shared terminal tool

@tool
async def submit_finding(ctx: Ctx, task_id: str, summary: str, table_handles: list[str], source_ids: list[str], status: str = "ok",
                         gaps: list[str] | None = None) -> str:
    """Finish: submit your finding. Always the last call.

    Args:
        task_id: The id of the task you were given.
        summary: Two to four plain sentences on what you found. Use only numbers returned by your tools.
        table_handles: Table handles (T1, T2...) your tools returned that hold the evidence.
        source_ids: Source ids (S1, S2...) your tools returned.
        status: "ok" if you answered the task, "partial" if something was missing.
        gaps: Things you could not find or that look too thin to trust, one short sentence each.
    """
    c = ctx.context
    for h in table_handles:
        try:
            c.tables.get(h)
        except KeyError as e:
            return err(str(e), "use only table handles returned by your tools")
    unknown = [s for s in source_ids if c.sources.get(s) is None]
    if unknown:
        return err(f"unknown source ids {unknown}", "use only source ids returned by your tools")
    return Finding(task_id=task_id, status="partial" if status == "partial" else "ok", agent=c.owner, table_handles=table_handles, source_ids=source_ids,
                   summary=summary, gaps=[Gap(kind="missing_metric", detail=g) for g in gaps or []]).model_dump_json()


RETRIEVER_TOOLS = [find_hospitals, find_services, build_cohort, submit_cohort]
COST_TOOLS = [get_drg_costs, get_cost_benchmarks, submit_finding]
QUALITY_TOOLS = [get_readmissions, get_outcomes, get_patient_experience, submit_finding]
