"""The Lead and its tools: resolve a cohort, fan out researchers in parallel, then write. `answer()` runs one request.

The Lead plans, fans out researchers, fills fillable gaps (max 2 extra rounds), then write_report composes the cited answer.
"""

import asyncio
import json
import os
from dataclasses import asdict, dataclass

from agents import Agent, RunContextWrapper, Runner, SQLiteSession
from agents.agent import StopAtTools

from atlas import analyst, cms, config, crosswalk, render, validate
from atlas.agents import COHORT_RETRIEVER, WRITER, COST_RESEARCHER, MAX_TURNS, QUALITY_RESEARCHER, TOOL_SETTINGS
from atlas.context import RecordToolCalls, RequestContext
from atlas.schemas import CohortSpec, Finding, Gap, Report, ResearchTask
from atlas.tools import err, make_cohort, ok, tool

HOOKS = RecordToolCalls()  # stateless: it writes into whichever request context the run carries
RESEARCHERS = {"cost": (COST_RESEARCHER, "cost"), "quality": (QUALITY_RESEARCHER, "quality")}
MIN_ROUND_S = 30


def tuned(agent: Agent, c: RequestContext) -> Agent:
    """The agent as configured for this request: chosen model and reasoning effort. Never mutates the shared agent."""
    if c.model is None and not c.effort:
        return agent
    kw = {}
    if c.model is not None:
        kw["model"] = c.model
    if c.effort:
        kw["model_settings"] = config.effort_settings(agent.model_settings, c.effort)
    return agent.clone(**kw)


def turns(base: int, c: RequestContext) -> int:
    return base + config.EXTRA_TURNS.get(c.effort, 0)  # do not start a round with less than this left after the writer reserve


# ---------------------------------------------------------------- cohort

async def _deterministic_spec(c: RequestContext, message: str) -> CohortSpec | None:
    """Fallback when the Retriever fails: build the cohort from crosswalk hints only."""
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
    c.stage("finding hospitals")
    spec = None
    try:
        result = await asyncio.wait_for(
            Runner.run(tuned(COHORT_RETRIEVER, c), request, context=c.child("Cohort Retriever"), hooks=HOOKS, max_turns=turns(MAX_TURNS["retriever"], c)), config.RETRIEVER_S)
        spec = CohortSpec.model_validate_json(result.final_output)
    except Exception:
        spec = await _deterministic_spec(c, request)
    if spec is None:
        return err("could not build a cohort", "ask the user for a hospital name, county or condition")
    hospitals = (await cms.general_info_ny(c.client)).rows
    names = {h.ccn: h.name for h in hospitals}
    if not spec.focus_ccns:  # "Bronx hospitals vs the rest of NY": the named region is the focus even if the cohort is statewide
        _region, counties = crosswalk.find_region(request)
        wanted = {x.casefold() for x in counties}
        spec.focus_ccns = [h.ccn for h in hospitals if h.type == "Acute Care Hospitals" and h.county.casefold() in wanted and h.ccn in c.cohorts[spec.cohort_handle]["ccns"]][:12]
    c.cohorts[spec.cohort_handle]["spec"] = spec.model_dump()
    return ok(cohort_handle=spec.cohort_handle, n=len(spec.hospital_ccns), region_label=spec.region_label,
              focus_hospitals=[{"ccn": x, "name": names.get(x, x)} for x in spec.focus_ccns], drg_codes=spec.drg_codes,
              measure_ids=spec.measure_ids, unresolved=spec.unresolved)


# ---------------------------------------------------------------- fan-out

def _partial(task: ResearchTask, agent_name: str, c: RequestContext, reason: str) -> Finding:
    """A finding for a researcher that timed out or failed: keep any tables it managed to store."""
    c.partials.append(f"{task.kind} task {task.id} ({agent_name}) did not finish: {reason}")
    tables = [t.id for t in c.tables.all() if t.meta.get("owner") == agent_name]
    sources = sorted({s for t in c.tables.all() if t.meta.get("owner") == agent_name for s in t.meta.get("source_ids", [])})
    return Finding(task_id=task.id, status="partial", agent=agent_name, table_handles=tables, source_ids=sources,
                   summary=f"{agent_name} did not finish ({reason}); any tables it stored are attached.",
                   gaps=[Gap(kind="missing_metric", detail=f"{task.kind} task {task.id} incomplete: {reason}", fillable=True)])


