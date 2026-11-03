import httpx
import pytest
from agents.tool_context import ToolContext

from atlas.context import RequestContext
from atlas.http import CmsClient


async def _noop(_s):
    return None


@pytest.fixture
def ctx():
    """A request context whose CMS client is forced offline, so tools read the shipped data/fallback snapshot."""
    client = CmsClient(transport=httpx.MockTransport(lambda req: httpx.Response(503)), sleep=_noop)
    return RequestContext(client=client)


async def call(tool, ctx, **kwargs):
    """Invoke a @function_tool the way the SDK does and return its (string) result."""
    import json
    args = json.dumps(kwargs)
    tc = ToolContext(context=ctx, tool_name=tool.name, tool_call_id="t1", tool_arguments=args)
    return await tool.on_invoke_tool(tc, args)
