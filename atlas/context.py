"""Per-request state. Hooks that record tool calls are added in Phase 2."""

import time
from dataclasses import dataclass, field

from atlas.config import REQUEST_S
from atlas.sources import SourceRegistry
from atlas.store import TableStore


@dataclass
class RequestContext:
    tables: TableStore = field(default_factory=TableStore)
    sources: SourceRegistry = field(default_factory=SourceRegistry)
    tool_calls: list[dict] = field(default_factory=list)
    started: float = field(default_factory=time.monotonic)
    budget_s: float = REQUEST_S
    rounds_used: int = 0

    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def remaining(self) -> float:
        return self.budget_s - self.elapsed()