async def _run_one(c: RequestContext, task: ResearchTask, name: str, timeout: float) -> Finding:
    agent, key = RESEARCHERS[task.kind]
    child = c.child(name)
    try:
        fault = os.environ.get("ATLAS_FAULT", "")  # test/eval switch: break every cost researcher
        if fault and task.kind == "cost":
            if fault == "timeout":
                raise asyncio.TimeoutError
            raise RuntimeError("injected fault")
        result = await asyncio.wait_for(
            Runner.run(tuned(agent, c).clone(name=name), task.model_dump_json(), context=child, hooks=HOOKS, max_turns=turns(MAX_TURNS[key], c)), timeout)
        finding = Finding.model_validate_json(result.final_output)
        return finding.model_copy(update={"task_id": task.id, "agent": name})
    except asyncio.TimeoutError:
        return _partial(task, name, c, f"timed out after {timeout:.0f}s")
    except Exception as exc:
        return _partial(task, name, c, f"{type(exc).__name__}")


@tool
async def dispatch_researchers(ctx: RunContextWrapper[RequestContext], tasks: list[ResearchTask]) -> str:
    """Send research tasks to researchers who work IN PARALLEL, each with a fresh context. Round 1: 3-4 tasks. Gap rounds: 1-4 tasks. Returns findings, analysed facts_count and gaps.

    Args:
        tasks: The tasks. kind is "cost" (DRG payments, needs drg_codes) or "quality" (needs measure_ids such as READM-30-HF-HRRP or MORT_30_HF, or ask about patient experience in the question). Every task needs the cohort_handle from resolve_cohort.
    """
    c = ctx.context
    low = 3 if c.rounds_used == 0 else 1  # first round fans out wide; gap rounds can be a single targeted task
    if not low <= len(tasks) <= 4:
        return err(f"{len(tasks)} tasks given", "round 1 needs 3 or 4 tasks: cost, quality outcomes, patient experience/safety" if low == 3 else "a gap round takes 1 to 4 tasks")
    if c.rounds_used >= 1 + config.MAX_GAP_ROUNDS:
        return err("round limit reached", "no more research rounds: call write_report with what you have")
    if c.remaining() < config.WRITER_RESERVE_S + MIN_ROUND_S:
        return err("budget exhausted", "write now: call write_report")
    for t in tasks:
        if t.cohort_handle not in c.cohorts:
            return err(f"unknown cohort handle {t.cohort_handle!r}", f"known handles: {', '.join(c.cohorts) or 'none'}")
    c.rounds_used += 1
    c.stage(f"researching (round {c.rounds_used}, {len(tasks)} researchers in parallel)")
    timeout = min(config.RESEARCHER_S, c.remaining() - config.WRITER_RESERVE_S)
    names = []
    for t in tasks:
        c.counters["researchers"] += 1
        names.append(f"{t.kind.title()} Researcher R{c.counters['researchers']}")
    findings = await asyncio.gather(*(_run_one(c, t, n, timeout) for t, n in zip(tasks, names)))
    c.stage("analysing")
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


def _writer_input(c: RequestContext, question: str) -> dict:
    facts = c.facts[:150]
    return {"question": question,
            "facts": [{"id": f.id, "label": f.label, "display": f.display, "sources": f.source_ids, "caveats": f.caveats} for f in facts],
            "gaps": [{"kind": g.kind, "detail": g.detail} for g in c.gaps],
            "sources": [{"id": s.id, "dataset": s.dataset, "period": s.period} for s in c.sources.all()]}


async def _write(c: RequestContext, payload: str) -> Report | None:
    result = await Runner.run(tuned(WRITER, c), payload, context=c.child("Writer"), max_turns=2)
    out = result.final_output
    return out if isinstance(out, Report) else Report.model_validate_json(str(out))


async def compose(c: RequestContext, question: str, reason: str = "") -> str:
    """Writer -> validate (repair once) -> render. Falls back to a model-free partial report; never returns unvalidated Writer text."""
    if c.rounds_used == 0 or not c.facts:
        c.record("Writer", "render_scope" if reason else "render_partial", {"reason": reason}, "no researchers ran" if c.rounds_used == 0 else "no facts")
        return render.render_scope(c, reason) if reason or c.rounds_used == 0 else render.render_partial(c, "no figures were produced")
    c.stage("writing and checking the report")
    payload = json.dumps(_writer_input(c, question))
    try:
        first = await asyncio.wait_for(_write(c, payload), config.WRITER_S)
    except Exception as exc:
        c.record("Writer", "write", {}, f"failed: {type(exc).__name__}")
        return render.render_partial(c, "the writer step failed, so these are the verified figures only")

    async def repair(violations):
        msg = payload + "\n\nYour previous draft had problems. Fix them and return the full report again:\n- " + "\n- ".join(violations[:12])
        return await asyncio.wait_for(_write(c, msg), max(10, config.WRITER_RESERVE_S - config.WRITER_S))

    v = await validate.validate(first, c, repair)
    c.audit = {**asdict(v.audit), "violations": len(v.violations)}
    c.record("Writer", "validate", {}, f"{len(v.violations)} violations after {'repair' if v.audit.repaired else 'first draft'}; audit clean={v.audit.clean}")
    return render.render(v, c)


