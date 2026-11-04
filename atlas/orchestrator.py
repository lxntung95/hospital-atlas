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
from atlas.agents import COHORT_RETRIEVER, CRITIC, WRITER, COST_RESEARCHER, MAX_TURNS, QUALITY_RESEARCHER, TOOL_SETTINGS
from atlas.context import RecordToolCalls, RequestContext
from atlas.schemas import CohortSpec, Critique, Finding, Gap, Report, ResearchTask
from atlas.tools import ToolError, make_cohort, ok, tool

HOOKS = RecordToolCalls()  # stateless: it writes into whichever request context the run carries
RESEARCHERS = {"cost": COST_RESEARCHER, "quality": QUALITY_RESEARCHER}
CLARIFY_MARK = "Reply with one of these"  # the UI looks for the same text to show the options as buttons


def tuned(agent: Agent, c: RequestContext) -> Agent:
    """The agent as configured for this request: chosen model and reasoning effort. Never mutates the shared agent."""
    if c.model is None and not c.effort:
        return agent
    # Only the Lead gets the chosen reasoning; the others just call tools or write, and extra reasoning only adds latency (it made Balanced take 110 s).
    reasoning = config.effort(c.effort).lead if agent.name == "Lead" else "low"
    return agent.clone(model_settings=config.effort_settings(agent.model_settings, reasoning), **({"model": c.model} if c.model is not None else {}))


def turns(base: int, c: RequestContext) -> int:
    return base + config.effort(c.effort).extra_turns


async def run_agent(agent: Agent, c: RequestContext, owner: str, payload: str, model: type, timeout: float | None, max_turns: int):
    """One nested agent run in its own context view, tuned to this request and time-limited; the output is parsed as `model`."""
    agent = tuned(agent, c)
    if agent.name != owner:
        agent = agent.clone(name=owner)
    out = (await asyncio.wait_for(Runner.run(agent, payload, context=c.child(owner), hooks=HOOKS, max_turns=max_turns), timeout)).final_output
    return out if isinstance(out, model) else model.model_validate_json(str(out))


# ---------------------------------------------------------------- cohort

async def _deterministic_spec(c: RequestContext, message: str) -> CohortSpec | None:
    """Fallback when the Retriever fails: build the cohort from crosswalk hints only."""
    hospitals = (await cms.hospitals(c.client)).values()
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
    try:
        spec = await run_agent(COHORT_RETRIEVER, c, "Cohort Retriever", request, CohortSpec, config.RETRIEVER_S, turns(MAX_TURNS["retriever"], c))
    except Exception:
        spec = await _deterministic_spec(c, request)
    if spec is None:
        raise ToolError("could not build a cohort", "ask the user for a hospital name, county or condition")
    hospitals = await cms.hospitals(c.client)
    if not spec.focus_ccns:  # "Bronx hospitals vs the rest of NY": the named region is the focus even if the cohort is statewide
        members = c.cohorts[spec.cohort_handle]["ccns"]
        spec.focus_ccns = [h.ccn for h in cms.acute(hospitals, crosswalk.find_region(request)[1]) if h.ccn in members][:12]
    c.cohorts[spec.cohort_handle]["spec"] = spec.model_dump()
    return ok(cohort_handle=spec.cohort_handle, n=len(spec.hospital_ccns), region_label=spec.region_label,
              focus_hospitals=[{"ccn": x, "name": hospitals[x].name if x in hospitals else x} for x in spec.focus_ccns], drg_codes=spec.drg_codes,
              measure_ids=spec.measure_ids, unresolved=spec.unresolved)


# ---------------------------------------------------------------- fan-out

def _partial(task: ResearchTask, agent_name: str, c: RequestContext, reason: str) -> Finding:
    """A finding for a researcher that timed out or failed: keep any tables it managed to store."""
    c.partials.append(f"{task.kind} task {task.id} ({agent_name}) did not finish: {reason}")
    mine = [t for t in c.tables.all() if t.meta.get("owner") == agent_name]
    return Finding(task_id=task.id, status="partial", agent=agent_name, table_handles=[t.id for t in mine], source_ids=sorted({s for t in mine for s in t.source_ids}),
                   summary=f"{agent_name} did not finish ({reason}); any tables it stored are attached.",
                   gaps=[Gap(kind="missing_metric", detail=f"{task.kind} task {task.id} incomplete: {reason}", fillable=True)])


