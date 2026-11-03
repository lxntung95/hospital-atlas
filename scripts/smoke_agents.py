"""M0 smoke test: does the Agents SDK pattern we plan to rely on work through LiteLLM on Gemini?

Checks, in order:
  1. A tool agent ends on a terminal submit tool (StopAtTools + tool_choice="required").
  2. A tool can run a nested Runner.run (the Lead's dispatch_researchers does this).
  3. asyncio.gather over fresh runs really runs in parallel, and one shared RunHooks sees every call.

Run: uv run scripts/smoke_agents.py
"""

import asyncio
import json
import time

from agents import (
    Agent,
    ModelSettings,
    RunHooks,
    Runner,
    function_tool,
    set_tracing_disabled,
)
from agents.agent import StopAtTools
from agents.extensions.models.litellm_model import LitellmModel
from pydantic import BaseModel

set_tracing_disabled(True)  # traces upload to OpenAI by default, which needs an OpenAI key

MODEL = LitellmModel(model="vertex_ai/gemini-3.5-flash-lite", api_key="unused")
SETTINGS = ModelSettings(tool_choice="required", extra_args={"vertex_location": "global"})


class Finding(BaseModel):
    task_id: str
    summary: str


class Recorder(RunHooks):
    """One instance shared by every run, like the real per-request hooks."""

    def __init__(self):
        self.t0 = time.monotonic()
        self.calls = []

    async def on_tool_end(self, context, agent, tool, result):
        self.calls += [{
            "agent": agent.name,
            "name": tool.name,
            "t": round(time.monotonic() - self.t0, 1),
        }]


@function_tool
async def lookup(topic: str) -> str:
    """Look up a fact.

    Args:
        topic: What to look up.
    """
    await asyncio.sleep(1)  # stand-in for an API call
    return json.dumps({"topic": topic, "fact": f"{topic} is a placeholder fact."})


@function_tool(strict_mode=False)
def submit_finding(finding: Finding) -> str:
    """Submit the final finding. Always the last call.

    Args:
        finding: The result of the research task.
    """
    return finding.model_dump_json()


researcher = Agent(
    name="Researcher",
    instructions="Call lookup once for the task topic, then call submit_finding with task_id and a one-sentence summary.",
    model=MODEL,
    model_settings=SETTINGS,
    tools=[lookup, submit_finding],
    tool_use_behavior=StopAtTools(stop_at_tool_names=["submit_finding"]),
    reset_tool_choice=False,
)

HOOKS = Recorder()


@function_tool
async def dispatch(topics: list[str]) -> str:
    """Research several topics in parallel, each in a fresh context.

    Args:
        topics: Topics to research.
    """
    async def one(i: int, topic: str):
        agent = researcher.clone(name=f"Researcher R{i}")
        result = await Runner.run(agent, json.dumps({"task_id": f"R{i}", "topic": topic}), hooks=HOOKS, max_turns=4)
        return Finding.model_validate_json(result.final_output)

    findings = await asyncio.gather(*(one(i, t) for i, t in enumerate(topics, 1)))
    return json.dumps([f.model_dump() for f in findings])


@function_tool
def write_report(text: str) -> str:
    """Finish with the final report text.

    Args:
        text: The report.
    """
    return text


lead = Agent(
    name="Lead",
    instructions="Call dispatch ONCE with exactly three topics: cats, dogs, birds. Then call write_report with a one-line summary.",
    model=MODEL,
    model_settings=SETTINGS,
    tools=[dispatch, write_report],
    tool_use_behavior=StopAtTools(stop_at_tool_names=["write_report"]),
    reset_tool_choice=False,
)


async def main():
    result = await Runner.run(lead, "Research the three topics.", hooks=HOOKS, max_turns=8)
    print("final_output:", str(result.final_output)[:200])
    print("calls:")
    for c in HOOKS.calls:
        print("  ", c)
    researchers = {c["agent"] for c in HOOKS.calls if c["agent"].startswith("Researcher")}
    lookups = [c["t"] for c in HOOKS.calls if c["name"] == "lookup"]
    print("distinct researchers:", sorted(researchers))
    print("lookup finish times (parallel if close together):", lookups)
    assert len(researchers) == 3, "expected three fresh researcher runs"
    assert max(lookups) - min(lookups) < 1.5, "lookups did not overlap, so the fan-out was not parallel"
    print("SMOKE TEST PASSED")


asyncio.run(main())