@tool
async def write_report(ctx: RunContextWrapper[RequestContext], reason: str = "") -> str:
    """Finish: produce the final cited report for the user. Always the last call. Takes no text: the report is written from the analysed facts.

    Args:
        reason: Leave empty after dispatch_researchers. Only if the question cannot be answered from New York hospital data (other state, unsupported topic, nothing found), give a one-sentence reason instead of dispatching.
    """
    c = ctx.context
    if c.rounds_used == 0 and not reason:
        return err("no research has run", "call resolve_cohort and dispatch_researchers first, or pass reason if the question is out of scope")
    return await compose(c, c.question, reason)


CLARIFY_FALLBACK = {"question": "Which part of New York hospital care should I look at?",
                    "options": ["Cost of a procedure (for example hip or knee replacement)", "Quality for a condition (for example heart failure readmissions)",
                                "A specific hospital or borough (for example the Bronx)", "Both cost and quality for one condition"]}


def clarification_text(question: str, options: list[str]) -> str:
    return "## " + question.strip() + "\n\n" + "\n".join(f"- {o}" for o in options[:4]) + "\n\nReply with one of these, or tell me the hospital, condition and region you care about."


@tool
async def ask_clarifying_question(ctx: RunContextWrapper[RequestContext], question: str, options: list[str]) -> str:
    """Ask the user ONE clarifying question instead of researching. Only for requests too vague to research (no condition, procedure, hospital or region). Always the last call.

    Args:
        question: One short question.
        options: 3 or 4 concrete answers the user can pick, each mentioning a condition or procedure, a region, or cost versus quality.
    """
    c = ctx.context
    if c.prev_clarified:
        return err("already asked", "do not ask again: choose a reasonable scope (statewide, the most common DRG) and call resolve_cohort")
    if c.rounds_used > 0:
        return err("research already started", "call write_report")
    if len(options) < 3:
        return err("need 3 or 4 options", "give concrete options: a condition or procedure, a region, cost versus quality")
    c.clarified = True
    return clarification_text(question, options)


LEAD_COMMON = """You are Hospital Atlas, a research lead for New York hospital cost and quality (Medicare data, CMS). Only New York hospitals exist in your data. Never invent numbers; you do not write the answer text."""

LEAD = Agent(
    name="Lead",
    instructions=LEAD_COMMON + """ Work in this order:
1. Call resolve_cohort once with the user's request (include any condition and region from earlier in the conversation).
2. Call dispatch_researchers ONCE with exactly three tasks (ids R1, R2, R3) using the returned cohort_handle:
   R1 kind "cost" with the drg_codes; R2 kind "quality" with the readmission and mortality/complication measure_ids; R3 kind "quality" about patient experience and patient-safety indicators (PSI_* ids if any are in measure_ids).
   Example task: {"id":"R1","kind":"cost","question":"Average Medicare payment by hospital for DRG 291","cohort_handle":"C1","drg_codes":[291],"measure_ids":[]}.
   If resolve_cohort gave no drg_codes, still send the three tasks, choosing DRGs only from find results.
3. Read the result. If it lists gaps with fillable true and a suggested_task, and rounds_left is above 0, call dispatch_researchers again with ONLY those suggested tasks (one to three, new ids R4, R5...). Do this at most twice. Do not repeat a task. Unfillable gaps are not retried: the report states them.
4. Call write_report with no arguments. It writes, checks and cites the report; you never write the answer.
If the question is not about New York hospital cost or quality (another state, an unsupported topic) call write_report with reason set to one plain sentence, without researching. Never call ask_clarifying_question in this mode.""",
    model=config.MODEL, model_settings=TOOL_SETTINGS, tools=[resolve_cohort, dispatch_researchers, write_report],
    tool_use_behavior=StopAtTools(stop_at_tool_names=["write_report"]), reset_tool_choice=False,
)

