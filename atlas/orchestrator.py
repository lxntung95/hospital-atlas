"""The Lead and its tools: resolve a cohort, fan out researchers in parallel, then write. `answer()` runs one request.

Phase 2 scope: the Lead is minimal (resolve -> dispatch -> write plain text). Analyst, Writer and validation arrive later.
"""

import asyncio
import json
from dataclasses import asdict, dataclass

from agents import Agent, RunContextWrapper, Runner, SQLiteSession
from agents.agent import StopAtTools

from atlas import analyst, config, crosswalk
from atlas.agents import COHORT_RETRIEVER, COST_RESEARCHER, MAX_TURNS, QUALITY_RESEARCHER, TOOL_SETTINGS
from atlas.context import RecordToolCalls, RequestContext
from atlas.schemas import CohortSpec, Finding, Gap, ResearchTask
from atlas.tools import err, make_cohort, ok, tool

HOOKS = RecordToolCalls()  # stateless: it writes into whichever request context the run carries
RESEARCHERS = {"cost": (COST_RESEARCHER, "cost"), "quality": (QUALITY_RESEARCHER, "quality")}
MIN_ROUND_S = 30  # do not start a round with less than this left after the writer reserve


# ---------------------------------------------------------------- cohort

async def _deterministic_spec(c: RequestContext, message: str) -> CohortSpec | None:
    """Fallback when the Retriever fails: build the cohort from crosswalk hints only."""
    from atlas import cms
    hospitals = (await cms.general_info_ny(c.client)).rows
    d = crosswalk.detect(message, hospitals)
    by_name = {h.name: h.ccn for h in hospitals}
    focus = [by_name[n] for n in d.hospital_hints if n in by_name]
    services = crosswalk.find_services(message)
    handle, _invalid, _sample = await make_cohort(c, focus, d.counties, statewide=not d.counties and not focus, label=d.region or "New York")
    if handle is None:
        return None
    return CohortSpec(cohort_handle=handle, hospital_ccns=c.cohorts[handle]["ccns"], focus_ccns=focus,
                      drg_codes=sorted({x for s in services for x in s.drgs}), measure_ids=sorted({m for s in services for m in s.measures}),
                      region_label=d.region or "New York", unresolved=[f"{t}: outside NY scope" for t in d.out_of_scope])


@tool
async def resolve_cohort(ctx: RunContextWrapper[RequestContext], request: str) -> str:
    """Find the hospitals, DRG codes and measure ids a request is about. Always call this first.

    Args:
        request: The user's request in their own words (include hospital names, region and condition).
    """
    c = ctx.context
    spec = None
    try:
        result = await asyncio.wait_for(
            Runner.run(COHORT_RETRIEVER, request, context=c.child("Cohort Retriever"), hooks=HOOKS, max_turns=MAX_TURNS["retriever"]), config.RETRIEVER_S)
        spec = CohortSpec.model_validate_json(result.final_output)
    except Exception:
        spec = await _deterministic_spec(c, request)
    if spec is None:
        return err("could not build a cohort", "ask the user for a hospital name, county or condition")
    from atlas import cms
    names = {h.ccn: h.name for h in (await cms.general_info_ny(c.client)).rows}
    c.cohorts[spec.cohort_handle]["spec"] = spec.model_dump()
    return ok(cohort_handle=spec.cohort_handle, n=len(spec.hospital_ccns), region_label=spec.region_label,
              focus_hospitals=[{"ccn": x, "name": names.get(x, x)} for x in spec.focus_ccns], drg_codes=spec.drg_codes,
              measure_ids=spec.measure_ids, unresolved=spec.unresolved)


# ---------------------------------------------------------------- fan-out

def _partial(task: ResearchTask, agent_name: str, c: RequestContext, reason: str) -> Finding:
    """A finding for a researcher that timed out or failed: keep any tables it managed to store."""
    tables = [t.id for t in c.tables.all() if t.meta.get("owner") == agent_name]
    sources = sorted({s for t in c.tables.all() if t.meta.get("owner") == agent_name for s in t.meta.get("source_ids", [])})
    return Finding(task_id=task.id, status="partial", agent=agent_name, table_handles=tables, source_ids=sources,
                   summary=f"{agent_name} did not finish ({reason}); any tables it stored are attached.",
                   gaps=[Gap(kind="missing_metric", detail=f"{task.kind} task {task.id} incomplete: {reason}", fillable=True)])


