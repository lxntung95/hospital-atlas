"""Markdown rendering. No number is formatted here: every figure comes from a Fact display or a derived-table display column."""

import json

from atlas.config import DATA_DIR
from atlas.context import RequestContext
from atlas.validate import Audit, Validated, caveats

RANK_ROWS = 10


def _cell(x) -> str:
    return str(x if x not in (None, "") else "-").replace("|", "/").replace("\n", " ")


def _table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join(_cell(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def _marks(ids) -> str:
    return " ".join(f"[{s}]" for s in ids)


def rank_table(ctx: RequestContext) -> str:
    try:
        t = ctx.tables.get("T_rank")
    except KeyError:
        t = None
    if not t or not t.rows:
        return ""
    rows = t.rows[:RANK_ROWS] + [r for r in t.rows[RANK_ROWS:] if r.get("focus")]
    body = [[r["rank"], r["name"] + (" (focus)" if r.get("focus") else ""), r["city"], r["payment_display"], r["vs_ny_display"], r["discharges"], "small sample" if r.get("small_n") else ""]
            for r in rows]
    cap = f"**{t.title}** (highest payment first; {len(t.rows)} ranked) {_marks(t.meta.get('source_ids', []))}"
    return cap + "\n\n" + _table(["#", "Hospital", "City", "Avg total payment", "vs NY avg", "Medicare discharges", "Note"], body)


def quadrant_table(ctx: RequestContext) -> str:
    try:
        t = ctx.tables.get("T_quadrant")
    except KeyError:
        t = None
    if not t or not t.rows:
        return ""
    rows = [r for r in t.rows if r.get("focus")] or t.rows[:RANK_ROWS]
    rows = rows[:RANK_ROWS]
    body = [[r["name"], r["payment_display"], r["quality_measure"] or "-", r["quality_display"] or "-", r["quadrant"] if r["quadrant"] != "insufficient data" else f"insufficient data ({r['reason']})"]
            for r in rows]
    cap = f"**{t.title}** {_marks(t.meta.get('source_ids', []))}"
    return cap + "\n\n" + _table(["Hospital", "Avg total payment", "Quality measure", "Value", "Group"], body)


def sources_section(ctx: RequestContext) -> str:
    used = sorted({s for f in ctx.facts for s in f.source_ids}, key=lambda s: int(s[1:]))
    lines = []
    for sid in used:
        s = ctx.sources.get(sid)
        if s:
            note = f" ({s.note})" if s.note else ""
            lines.append(f"- [{s.id}] {s.dataset} — {s.period} — retrieved {s.retrieved_at}{note} — {s.url}")
    return "### Sources\n\n" + ("\n".join(lines) if lines else "No dataset was queried for this answer.")


def cannot_section(items: list[str]) -> str:
    return "### What the data can't tell you\n\n" + "\n".join(f"- {i}" for i in items)


def audit_line(a: Audit) -> str:
    if a.clean and not a.repaired:
        return ""
    parts = []
    if a.removed_citations:
        parts.append(f"{a.removed_citations} unknown citation(s) removed")
    if a.flagged_numbers:
        parts.append(f"{a.flagged_numbers} sentence(s) dropped for numbers not found in the data")
    if a.dropped_claims:
        parts.append(f"{a.dropped_claims} claim(s) dropped")
    if a.repaired:
        parts.append("the draft was revised once after validation")
    return "_Audit: " + "; ".join(parts) + "._"


def render(v: Validated, ctx: RequestContext) -> str:
    r = v.report
    out = [f"## {r.headline}"]
    if ctx.partials:
        out.append("_Partial report: " + "; ".join(ctx.partials) + "._")
    out += [c.text for c in r.claims]
    for block in (rank_table(ctx), quadrant_table(ctx)):
        if block:
            out.append(block)
    out.append(cannot_section(r.data_cannot_tell_you))
    if r.followups:
        out.append("### You could also ask\n\n" + "\n".join(f"- {q}" for q in r.followups))
    out.append(sources_section(ctx))
    a = audit_line(v.audit)
    if a:
        out.append(a)
    return "\n\n".join(out)


def render_partial(ctx: RequestContext, reason: str) -> str:
    """Whatever the analysis has, no model involved. Never raises, works with zero facts."""
    out = ["## Partial results", f"This answer is incomplete: {reason}"]
    if ctx.partials:
        out.append("; ".join(ctx.partials))
    keep = [f for f in ctx.facts if f.unit in ("usd", "ratio", "pct", "stars", "text") and ".cohort_" not in f.key or f.key.endswith(("state_avg", "national_avg"))][:15]
    if keep:
        out.append("\n".join(f"- {f.label}: {f.display} {_marks(f.source_ids)}".rstrip() for f in keep))
    else:
        out.append("No figures were completed before the time limit.")
    for block in (rank_table(ctx), quadrant_table(ctx)):
        if block:
            out.append(block)
    out.append(cannot_section(caveats(ctx)))
    out.append(sources_section(ctx))
    return "\n\n".join(out)


def render_scope(ctx: RequestContext, reason: str) -> str:
    """Out-of-scope or unanswerable question: honest, short, no researchers needed."""
    unresolved = [u for c in ctx.cohorts.values() for u in (c.get("spec") or {}).get("unresolved", [])]
    out = ["## This question is outside what the data can answer", reason or "The data covers New York hospitals only."]
    if unresolved:
        out.append("Could not resolve:\n" + "\n".join(f"- {u}" for u in unresolved))
    out.append("Hospital Atlas covers New York hospitals using CMS Medicare data: inpatient payments by DRG (CY2024), readmission and mortality measures, patient safety indicators and patient-survey star ratings.")
    out.append(cannot_section(caveats(ctx)))
    out.append(sources_section(ctx))
    return "\n\n".join(out)


# ---------------------------------------------------------------- structured artifacts for the UI

_CENTROIDS: dict | None = None


def zip_centroids() -> dict:
    global _CENTROIDS
    if _CENTROIDS is None:
        try:
            _CENTROIDS = json.loads((DATA_DIR / "ny_zip_centroids.json").read_text())
        except (OSError, ValueError):
            _CENTROIDS = {}
    return _CENTROIDS


def _stored(ctx: RequestContext, table_id: str):
    try:
        return ctx.tables.get(table_id)
    except KeyError:
        return None


def build_artifacts(ctx: RequestContext, hospitals: dict) -> dict:
    """Everything the evidence panel draws, from the stored tables and Facts only. `hospitals`: ccn -> cms.Hospital."""
    cents = zip_centroids()
    rank, quad = _stored(ctx, "T_rank"), _stored(ctx, "T_quadrant")
    q_by = {r["ccn"]: r for r in (quad.rows if quad else [])}
    cohort = []
    for r in (rank.rows if rank else []):
        h = hospitals.get(r["ccn"])
        z = (h.zip or "")[:5] if h else ""
        ll = cents.get(z)
        q = q_by.get(r["ccn"], {})
        cohort.append({"ccn": r["ccn"], "name": r["name"], "city": r["city"], "zip": z, "lat": ll[0] if ll else None, "lon": ll[1] if ll else None,
                       "rank": r["rank"], "discharges": r["discharges"], "avg_total_payment": r["avg_total_payment"], "payment_display": r["payment_display"],
                       "quadrant": q.get("quadrant", ""), "small_n": r["small_n"], "focus": r["focus"]})
    primary = rank.rows[0]["drg"] if rank and rank.rows else None
    fact_by = {f.key: f for f in ctx.facts}

    def bench(level: str):
        f = fact_by.get(f"cost.drg{primary}.{level}_avg")
        return {"value": f.value, "display": f.display, "source_ids": f.source_ids} if f else None

    shown = (rank.rows[:15] + [r for r in rank.rows[15:] if r["focus"]]) if rank else []
    charts = {
        "payment_bars": {"drg": primary, "items": [{"ccn": r["ccn"], "name": r["name"], "value": r["avg_total_payment"], "display": r["payment_display"], "focus": r["focus"], "small_n": r["small_n"]} for r in shown],
                         "references": {"ny": bench("state"), "national": bench("national")}},
        "cost_quality_scatter": {"measure": next((r["quality_measure"] for r in (quad.rows if quad else []) if r["quality_measure"]), None),
                                 "points": [{"ccn": r["ccn"], "name": r["name"], "x": r["avg_total_payment"], "x_display": r["payment_display"], "y": r["quality_value"], "y_display": r["quality_display"],
                                             "quadrant": r["quadrant"], "focus": r["focus"]} for r in (quad.rows if quad else []) if r["quality_value"] is not None]},
    }
    tables = [{"id": t.id, "title": t.title, "columns": t.columns, "rows": t.rows} for t in (rank, quad) if t]
    used = sorted({s for f in ctx.facts for s in f.source_ids}, key=lambda s: int(s[1:]))
    sources = [{"id": s.id, "dataset": s.dataset, "period": s.period, "retrieved_at": s.retrieved_at, "url": s.url, "note": s.note} for s in (ctx.sources.get(i) for i in used) if s]
    return {"cohort": cohort, "tables": tables, "charts": charts, "benchmarks": {"drg": primary, "ny": bench("state"), "national": bench("national")}, "sources": sources,
            "facts": [{"id": f.id, "label": f.label, "display": f.display, "source_ids": f.source_ids, "caveats": f.caveats} for f in ctx.facts]}
