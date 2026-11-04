"""Citation and number validation for Writer output. Nothing the Writer says reaches the user without passing through here.

Rules: every [S#] exists; a claim carries the sources of the facts it cites; every number matches a Fact (+-0.5%) or is an allowed
kind (year, DRG code, CCN, measure id, small integer, known threshold); the "can't tell you" list has >= 2 items merged with the
deterministic caveats. Repair once, then strip what still fails and say so in the audit.
"""

import re
from dataclasses import dataclass, field

from atlas.context import RequestContext
from atlas.schemas import Claim, Report
from atlas.sources import sid_key

CITE = re.compile(r"\[S(\d+)\]")
MEASURE = re.compile(r"\b[A-Za-z]+(?:[-_][A-Za-z0-9]+)+\b")  # READM-30-HF-HRRP, MORT_30_HF, PSI_90, Hybrid_HWM
DRG = re.compile(r"\bDRGs?\s*\d+(?:\s*(?:,|/|and|or|&|-|to)\s*\d+)*", re.I)
CCN = re.compile(r"\b\d{6}\b")
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
HANDLE = re.compile(r"\b[TFSC]\d+\b")
NUM = re.compile(r"(?<![\w.])[-+]?\$?\d[\d,]*(?:\.\d+)?")
FACT_MARK = re.compile(r"\s*\[F\d+\]")  # the Writer sometimes echoes fact ids into prose
SENTENCE = re.compile(r"(?<=[.!?])\s+")
ALLOWED_INTS = set(range(0, 11)) | {11, 20, 25, 30, 100}  # small counts and the thresholds named in the caveats
TOL = 0.005

BASE_CAVEATS = [
    "Cost figures are Medicare fee-for-service inpatient payments for calendar year 2024; commercial insurance prices and what patients pay out of pocket are not in this data.",
    "Hospital charges are list prices, not what anyone pays; CMS suppresses hospital-DRG rows with fewer than 11 discharges.",
    "Quality measures cover periods that differ from the payment year, and the data cannot show whether a procedure was right for an individual patient.",
]


@dataclass
class Audit:
    removed_citations: int = 0
    flagged_numbers: int = 0  # sentences dropped for an unverifiable number
    dropped_claims: int = 0
    attached_sources: int = 0
    repaired: bool = False

    @property
    def clean(self) -> bool:
        return not (self.removed_citations or self.flagged_numbers or self.dropped_claims)


@dataclass
class Validated:
    report: Report
    audit: Audit
    violations: list[str] = field(default_factory=list)


def _number(token: str) -> float | None:
    try:
        return abs(float(token.replace("$", "").replace(",", "")))
    except ValueError:
        return None


def _fact_numbers(facts) -> list[float]:
    vals: list[float] = []
    for f in facts:
        vals += [v for v in map(_number, NUM.findall(f.display)) if v is not None]
        if isinstance(f.value, (int, float)) and not isinstance(f.value, bool):
            vals.append(abs(float(f.value)))
    return vals


def _scrub(text: str) -> str:
    for rx in (CITE, DRG, MEASURE, CCN, YEAR, HANDLE):
        text = rx.sub(" ", text)
    return text


def unmatched_numbers(text: str, pool: list[float]) -> list[str]:
    bad = []
    for m in NUM.findall(_scrub(text)):
        v = _number(m)
        if v is None:
            continue
        if v == int(v) and "." not in m and int(v) in ALLOWED_INTS and "$" not in m and "," not in m:
            continue
        if not any(abs(v - p) <= TOL * max(abs(p), 1e-9) or v == p for p in pool):
            bad.append(m)
    return bad


def caveats(ctx: RequestContext) -> list[str]:
    out = list(BASE_CAVEATS)
    out += [g.detail for g in ctx.gaps if not g.fillable]
    out += [f"Partial result: {p}." for p in ctx.partials]
    return list(dict.fromkeys(out))


