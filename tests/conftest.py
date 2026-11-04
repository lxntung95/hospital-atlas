import json

import httpx
import pytest
from agents.tool_context import ToolContext

from atlas import config, orchestrator, tools
from atlas.context import RequestContext
from atlas.http import CmsClient
from atlas.schemas import ResearchTask


async def _noop(_s):
    return None


@pytest.fixture
def ctx():
    """A request context whose CMS client is forced offline, so tools read the shipped data/fallback snapshot."""
    client = CmsClient(transport=httpx.MockTransport(lambda req: httpx.Response(503)), sleep=_noop)
    return RequestContext(client=client)


@pytest.fixture
def sessions_db(monkeypatch, tmp_path):
    """A throwaway conversation database, so tests never share Lead sessions."""
    monkeypatch.setattr(config, "SESSIONS_DB", str(tmp_path / "s.db"))


@pytest.fixture
def stub_runner(monkeypatch):
    """stub_runner(fn) replaces Runner.run (the only place the agents call a model) with fn for this test."""
    return lambda fn: monkeypatch.setattr(orchestrator.Runner, "run", fn)


async def call(tool, ctx, **kwargs):
    """Invoke a @function_tool the way the SDK does and return its (string) result."""
    args = json.dumps(kwargs)
    tc = ToolContext(context=ctx, tool_name=tool.name, tool_call_id="t1", tool_arguments=args)
    return await tool.on_invoke_tool(tc, args)


async def j(tool, ctx, **kwargs):
    return json.loads(await call(tool, ctx, **kwargs))


async def bronx(ctx):
    """A cohort of Montefiore plus the Bronx acute care hospitals; returns its handle."""
    return (await j(tools.build_cohort, ctx, ccns=["330059"], counties=["Bronx"], label="Bronx"))["cohort_handle"]


async def hf_bronx(ctx):
    """The heart-failure research a Lead would dispatch for the Bronx cohort, run through the real tools."""
    h = await bronx(ctx)
    await j(tools.get_drg_costs, ctx, cohort_handle=h, drg_codes=[291])
    await j(tools.get_cost_benchmarks, ctx, drg_codes=[291])
    await j(tools.get_readmissions, ctx, cohort_handle=h, measure_ids=["READM-30-HF-HRRP"])
    await j(tools.get_outcomes, ctx, cohort_handle=h, measure_ids=["MORT_30_HF"])
    await j(tools.get_patient_experience, ctx, cohort_handle=h)
    return h


def task(i, kind="cost"):
    return ResearchTask(id=f"R{i}", kind=kind, question="q", cohort_handle="C1", drg_codes=[291], measure_ids=[]).model_dump()


def prepare(ctx):
    ctx.cohorts["C1"] = {"ccns": ["330059"], "label": "x"}
