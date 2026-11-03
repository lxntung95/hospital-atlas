"""The Analyst: all statistics in plain Python (stdlib only). Reads the tables the researchers stored and produces
Facts (every number the report may use, with a canonical display string and source ids), Gaps (what is missing and whether
another research round could fill it) and two derived tables, T_rank and T_quadrant.

Rule: nothing here calls a model, and missing input produces a Gap, never an invented Fact.
"""

import statistics
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from atlas import cms, crosswalk
from atlas.context import RequestContext
from atlas.schemas import Gap

# Small-n thresholds
MIN_DISCHARGES = 20  # cost rows
MIN_HRRP_CASES = 25
MIN_MORT_DENOM = 25
MIN_SURVEYS = 100
TOP_N = 5  # hospitals featured with their own Facts besides the named ones
ALL_IF_AT_MOST = 8


# ---------------------------------------------------------------- formatting (the only place numbers become text)

def fmt_usd(x: float) -> str:
    return f"${x:,.0f}"


def fmt_pct(x: float, signed: bool = False) -> str:
    return f"{x:+.1f}%" if signed else f"{x:.1f}%"


def fmt_pp(x: float) -> str:
    return f"{x:+.1f} pp"  # percentage points


def fmt_ratio(x: float) -> str:
    return f"{x:.3f}"


def fmt_int(x: float) -> str:
    return f"{x:,.0f}"


def fmt_rank(rank: int, n: int) -> str:
    return f"#{rank} of {n}"


def fmt_ordinal(n: float) -> str:
    n = int(round(n))
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fmt_period(p: str) -> str:
    """'2021-07-01 to 2024-06-30' -> 'Jul 2021 to Jun 2024'; other strings pass through."""
    try:
        a, b = p.split(" to ")
        return f"{MONTHS[int(a[5:7]) - 1]} {a[:4]} to {MONTHS[int(b[5:7]) - 1]} {b[:4]}"
    except (ValueError, IndexError):
        return p


# ---------------------------------------------------------------- models

class Fact(BaseModel):
    id: str
    key: str  # stable, e.g. "cost.drg470.330059.avg_total_payment"
    label: str
    value: float | int | str | None
    display: str  # the ONLY text allowed in prose
    unit: str = ""
    source_ids: list[str] = Field(default_factory=list)
    table_id: str | None = None
    ccn: str | None = None
    drg: int | None = None
    measure: str | None = None
    caveats: list[str] = Field(default_factory=list)


@dataclass
class Analysis:
    facts: list[Fact] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
    primary_drg: int | None = None
    quadrant: list[dict] = field(default_factory=list)
    rank: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------- statistics helpers

def weighted_mean(values: list[float], weights: list[float]) -> float | None:
    total = sum(weights)
    return sum(v * w for v, w in zip(values, weights)) / total if total else None


def quartiles(xs: list[float]) -> tuple[float, float, float] | None:
    if len(xs) < 2:
        return None
    q1, q2, q3 = statistics.quantiles(xs, n=4, method="inclusive")
    return q1, q2, q3


def pct_diff(x: float, ref: float) -> float | None:
    return (x - ref) / ref * 100 if ref else None


def psi_signal(score: float | None, lower: float | None, upper: float | None, national: float | None) -> str | None:
    """better / worse / not distinguishable, from the confidence interval against the national rate."""
    if None in (score, lower, upper, national):
        return None
    if upper < national:
        return "better"
    if lower > national:
        return "worse"
    return "not distinguishable"


def _src(table, drg: int | None = None) -> list[str]:
    ids = table.meta.get("source_ids") or ([table.source_id] if table.source_id else [])
    drgs = table.meta.get("drgs")
    if drg is not None and drgs and drg in drgs and len(ids) == len(drgs):
        return [ids[drgs.index(drg)]]
    return list(ids)


class _Builder:
    def __init__(self):
        self.facts: list[Fact] = []

    def add(self, key, label, value, display, unit="", sources=(), table=None, ccn=None, drg=None, measure=None, caveats=()):
        fact = Fact(id=f"F{len(self.facts) + 1}", key=key, label=label, value=value, display=display, unit=unit, source_ids=list(sources),
                    table_id=table.id if table else None, ccn=ccn, drg=drg, measure=measure, caveats=list(caveats))
        self.facts.append(fact)
        return fact


