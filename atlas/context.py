"""Per-request state shared by the Lead and every nested researcher run, plus the hooks that record tool calls."""

import json
import time
from dataclasses import dataclass, field, replace

from agents import RunHooks

from atlas import config
from atlas.http import CmsClient
from atlas.sources import SourceRegistry
from atlas.store import TableStore


@dataclass
class RunState:
    """What /progress reports about a request that is still running. Shared by reference with every child context."""

    stage: str = "starting"
    status: str = "running"  # running | done | error


@dataclass
class RequestContext:
    """Passed as `context=` to every Runner.run in a request. Mutable members are shared by reference."""

    client: CmsClient | None = None  # None -> the process-wide client; tests inject one backed by the shipped fallback
    tables: TableStore = field(default_factory=TableStore)
    sources: SourceRegistry = field(default_factory=SourceRegistry)
    tool_calls: list[dict] = field(default_factory=list)
    cohorts: dict[str, dict] = field(default_factory=dict)  # handle -> {"ccns": [...], "label": str}
    question: str = ""
    run: RunState = field(default_factory=RunState)
    model: object | None = None  # per-request LitellmModel (None -> the agents' own)
    model_id: str = ""
    effort: str = ""
    audit: dict | None = None
    artifacts: dict | None = None
    prev_clarified: bool = False  # the previous assistant turn in this conversation was a clarification question
    partials: list = field(default_factory=list)  # researcher tasks that timed out or failed this request
    clarified: bool = False  # this turn ended in one
    nudged: bool = False  # the Lead has been told once that fillable gaps remain
    reported: bool = False  # write_report produced the final report
    facts: list = field(default_factory=list)  # filled by atlas.analyst.analyze
    gaps: list = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=lambda: {"researchers": 0})
    started: float = field(default_factory=time.monotonic)
    budget_s: float = config.REQUEST_S
    rounds_used: int = 0  # research rounds run so far (the Lead's dispatches, the automatic gap round, the Critic's round)
    owner: str = "Lead"  # which agent run this context view belongs to

    def child(self, owner: str) -> "RequestContext":
        """A view for one nested run: shares tables, sources, tool_calls and cohorts, but knows its owner."""
        return replace(self, owner=owner)

    def stage(self, text: str) -> None:
        self.run.stage = text

    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def remaining(self) -> float:
        return self.budget_s - self.elapsed()

    @property
    def max_rounds(self) -> int:
        return 1 + config.effort(self.effort).gap_rounds

    @property
    def rounds_left(self) -> int:
        return self.max_rounds - self.rounds_used

    def can_research(self, extra_s: float = 0) -> bool:
        """Another round is allowed and there is time for it plus the Writer reserve."""
        return self.rounds_left > 0 and self.remaining() >= config.WRITER_RESERVE_S + config.MIN_ROUND_S + extra_s

    def record(self, agent: str, name: str, args: dict, result: str) -> None:
        """Add a synthetic entry (for code steps such as the Analyst) to tool_calls."""
        self.tool_calls.append({"agent": agent, "name": name, "args": args, "result": str(result)[:800], "t": round(self.elapsed(), 1)})


class RecordToolCalls(RunHooks):
    """Stateless: records each tool call into the request context, tagged with the agent that made it."""

    async def on_tool_end(self, context, agent, tool, result):
        try:
            args = json.loads(context.tool_arguments)
        except (TypeError, ValueError):
            args = {"raw": str(context.tool_arguments)}
        context.context.record(agent.name, tool.name, args, result)