async def _run_one(c: RequestContext, task: ResearchTask, name: str, timeout: float) -> Finding:
    try:
        fault = os.environ.get("ATLAS_FAULT", "")  # test/eval switch: break every cost researcher
        if fault and task.kind == "cost":
            if fault == "timeout":
                raise asyncio.TimeoutError
            raise RuntimeError("injected fault")
        finding = await run_agent(RESEARCHERS[task.kind], c, name, task.model_dump_json(), Finding, timeout, turns(MAX_TURNS[task.kind], c))
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
        raise ToolError(f"{len(tasks)} tasks given", "round 1 needs 3 or 4 tasks: cost, quality outcomes, patient experience/safety" if low == 3 else "a gap round takes 1 to 4 tasks")
    if c.rounds_left <= 0:
        raise ToolError("round limit reached", "no more research rounds: call write_report with what you have")
    if not c.can_research():
        raise ToolError("budget exhausted", "write now: call write_report")
    for t in tasks:
        if t.cohort_handle not in c.cohorts:
            raise ToolError(f"unknown cohort handle {t.cohort_handle!r}", f"known handles: {', '.join(c.cohorts) or 'none'}")
    return await _run_round(c, tasks)


async def _run_round(c: RequestContext, tasks: list[ResearchTask]) -> str:
    """One parallel research round plus the analysis. Shared by the Lead's dispatch tool and the automatic gap round."""
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
    return ok(round=c.rounds_used, rounds_left=c.rounds_left,
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
    return await run_agent(WRITER, c, "Writer", payload, Report, None, 2)


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


def _critic_input(c: RequestContext, question: str) -> str:
    return json.dumps({"question": question, "facts": [{"label": f.label, "display": f.display} for f in c.facts[:80]],
                       "known_gaps": [g.detail for g in c.gaps], "allowed_measure_ids": sorted(crosswalk.measures()),
                       "allowed_drgs": sorted({r["drg"] for t in c.tables.all() for r in t.rows if isinstance(r.get("drg"), int)})})


def _new_tasks(c: RequestContext, specs: list[tuple]) -> list[ResearchTask]:
    """Research tasks for the latest cohort from (kind, question, drg_codes, measure_ids) tuples, with fresh ids R<n>."""
    handle, n = list(c.cohorts)[-1], c.counters["researchers"]
    return [ResearchTask(id=f"R{n + i}", kind=k, question=q, cohort_handle=handle, drg_codes=d, measure_ids=m) for i, (k, q, d, m) in enumerate(specs, 1)]


def _critique_tasks(c: RequestContext, crit: Critique) -> list[ResearchTask]:
    """Validate the Critic's suggestions against the real measure list; drop anything invented."""
    known, specs = crosswalk.measures(), []
    for t in crit.tasks[:2]:
        drgs, ms = [d for d in t.drg_codes if 100 <= d <= 999][:3], [m for m in t.measure_ids if m in known][:4]
        if (t.kind == "cost" and drgs) or (t.kind == "quality" and ms):
            specs.append((t.kind, t.why, drgs, ms))
    return _new_tasks(c, specs)


async def run_critic(c: RequestContext, question: str) -> None:
    """Thinking mode only: an LLM reads the analysed facts against the question. Unanswered parts become known gaps (the Writer states
    them); valid extra lookups run as one more gap round. Any failure or timeout is skipped so the answer is never delayed past config.CRITIC_S."""
    c.stage("reviewing the analysis")
    try:
        crit = await run_agent(CRITIC, c, "Critic", _critic_input(c, question), Critique, config.CRITIC_S, 2)
    except Exception as exc:
        c.record("Critic", "review", {}, f"skipped: {type(exc).__name__}")
        return
    tasks = _critique_tasks(c, crit)
    c.record("Critic", "review", {"unanswered": crit.unanswered[:3]}, f"{len(crit.unanswered)} unanswered, {len(tasks)} extra lookups")
    if tasks and c.can_research():
        await _run_round(c, tasks)  # the Analyst re-runs and recomputes the gaps, so the Critic's notes would be overwritten: skip them
        return
    for u in crit.unanswered[:3]:  # nothing to look up: say so in the report (the Writer sees gaps; "can't tell you" lists unfillable ones)
        c.gaps.append(Gap(kind="missing_metric", detail=f"Not covered by the data gathered: {u}", fillable=False))


def _gap_tasks(c: RequestContext) -> list[ResearchTask]:
    specs, seen = [], set()
    for g in c.gaps:
        t = g.suggested_task if g.fillable else None
        key = json.dumps(t, sort_keys=True)
        if t and key not in seen and len(specs) < 3:
            seen.add(key)
            specs.append((t["kind"], g.detail, t.get("drg_codes", []), t.get("measure_ids", [])))
    return _new_tasks(c, specs)


@tool
async def write_report(ctx: RunContextWrapper[RequestContext], reason: str = "") -> str:
    """Finish: produce the final cited report for the user. Always the last call. Takes no text: the report is written from the analysed facts.

    Args:
        reason: Leave empty after dispatch_researchers. Only if the question cannot be answered from New York hospital data (other state, unsupported topic, nothing found), give a one-sentence reason instead of dispatching.
    """
    c = ctx.context
    if c.rounds_used == 0 and not reason:
        raise ToolError("no research has run", "call resolve_cohort and dispatch_researchers first, or pass reason if the question is out of scope")
    if not reason and c.rounds_used >= 1 and c.cohorts and c.can_research(15):
        tasks = _gap_tasks(c)  # the Lead skipped a fillable gap: run one deterministic gap round so the report is complete
        if tasks:
            c.record("Lead", "auto_gap_round", {"tasks": [t.id for t in tasks]}, "fillable gaps remained; filled automatically before writing")
            await _run_round(c, tasks)
    if config.effort(c.effort).critic and c.rounds_used >= 1 and c.facts and not reason and c.remaining() >= config.WRITER_RESERVE_S + config.CRITIC_S + 5:
        await run_critic(c, c.question)
    return await compose(c, c.question, reason)


CLARIFY_FALLBACK = {"question": "Which part of New York hospital care should I look at?",
                    "options": ["Cost of a procedure (for example hip or knee replacement)", "Quality for a condition (for example heart failure readmissions)",
                                "A specific hospital or borough (for example the Bronx)", "Both cost and quality for one condition"]}


def clarification_text(question: str, options: list[str]) -> str:
    return "## " + question.strip() + "\n\n" + "\n".join(f"- {o}" for o in options[:4]) + "\n\n" + CLARIFY_MARK + ", or tell me the hospital, condition and region you care about."


@tool
async def ask_clarifying_question(ctx: RunContextWrapper[RequestContext], question: str, options: list[str]) -> str:
    """Ask the user ONE clarifying question instead of researching. Only for requests too vague to research (no condition, procedure, hospital or region). Always the last call.

    Args:
        question: One short question.
        options: 3 or 4 concrete answers the user can pick, each mentioning a condition or procedure, a region, or cost versus quality.
    """
    c = ctx.context
    if c.prev_clarified:
        raise ToolError("already asked", "do not ask again: choose a reasonable scope (statewide, the most common DRG) and call resolve_cohort")
    if c.rounds_used > 0:
        raise ToolError("research already started", "call write_report")
    if len(options) < 3:
        raise ToolError("need 3 or 4 options", "give concrete options: a condition or procedure, a region, cost versus quality")
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
    d = crosswalk.detect(message, (await cms.hospitals(ctx.client)).values())
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
            ctx.prev_clarified = ctx.prev_clarified or (history[-1].get("role") == "assistant" and CLARIFY_MARK in str(history[-1].get("content")))
        text = await asyncio.wait_for(_run_lead(ctx, message, session_id), config.REQUEST_S)
    except asyncio.TimeoutError:
        text = await _rescue(ctx, "the time limit was reached", write=False)
    except Exception as exc:
        text = await _rescue(ctx, f"{type(exc).__name__} in the research loop", write=ctx.remaining() > config.WRITER_RESERVE_S)
    _CLARIFIED[session_id] = ctx.clarified
    try:
        ctx.artifacts = render.build_artifacts(ctx, await cms.hospitals(ctx.client))
    except Exception:
        ctx.artifacts = None
    return Answer(text, ctx.tool_calls, ctx)