def _pool(facts: dict, fids: list[str], fallback: list[float]) -> list[float]:
    """Numbers a claim may use: those of the facts it cites, or of all facts when it cites none."""
    return _fact_numbers([facts[i] for i in fids if i in facts]) or fallback


def find_violations(report: Report, ctx: RequestContext) -> list[str]:
    """Human-readable problems, used both for the repair prompt and for tests."""
    facts = {f.id: f for f in ctx.facts}
    all_pool = _fact_numbers(ctx.facts)
    out = []
    texts = [("headline", report.headline, [])] + [(f"claim {i}", c.text, c.fact_ids) for i, c in enumerate(report.claims, 1)]
    for where, text, fids in texts:
        for s in set(CITE.findall(text)):
            if ctx.sources.get(f"S{s}") is None:
                out.append(f"{where}: source S{s} does not exist")
        for n in unmatched_numbers(text, _pool(facts, fids, all_pool)):
            out.append(f"{where}: number {n} is not the display of a cited fact; copy displays verbatim")
        for i in fids:
            if i not in facts:
                out.append(f"{where}: fact {i} does not exist")
    for c in report.claims:
        for s in c.source_ids:
            if ctx.sources.get(s) is None:
                out.append(f"claim source {s} does not exist")
    if len(report.data_cannot_tell_you) < 2:
        out.append("data_cannot_tell_you needs at least 2 items")
    return out


def sanitize(report: Report, ctx: RequestContext, repaired: bool = False) -> Validated:
    """Always-safe output: fix what can be fixed, strip what cannot, count everything."""
    audit = Audit(repaired=repaired)
    facts = {f.id: f for f in ctx.facts}
    all_pool = _fact_numbers(ctx.facts)

    def clean_text(text: str, fids: list[str]) -> str | None:
        def drop_cite(m):
            if ctx.sources.get(f"S{m.group(1)}") is None:
                audit.removed_citations += 1
                return ""
            return m.group(0)

        text = FACT_MARK.sub("", CITE.sub(drop_cite, text))
        pool = _pool(facts, fids, all_pool)
        kept = []
        for sent in SENTENCE.split(text.strip()):
            if unmatched_numbers(sent, pool):
                audit.flagged_numbers += 1
                continue
            kept.append(sent)
        result = " ".join(kept).strip()
        return re.sub(r"\s{2,}", " ", result) or None

    headline = clean_text(report.headline, []) or "Results from the available CMS data"
    claims = []
    for c in report.claims:
        fids = [i for i in c.fact_ids if i in facts]
        text = clean_text(c.text, fids)
        if not text:
            audit.dropped_claims += 1
            continue
        cited = {f"S{n}" for n in CITE.findall(text)}
        want = set(cited) | {s for s in c.source_ids if ctx.sources.get(s)}
        for i in fids:
            want |= set(facts[i].source_ids)
        missing = sorted(want - cited, key=sid_key)
        if missing:
            audit.attached_sources += len(missing)
            text = f"{text} " + "".join(f"[{s}]" for s in missing)
        claims.append(Claim(text=text, fact_ids=fids, source_ids=sorted(want, key=sid_key)))
    cannot = [x for x in report.data_cannot_tell_you if x.strip()]
    merged = cannot + [c for c in caveats(ctx) if c not in cannot]
    return Validated(Report(headline=headline, claims=claims, data_cannot_tell_you=merged, followups=report.followups[:3]), audit)


async def validate(report: Report, ctx: RequestContext, repair=None) -> Validated:
    """repair: async callable taking the violation list and returning a new Report (or None). Called at most once."""
    violations = find_violations(report, ctx)
    repaired = False
    if violations and repair is not None:
        try:
            second = await repair(violations)
        except Exception:
            second = None
        if second is not None:
            report, repaired = second, True
            violations = find_violations(report, ctx)
    result = sanitize(report, ctx, repaired)
    result.violations = violations
    return result
