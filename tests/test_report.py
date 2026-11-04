"""T7 and friends: validator, renderer, repair loop, compose with a stub Writer. Offline."""

import pytest

from atlas import analyst, orchestrator, render, validate
from atlas.schemas import Claim, Report
from tests.conftest import hf_bronx


@pytest.fixture
async def done(ctx):
    await hf_bronx(ctx)
    ctx.question = "Compare heart failure payments in the Bronx"
    ctx.rounds_used = 1
    await analyst.analyze(ctx)
    return ctx


def fact(ctx, key):
    return next(f for f in ctx.facts if f.key == key)


def good_report(ctx) -> Report:
    f = fact(ctx, "cost.drg291.state_avg")
    return Report(headline="Heart failure payments vary across the Bronx",
                  claims=[Claim(text=f"The New York average is {f.display}.", fact_ids=[f.id], source_ids=f.source_ids)],
                  data_cannot_tell_you=["Whether outcomes differ for sicker patients.", "Commercial prices."])


async def test_valid_report_unchanged(done):
    v = await validate.validate(good_report(done), done)
    assert v.violations == [] and v.audit.clean and not v.audit.repaired
    assert v.report.claims[0].text.startswith("The New York average is")
    assert "[S" in v.report.claims[0].text  # fact sources auto-attached


async def test_fake_citation_stripped(done):
    f = fact(done, "cost.drg291.state_avg")
    r = Report(headline="h", claims=[Claim(text=f"The New York average is {f.display}. [S99]", fact_ids=[f.id])], data_cannot_tell_you=["a", "b"])
    assert any("S99" in x for x in validate.find_violations(r, done))
    v = await validate.validate(r, done)
    assert "[S99]" not in v.report.claims[0].text and v.audit.removed_citations == 1


async def test_stray_number_dropped(done):
    f = fact(done, "cost.drg291.state_avg")
    r = Report(headline="h", claims=[Claim(text=f"The average is {f.display}. Costs rose 87% last year.", fact_ids=[f.id]),
                                     Claim(text="Payments were $99,999.", fact_ids=[])], data_cannot_tell_you=["a", "b"])
    v = await validate.validate(r, done)
    assert v.audit.flagged_numbers == 2 and v.audit.dropped_claims == 1
    assert "87%" not in v.report.claims[0].text and len(v.report.claims) == 1


def test_allowed_numbers():
    pool = [23235.0]
    ok = "In 2024, DRG 291 and 292 at CCN 330059 under READM-30-HF-HRRP and MORT_30_HF showed 3 hospitals, $23,235, within 30-day windows; fewer than 11 discharges."
    assert validate.unmatched_numbers(ok, pool) == []
    assert validate.unmatched_numbers("$23,300 vs $23,235", pool) == []  # within 0.5% is still a match
    assert validate.unmatched_numbers("$25,000", pool) == ["$25,000"]


async def test_repair_runs_once(done):
    f = fact(done, "cost.drg291.state_avg")
    bad = Report(headline="h", claims=[Claim(text="Paid $1,234,567.", fact_ids=[f.id])], data_cannot_tell_you=["a"])
    calls = []

    async def repair(violations):
        calls.append(violations)
        return good_report(done)

    v = await validate.validate(bad, done, repair)
    assert len(calls) == 1 and v.audit.repaired and v.audit.clean and v.violations == []


async def test_repair_failure_still_sanitizes(done):
    f = fact(done, "cost.drg291.state_avg")
    bad = Report(headline="h", claims=[Claim(text="Paid $1,234,567.", fact_ids=[f.id])], data_cannot_tell_you=[])

    async def repair(_v):
        raise RuntimeError("boom")

    v = await validate.validate(bad, done, repair)
    assert v.report.claims == [] and len(v.report.data_cannot_tell_you) >= 2 and not v.audit.clean


async def test_cannot_section_merges_deterministic_caveats(done):
    v = await validate.validate(good_report(done), done)
    assert len(v.report.data_cannot_tell_you) >= 2 + len(validate.BASE_CAVEATS) - 0
    assert any("Medicare fee-for-service" in c for c in v.report.data_cannot_tell_you)


async def test_render_full_report(done):
    v = await validate.validate(good_report(done), done)
    md = render.render(v, done)
    assert md.startswith("## Heart failure") and "### What the data can't tell you" in md and "### Sources" in md
    assert "| # | Hospital |" in md and "Cost versus quality" in md
    assert "https://data.cms.gov" in md or "https://data.cms.gov".split("//")[1] in md
    assert "_Audit" not in md  # clean run has no audit line


async def test_render_audit_line_when_stripped(done):
    r = good_report(done)
    r.claims.append(Claim(text="Bogus $5,555,555.", fact_ids=[]))
    md = render.render(await validate.validate(r, done), done)
    assert "_Audit:" in md and "5,555,555" not in md


def test_partial_and_scope_with_no_facts(ctx):
    md = render.render_partial(ctx, "timed out")
    assert "Partial results" in md and "timed out" in md and "### Sources" in md
    md = render.render_scope(ctx, "Boston is outside New York.")
    assert "outside what the data can answer" in md and "Boston" in md and "can't tell you" in md


async def test_compose_with_stub_writer(done, monkeypatch):
    async def stub(c, payload):
        return good_report(c)
    monkeypatch.setattr(orchestrator, "_write", stub)
    md = await orchestrator.compose(done, done.question)
    assert md.startswith("## Heart failure") and "### Sources" in md


async def test_compose_writer_failure_falls_back_to_partial(done, monkeypatch):
    async def boom(c, payload):
        raise RuntimeError("model down")
    monkeypatch.setattr(orchestrator, "_write", boom)
    md = await orchestrator.compose(done, done.question)
    assert "Partial results" in md and "### Sources" in md


async def test_compose_out_of_scope_needs_no_researchers(ctx):
    md = await orchestrator.compose(ctx, "Mass General", "Massachusetts hospitals are not in the data.")
    assert "outside what the data can answer" in md


async def test_write_report_refuses_without_research(ctx):
    from tests.conftest import call
    import json
    r = json.loads(await call(orchestrator.write_report, ctx))
    assert "error" in r


async def test_fact_markers_removed(done):
    f = fact(done, "cost.drg291.state_avg")
    r = Report(headline="h", claims=[Claim(text=f"Average is {f.display} [F3][F4].", fact_ids=[f.id])], data_cannot_tell_you=["a", "b"])
    v = await validate.validate(r, done)
    assert "[F" not in v.report.claims[0].text