# ---------------------------------------------------------------- reading the stored tables

def _collect(ctx: RequestContext, kind: str) -> list[tuple[dict, object]]:
    seen, out = set(), []
    for t in ctx.tables.all():
        if t.meta.get("kind") != kind:
            continue
        for r in t.rows:
            key = (r.get("ccn"), r.get("drg"), r.get("measure"), r.get("measure_id"), r.get("geo"), r.get("level"))
            if key not in seen:
                seen.add(key)
                out.append((r, t))
    return out


def _focus_ccns(ctx: RequestContext) -> list[str]:
    out = []
    for c in ctx.cohorts.values():
        for x in (c.get("spec") or {}).get("focus_ccns", []):
            if x not in out:
                out.append(x)
    return out


NON_FFS_TYPES = ("Veterans", "Psychiatric", "Childrens", "Defense")


# ---------------------------------------------------------------- the analysis

def analyze_tables(ctx: RequestContext, hospitals: dict) -> Analysis:
    """Pure function of ctx.tables / ctx.cohorts / the hospital list. Safe to call after every research round."""
    b = _Builder()
    out = Analysis()
    focus = _focus_ccns(ctx)
    names = {}
    costs, bench = {}, {}
    for r, t in _collect(ctx, "drg_costs"):
        costs.setdefault(r["drg"], []).append((r, t))
        names[r["ccn"]] = r["name"]
    for r, t in _collect(ctx, "benchmarks"):
        bench.setdefault(r["drg"], {})[r["level"]] = (r, t)

    # ---- cost
    ranked: dict[int, list[dict]] = {}
    for drg in sorted(costs):
        rows = sorted((r for r, _ in costs[drg] if r["avg_total_payment"] is not None), key=lambda r: (-r["avg_total_payment"], r["ccn"]))
        table = costs[drg][0][1]
        src = _src(table, drg)
        n = len(rows)
        ny = bench.get(drg, {}).get("State")
        nat = bench.get(drg, {}).get("National")
        pays = [r["avg_total_payment"] for r in rows]
        disch = [r["discharges"] or 0 for r in rows]
        k = f"cost.drg{drg}"
        if n:
            wm = weighted_mean(pays, disch)
            b.add(f"{k}.cohort_wmean", f"DRG {drg} cohort volume-weighted mean payment", round(wm, 2), fmt_usd(wm), "usd", src, table, drg=drg)
            b.add(f"{k}.cohort_median", f"DRG {drg} cohort median payment", statistics.median(pays), fmt_usd(statistics.median(pays)), "usd", src, table, drg=drg)
            q = quartiles(pays)
            if q:
                b.add(f"{k}.cohort_iqr", f"DRG {drg} cohort interquartile range", f"{q[0]:.0f}-{q[2]:.0f}", f"{fmt_usd(q[0])} to {fmt_usd(q[2])}", "usd", src, table, drg=drg)
            b.add(f"{k}.cohort_hospitals", f"DRG {drg} hospitals with data", n, fmt_int(n), "count", src, table, drg=drg)
            b.add(f"{k}.cohort_discharges", f"DRG {drg} Medicare discharges in cohort", sum(disch), fmt_int(sum(disch)), "count", src, table, drg=drg)
        for lvl, label, row in (("State", "New York average", ny), ("National", "national average", nat)):
            if row:
                b.add(f"{k}.{lvl.lower()}_avg", f"DRG {drg} {label} payment", row[0]["avg_total_payment"], fmt_usd(row[0]["avg_total_payment"]), "usd", _src(row[1], drg), row[1], drg=drg)
        if ny and n:
            b.add(f"{k}.coverage", f"DRG {drg} share of NY Medicare discharges in these rows", round(sum(disch) / ny[0]["discharges"] * 100, 1),
                  f"{fmt_int(sum(disch))} of {fmt_int(ny[0]['discharges'])} ({fmt_pct(sum(disch) / ny[0]['discharges'] * 100)})", "pct", src + _src(ny[1], drg), table, drg=drg,
                  caveats=["hospitals with fewer than 11 Medicare discharges for a DRG are suppressed by CMS"])
        featured = {r["ccn"] for r in rows} if n <= ALL_IF_AT_MOST else {r["ccn"] for r in rows[:TOP_N]}
        featured |= {x for x in focus if any(r["ccn"] == x for r in rows)}
        for i, r in enumerate(rows, 1):
            if r["ccn"] not in featured:
                continue
            ccn, kk = r["ccn"], f"{k}.{r['ccn']}"
            cav = [f"only {r['discharges']} Medicare discharges: treat as unstable"] if (r["discharges"] or 0) < MIN_DISCHARGES else []
            b.add(f"{kk}.avg_total_payment", f"{r['name']} DRG {drg} average total payment", r["avg_total_payment"], fmt_usd(r["avg_total_payment"]), "usd", src, table, ccn, drg, caveats=cav)
            b.add(f"{kk}.discharges", f"{r['name']} DRG {drg} Medicare discharges", r["discharges"], fmt_int(r["discharges"] or 0), "count", src, table, ccn, drg)
            b.add(f"{kk}.rank", f"{r['name']} DRG {drg} payment rank in cohort", i, fmt_rank(i, n), "rank", src, table, ccn, drg)
            if n > 1:
                p = (n - i) / (n - 1) * 100
                b.add(f"{kk}.percentile", f"{r['name']} DRG {drg} payment percentile in cohort", round(p), f"{fmt_ordinal(p)} percentile", "pct", src, table, ccn, drg)
            for row, label in ((ny, "New York average"), (nat, "national average")):
                if row:
                    d = pct_diff(r["avg_total_payment"], row[0]["avg_total_payment"])
                    b.add(f"{kk}.vs_{row[0]['level'].lower()}", f"{r['name']} DRG {drg} payment vs {label}", round(d, 1), fmt_pct(d, signed=True), "pct",
                          src + _src(row[1], drg), table, ccn, drg, caveats=cav)
            if r["avg_charge"] and r["avg_total_payment"]:
                b.add(f"{kk}.charge_ratio", f"{r['name']} DRG {drg} submitted charge to payment ratio", round(r["avg_charge"] / r["avg_total_payment"], 1),
                      f"{r['avg_charge'] / r['avg_total_payment']:.1f}x", "ratio", src, table, ccn, drg, caveats=["charges are list prices, not what anyone pays"])
        ranked[drg] = rows
    primary = max(ranked, key=lambda d: sum(r["discharges"] or 0 for r in ranked[d]), default=None)
    out.primary_drg = primary
    if primary is not None:
        n = len(ranked[primary])
        ny = bench.get(primary, {}).get("State")
        out.rank = [{"rank": i, "ccn": r["ccn"], "name": r["name"], "city": r["city"], "drg": primary, "discharges": r["discharges"],
                     "avg_total_payment": r["avg_total_payment"], "payment_display": fmt_usd(r["avg_total_payment"]),
                     "vs_ny_pct": round(pct_diff(r["avg_total_payment"], ny[0]["avg_total_payment"]), 1) if ny else None,
                     "vs_ny_display": fmt_pct(pct_diff(r["avg_total_payment"], ny[0]["avg_total_payment"]), signed=True) if ny else "",
                     "small_n": (r["discharges"] or 0) < MIN_DISCHARGES, "focus": r["ccn"] in focus} for i, r in enumerate(ranked[primary], 1)]

    # ---- quality
    quality: dict[str, tuple[str, dict]] = {}  # ccn -> (signal text key info) used for the quadrant
    hrrp = _collect(ctx, "hrrp")
    outcomes = _collect(ctx, "outcomes")
    hcahps = _collect(ctx, "hcahps")
    feat_q = set(focus)
    all_q_ccns = {r["ccn"] for r, _ in hrrp + outcomes + hcahps}
    feat_q |= all_q_ccns if len(all_q_ccns) <= ALL_IF_AT_MOST else set()
    if len(all_q_ccns) > ALL_IF_AT_MOST:  # large cohort: feature the best-ranked on cost too, if we know them
        feat_q |= {r["ccn"] for rows in ranked.values() for r in rows[:TOP_N]}
    periods = {}
    hrrp_by = {}
    for r, t in hrrp:
        periods.setdefault(("HRRP", r["period"]), t)
        hrrp_by[(r["ccn"], r["measure"])] = r
        if r["ccn"] not in feat_q or r["excess_readmission_ratio"] is None:
            continue
        err, cases = r["excess_readmission_ratio"], r["cases"]
        sig = "worse than expected" if err > 1 else "better than expected" if err < 1 else "as expected"
        cav = [f"only {cases} cases: treat as unstable"] if (cases or 0) < MIN_HRRP_CASES else []
        src = _src(t)
        kk = f"quality.{r['measure']}.{r['ccn']}"
        b.add(f"{kk}.err", f"{r['name']} {r['measure']} excess readmission ratio", err, fmt_ratio(err), "ratio", src, t, r["ccn"], measure=r["measure"], caveats=cav)
        b.add(f"{kk}.signal", f"{r['name']} {r['measure']} compared with expected", sig, sig, "text", src, t, r["ccn"], measure=r["measure"], caveats=cav)
        if cases:
            b.add(f"{kk}.cases", f"{r['name']} {r['measure']} cases", cases, fmt_int(cases), "count", src, t, r["ccn"], measure=r["measure"])
    for measure in sorted({r["measure"] for r, _ in hrrp}):
        vals = [r["excess_readmission_ratio"] for r, _ in hrrp if r["measure"] == measure and r["excess_readmission_ratio"] is not None]
        if vals:
            t = next(t for r, t in hrrp if r["measure"] == measure)
            b.add(f"quality.{measure}.cohort_median_err", f"{measure} cohort median excess readmission ratio", statistics.median(vals), fmt_ratio(statistics.median(vals)), "ratio", _src(t), t, measure=measure)
            b.add(f"quality.{measure}.cohort_n", f"{measure} hospitals with a ratio", len(vals), fmt_int(len(vals)), "count", _src(t), t, measure=measure)

    out_by = {}
    for r, t in outcomes:
        periods.setdefault(("outcomes", r["period"]), t)
        out_by[(r["ccn"], r["measure_id"])] = r
        if r["ccn"] not in feat_q or r["score"] is None:
            continue
        mid, nat = r["measure_id"], r["national_rate"]
        src = _src(t)
        kk = f"quality.{mid}.{r['ccn']}"
        cav = [f"denominator {r['denominator']} is below {MIN_MORT_DENOM}: treat as unstable"] if r["denominator"] is not None and r["denominator"] < MIN_MORT_DENOM else []
        if r["compared_to_national"] == "Number of Cases Too Small":
            cav.append("CMS: number of cases too small to compare")
        if mid.startswith("PSI"):
            sig = psi_signal(r["score"], r["lower"], r["upper"], nat)
            if sig and r["compared_to_national"] and r["compared_to_national"].split()[0].lower() not in (sig.split()[0], "no") and not (sig == "not distinguishable"):
                cav.append(f"CMS label differs: {r['compared_to_national']}")
            b.add(f"{kk}.score", f"{r['name']} {mid} score", r["score"], f"{r['score']:g}", "rate", src, t, r["ccn"], measure=mid, caveats=cav)
            if sig:
                b.add(f"{kk}.signal", f"{r['name']} {mid} versus the national rate (confidence interval)", sig, sig, "text", src, t, r["ccn"], measure=mid, caveats=cav)
        else:
            b.add(f"{kk}.score", f"{r['name']} {mid} score", r["score"], fmt_pct(r["score"]), "pct", src, t, r["ccn"], measure=mid, caveats=cav)
            if nat is not None:
                diff = r["score"] - nat
                word = "lower than" if diff < 0 else "higher than" if diff > 0 else "equal to"
                b.add(f"{kk}.vs_national", f"{r['name']} {mid} difference from the national rate", round(diff, 2), fmt_pp(diff), "pp", src, t, r["ccn"], measure=mid,
                      caveats=cav + ["direction only: CMS publishes no confidence interval for this measure"])
                b.add(f"{kk}.direction", f"{r['name']} {mid} compared with the national rate", word, f"{word} the national rate (direction only)", "text", src, t, r["ccn"], measure=mid, caveats=cav)
    for mid in sorted({r["measure_id"] for r, _ in outcomes}):
        nat = next((r["national_rate"] for r, _ in outcomes if r["measure_id"] == mid and r["national_rate"] is not None), None)
        t = next(t for r, t in outcomes if r["measure_id"] == mid)
        if nat is not None:
            b.add(f"quality.{mid}.national_rate", f"{mid} national rate", nat, fmt_pct(nat) if not mid.startswith("PSI") else f"{nat:g}", "pct" if not mid.startswith("PSI") else "rate", _src(t), t, measure=mid)

    for r, t in hcahps:
        periods.setdefault(("HCAHPS", r["period"]), t)
        if r["ccn"] not in feat_q or r["stars"] is None:
            continue
        cav = [f"only {r['surveys']} completed surveys: treat as unstable"] if (r["surveys"] or 0) < MIN_SURVEYS else []
        b.add(f"quality.hcahps.{r['ccn']}.stars", f"{r['name']} HCAHPS overall star rating", r["stars"], f"{r['stars']} of 5 stars", "stars", _src(t), t, r["ccn"], caveats=cav + ["from patient surveys, not clinical quality"])

    # ---- cost-vs-quality quadrant (primary DRG vs the condition's headline quality measure)
    if primary is not None:
        owner = next((c for c, v in crosswalk.crosswalk().items() if primary in v["drgs"]), None)
        cw = crosswalk.crosswalk().get(owner, {}) if owner else {}
        measure = next((m for m in (cw.get("hrrp_measure"), cw.get("mort_measure"), cw.get("comp_measure")) if m and (
            any(k[1] == m for k in hrrp_by) or any(k[1] == m for k in out_by))), None)
        pays = [r["avg_total_payment"] for r in ranked[primary]]
        cut = statistics.median(pays) if pays else None
        for r in ranked[primary]:
            q, why = "insufficient data", ""
            qv = None
            if measure is None:
                why = "no quality measure fetched for this condition"
            elif measure.startswith("READM"):
                h = hrrp_by.get((r["ccn"], measure))
                if not h or h["excess_readmission_ratio"] is None:
                    why = "no readmission ratio"
                elif (h["cases"] or 0) < MIN_HRRP_CASES:
                    why = f"fewer than {MIN_HRRP_CASES} readmission cases"
                else:
                    qv, good = h["excess_readmission_ratio"], h["excess_readmission_ratio"] <= 1
            else:
                o = out_by.get((r["ccn"], measure))
                if not o or o["score"] is None or o["national_rate"] is None:
                    why = "no score"
                elif o["denominator"] is not None and o["denominator"] < MIN_MORT_DENOM:
                    why = f"denominator below {MIN_MORT_DENOM}"
                else:
                    qv, good = o["score"], o["score"] <= o["national_rate"]
            if qv is not None and (r["discharges"] or 0) < MIN_DISCHARGES:
                qv, why = None, f"fewer than {MIN_DISCHARGES} Medicare discharges"
            if qv is not None:
                q = ("lower cost" if r["avg_total_payment"] <= cut else "higher cost") + " / " + ("better quality" if good else "worse quality")
            out.quadrant.append({"ccn": r["ccn"], "name": r["name"], "drg": primary, "avg_total_payment": r["avg_total_payment"], "payment_display": fmt_usd(r["avg_total_payment"]),
                                 "quality_measure": measure, "quality_value": qv, "quadrant": q, "reason": why, "focus": r["ccn"] in focus})
        if out.quadrant and measure:
            counts = {}
            for row in out.quadrant:
                counts[row["quadrant"]] = counts.get(row["quadrant"], 0) + 1
            for name, cnt in sorted(counts.items()):
                b.add(f"quadrant.drg{primary}.{name}", f"hospitals in the '{name}' group (DRG {primary} payment vs {measure})", cnt, fmt_int(cnt), "count", [], None, measure=measure,
                      caveats=["cost split at the cohort median payment; quality split at 1.0 (readmissions) or the national rate"])

    # ---- gaps
    gaps = []
    fetched = set(costs)
    for drg in sorted(costs):
        if drg not in bench or "State" not in bench[drg] or "National" not in bench[drg]:
            gaps.append(Gap(kind="no_benchmark", detail=f"No New York/national benchmark fetched for DRG {drg}.", fillable=True, suggested_task={"kind": "cost", "drg_codes": [drg]}))
    conditions = {c for c, v in crosswalk.crosswalk().items() if fetched & set(v["drgs"])}
    for cond in sorted(conditions):
        v = crosswalk.crosswalk()[cond]
        missing = sorted(set(v["drgs"]) - fetched)[:6]
        if missing:
            gaps.append(Gap(kind="missing_metric", detail=f"{v['label']}: sibling DRG(s) {', '.join(map(str, missing))} were not fetched.", fillable=True, suggested_task={"kind": "cost", "drg_codes": missing}))
        want = [m for m in (v["hrrp_measure"], v["mort_measure"], v["comp_measure"]) if m]
        have = {k[1] for k in hrrp_by} | {k[1] for k in out_by}
        miss_q = [m for m in want if m not in have]
        if miss_q:
            gaps.append(Gap(kind="missing_metric", detail=f"{v['label']}: quality measure(s) {', '.join(miss_q)} were not fetched.", fillable=True, suggested_task={"kind": "quality", "measure_ids": miss_q}))
        if not want:
            gaps.append(Gap(kind="missing_metric", detail=f"{v['label']}: CMS publishes no condition-specific quality measure.", fillable=False))
    # hospitals in the cohort with no cost rows
    with_cost = {r["ccn"] for rows in ranked.values() for r in rows}
    if costs:
        for handle, c in ctx.cohorts.items():
            absent = [x for x in c["ccns"] if x not in with_cost]
            nonffs = [hospitals[x].name for x in absent if x in hospitals and any(s in hospitals[x].type for s in NON_FFS_TYPES)]
            suppressed = [hospitals[x].name if x in hospitals else x for x in absent if not (x in hospitals and any(s in hospitals[x].type for s in NON_FFS_TYPES))]
            if nonffs:
                gaps.append(Gap(kind="unresolved_entity", detail=f"No Medicare fee-for-service inpatient data for: {', '.join(nonffs)} (VA, psychiatric, children's or federal facilities).", fillable=False))
            if suppressed:
                gaps.append(Gap(kind="small_n", detail=f"{len(suppressed)} hospital(s) have no row for the requested DRG(s) (fewer than 11 discharges are suppressed): {', '.join(suppressed[:8])}{'...' if len(suppressed) > 8 else ''}.", fillable=False))
    small = [f.label for f in b.facts if any("treat as unstable" in c for c in f.caveats) and f.unit in ("usd", "ratio", "pct", "stars", "rate") and f.key.endswith((".avg_total_payment", ".err", ".score", ".stars"))]
    if small:
        gaps.append(Gap(kind="small_n", detail=f"{len(small)} figure(s) rest on small samples and are flagged unstable.", fillable=False))
    pers = sorted({fmt_period(p) for (_k, p) in periods})
    if costs and pers:
        gaps.append(Gap(kind="period_mismatch", detail=f"Cost data is calendar 2024; quality measures cover different periods ({'; '.join(pers)}). Compare directionally.", fillable=False))
    elif len(pers) > 1:
        gaps.append(Gap(kind="period_mismatch", detail=f"Quality measures cover different periods ({'; '.join(pers)}).", fillable=False))
    out.facts, out.gaps = b.facts, gaps
    return out


async def analyze(ctx: RequestContext) -> Analysis:
    """Recompute everything from ctx.tables (idempotent), store Facts/Gaps on the context and the derived tables in the store."""
    hospitals = {h.ccn: h for h in (await cms.general_info_ny(ctx.client)).rows}
    result = analyze_tables(ctx, hospitals)
    ctx.facts, ctx.gaps = result.facts, result.gaps
    if result.rank:
        ctx.tables.put("T_rank", f"Cohort ranking by average total payment, DRG {result.primary_drg}", result.rank, owner="Analyst", kind="rank")
    if result.quadrant:
        ctx.tables.put("T_quadrant", f"Cost versus quality, DRG {result.primary_drg}", result.quadrant, owner="Analyst", kind="quadrant")
    ctx.record("Analyst", "analyze", {}, f"{len(result.facts)} facts, {len(result.gaps)} gaps ({sum(g.fillable for g in result.gaps)} fillable)")
    return result