async def _run_one(c: RequestContext, task: ResearchTask, name: str, timeout: float) -> Finding:
    agent, key = RESEARCHERS[task.kind]
    child = c.child(name)
    try:
        result = await asyncio.wait_for(
            Runner.run(agent.clone(name=name), task.model_dump_json(), context=child, hooks=HOOKS, max_turns=MAX_TURNS[key]), timeout)
        finding = Finding.model_validate_json(result.final_output)
        return finding.model_copy(update={"task_id": task.id, "agent": name})
    except asyncio.TimeoutError:
        return _partial(task, name, c, f"timed out after {timeout:.0f}s")
    except Exception as exc:
        return _partial(task, name, c, f"{type(exc).__name__}")


@tool
async def dispatch_researchers(ctx: RunContextWrapper[RequestContext], tasks: list[ResearchTask]) -> str:
    """Send 2-4 research tasks to researchers who work IN PARALLEL, each with a fresh context. Returns their findings.

    Args:
        tasks: The tasks. kind is "cost" (DRG payments, needs drg_codes) or "quality" (needs measure_ids such as READM-30-HF-HRRP or MORT_30_HF, or ask about patient experience in the question). Every task needs the cohort_handle from resolve_cohort.
    """
    c = ctx.context
    if not 2 <= len(tasks) <= 4:
        return err(f"{len(tasks)} tasks given", "dispatch 2 to 4 tasks per round, ideally 3: cost, quality outcomes, patient experience/safety")
    if c.rounds_used >= 1 + config.MAX_GAP_ROUNDS:
        return err("round limit reached", "no more research rounds: call write_report with what you have")
    if c.remaining() < config.WRITER_RESERVE_S + MIN_ROUND_S:
        return err("budget exhausted", "write now: call write_report")
    for t in tasks:
        if t.cohort_handle not in c.cohorts:
            return err(f"unknown cohort handle {t.cohort_handle!r}", f"known handles: {', '.join(c.cohorts) or 'none'}")
    c.rounds_used += 1
    timeout = min(config.RESEARCHER_S, c.remaining() - config.WRITER_RESERVE_S)
    names = []
    for t in tasks:
        c.counters["researchers"] += 1
        names.append(f"{t.kind.title()} Researcher R{c.counters['researchers']}")
    findings = await asyncio.gather(*(_run_one(c, t, n, timeout) for t, n in zip(tasks, names)))
    try:
        analysis = await analyst.analyze(c)
        gaps = [g.model_dump() for g in analysis.gaps]
    except Exception as e:  # the analysis must never sink the request
        c.record("Analyst", "analyze", {}, f"failed: {type(e).__name__}: {e}")
        analysis, gaps = None, []
    return ok(round=c.rounds_used, rounds_left=1 + config.MAX_GAP_ROUNDS - c.rounds_used,
              facts_count=len(analysis.facts) if analysis else 0, gaps=gaps,
              findings=[f.model_dump(exclude={"gaps"}) | {"gaps": [g.detail for g in f.gaps]} for f in findings],
              tables=[{"handle": t.id, "title": t.title, "rows": len(t.rows)} for t in c.tables.all()])


@tool
async def write_report(ctx: RunContextWrapper[RequestContext], text: str) -> str:
    """Finish with the final answer for the user. Always the last call.

    Args:
        text: The answer, in plain sentences, using only facts from the findings. Say what the data cannot tell you.
    """
    return text


LEAD = Agent(
    name="Lead",
    instructions="""You are Hospital Atlas, a research lead for New York hospital cost and quality (Medicare data, CMS). Work in this order:
1. Call resolve_cohort once with the user's request.
2. Call dispatch_researchers once with three tasks (ids R1, R2, R3) using the returned cohort_handle: (a) kind "cost" with the drg_codes, (b) kind "quality" with the readmission and mortality/complication measure_ids, (c) kind "quality" about patient experience and patient-safety indicators (PSI_* ids if any). If there are no drg_codes, use two quality tasks and one cost task for the DRGs you think fit, taken from find results only.
3. Call write_report with a short answer built only from the findings: lead with the answer, name hospitals and numbers exactly as the findings give them, and finish with one sentence on what the data cannot tell you. If anything is unresolved or outside New York, say so plainly.
Never invent numbers. Only New York hospitals exist in your data.""",
    model=config.MODEL, model_settings=TOOL_SETTINGS, tools=[resolve_cohort, dispatch_researchers, write_report],
    tool_use_behavior=StopAtTools(stop_at_tool_names=["write_report"]), reset_tool_choice=False,
)


# ---------------------------------------------------------------- one request

@dataclass
class Answer:
    text: str
    tool_calls: list[dict]
    ctx: RequestContext


async def answer(message: str, session_id: str, client=None) -> Answer:
    ctx = RequestContext(client=client)
    result = await Runner.run(LEAD, message, context=ctx, hooks=HOOKS, session=SQLiteSession(session_id, config.SESSIONS_DB), max_turns=8)
    return Answer(str(result.final_output), ctx.tool_calls, ctx)