LEAD_CLARIFY = Agent(
    name="Lead",
    instructions=LEAD_COMMON + """ The user's request is too vague to research (no condition, procedure, hospital or region). Call ask_clarifying_question once with a short question and 3 or 4 concrete options, for example a procedure's cost in a region, a condition's quality, or comparing named hospitals.""",
    model=config.MODEL, model_settings=TOOL_SETTINGS, tools=[ask_clarifying_question],
    tool_use_behavior=StopAtTools(stop_at_tool_names=["ask_clarifying_question"]), reset_tool_choice=False,
)


# ---------------------------------------------------------------- one request

@dataclass
class Answer:
    text: str
    tool_calls: list[dict]
    ctx: RequestContext


_CLARIFIED: dict[str, bool] = {}  # session id -> the last assistant turn was a clarification (one instance, so in-memory is enough)


def _hints(d: crosswalk.Detected) -> str:
    bits = []
    if d.condition:
        bits.append(f"condition={d.condition}")
    if d.region:
        bits.append(f"region={d.region}")
    if d.out_of_scope:
        bits.append("outside New York: " + ", ".join(d.out_of_scope))
    return f"\n\n[system hints: {'; '.join(bits)}]" if bits else ""


async def _rescue(ctx: RequestContext, reason: str, write: bool) -> str:
    """The safety net: whatever happened, return something honest built from what was gathered. Never raises."""
    try:
        if ctx.tables.all() and not ctx.facts:
            await asyncio.wait_for(analyst.analyze(ctx), 10)
        if ctx.facts:
            if write:
                return await asyncio.wait_for(compose(ctx, ctx.question), config.WRITER_RESERVE_S)
            return render.render_partial(ctx, reason)
    except Exception:
        if ctx.facts:
            return render.render_partial(ctx, reason)
    return "I could not finish that request (" + reason + ").\n\n" + clarification_text(**CLARIFY_FALLBACK)


async def _run_lead(ctx: RequestContext, message: str, session_id: str) -> str:
    session = SQLiteSession(session_id, config.SESSIONS_DB)
    first_turn = not await session.get_items(limit=1)
    hospitals = (await cms.general_info_ny(ctx.client)).rows
    d = crosswalk.detect(message, hospitals)
    vague = first_turn and d.vague and not d.out_of_scope and not ctx.prev_clarified
    result = await Runner.run(tuned(LEAD_CLARIFY if vague else LEAD, ctx), message + _hints(d), context=ctx, hooks=HOOKS, session=session, max_turns=turns(8, ctx))
    if vague and not ctx.clarified:
        ctx.clarified = True
        return clarification_text(**CLARIFY_FALLBACK)
    return str(result.final_output)


HISTORY_MAX = 12


async def seed_history(session: SQLiteSession, history: list[dict]) -> int:
    """Restore a saved chat into an empty session so the Lead continues coherently. Returns the number of items added."""
    if await session.get_items(limit=1):
        return 0  # never overwrite a live conversation
    items = [{"role": h["role"], "content": str(h["content"])[:4000]} for h in history[-HISTORY_MAX:] if h.get("role") in ("user", "assistant") and h.get("content")]
    if items:
        await session.add_items(items)
    return len(items)


async def answer(message: str, session_id: str, client=None, model_id: str | None = None, effort: str | None = None,
                 history: list[dict] | None = None, on_start=None) -> Answer:
    """model_id / effort must already be validated by the caller (config.build_model raises on unknown ids)."""
    ctx = RequestContext(client=client)
    ctx.question = message
    ctx.prev_clarified = _CLARIFIED.get(session_id, False)
    if model_id:
        ctx.model, ctx.model_id = config.build_model(model_id), model_id
    ctx.effort = effort or ""
    if on_start:
        on_start(ctx)
    try:
        if history:
            await seed_history(SQLiteSession(session_id, config.SESSIONS_DB), history)
            ctx.prev_clarified = ctx.prev_clarified or (history[-1].get("role") == "assistant" and "Reply with one of these" in str(history[-1].get("content")))
        text = await asyncio.wait_for(_run_lead(ctx, message, session_id), config.REQUEST_S)
    except asyncio.TimeoutError:
        text = await _rescue(ctx, "the time limit was reached", write=False)
    except Exception as exc:
        text = await _rescue(ctx, f"{type(exc).__name__} in the research loop", write=ctx.remaining() > config.WRITER_RESERVE_S)
    _CLARIFIED[session_id] = ctx.clarified
    try:
        hospitals = {h.ccn: h for h in (await cms.general_info_ny(ctx.client)).rows}
        ctx.artifacts = render.build_artifacts(ctx, hospitals)
    except Exception:
        ctx.artifacts = None
    return Answer(text, ctx.tool_calls, ctx)
