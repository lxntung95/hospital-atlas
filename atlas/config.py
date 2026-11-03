"""One place for settings: model, budgets, dataset ids, cache TTL, per-host limits."""

import asyncio
import os
import weakref
from pathlib import Path

from agents import ModelSettings
from agents.extensions.models.litellm_model import LitellmModel

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
FALLBACK_DIR = DATA_DIR / "fallback"

# --- Model ---

MODEL_ID = os.environ.get("ATLAS_MODEL", "vertex_ai/gemini-3.5-flash-lite")
MODEL_CALLS = 4  # at most this many concurrent model calls per process (Vertex 429s otherwise)
_gates: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore]" = weakref.WeakKeyDictionary()


def _gate() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    if loop not in _gates:
        _gates[loop] = asyncio.Semaphore(MODEL_CALLS)
    return _gates[loop]


class LimitedModel(LitellmModel):
    """LitellmModel with a process-wide cap on concurrent calls."""

    async def get_response(self, *args, **kwargs):
        async with _gate():
            return await super().get_response(*args, **kwargs)


MODEL = LimitedModel(model=MODEL_ID, api_key="unused")  # api_key unused: Vertex uses gcloud credentials
# vertex_location global: Google routes each call to any region with capacity. timeout/num_retries are passed to litellm.acompletion.
SETTINGS = ModelSettings(extra_args={"vertex_location": "global", "timeout": 45, "num_retries": 2})

# --- Research budgets (seconds) and loop caps ---

MAX_GAP_ROUNDS = 2
REQUEST_S = 240
RESEARCHER_S = 60
RETRIEVER_S = 30
WRITER_RESERVE_S = 45
WRITER_S = 30  # per Writer attempt (the repair attempt gets the remainder of the reserve)

# --- Live data ---

STATE = "NY"  # the NY filter is a constant, never a tool parameter
TTL_S = 6 * 3600  # whole-NY-slice cache lifetime
HTTP_TIMEOUT_S = 20
# No custom User-Agent: data.cms.gov rejected "hospital-atlas course project" with 403, so we send httpx's default.
RETRY_DEGRADED_S = 60  # after a failed live fetch, serve the degraded copy this long before trying again
RETRY_BACKOFF_S = (0.5, 1.5, 4.0)  # three retries
HOST_CONCURRENCY = {"data.cms.gov": 4, "eutils.ncbi.nlm.nih.gov": 2}

DATA_API = "https://data.cms.gov/data-api/v1/dataset"
PROVIDER_API = "https://data.cms.gov/provider-data/api/1/datastore/query"
DATA_API_PAGE = 5000  # data-api max page size
PROVIDER_PAGE = 1500  # Provider Data max limit (1600 returns 400)

# dataset ids (see docs/PLAN 1/Overview.md section 2)
GENERAL_INFO = "xubh-q36u"
INPATIENT_BY_PROVIDER = "690ddc6c-2767-4618-b277-420ffb2bf27c"  # CY2024
INPATIENT_BY_GEOGRAPHY = "2941ab09-8cee-49d8-9703-f3c5b854e388"
HRRP = "9n3s-kdb3"
COMPLICATIONS = "ynj2-r877"
COMPLICATIONS_NATIONAL = "qqw3-t4ie"
HCAHPS = "dgck-syfz"

# --- Sessions ---

SESSIONS_DB = "conversations.db"  # in memory on Cloud Run, so it lasts as long as the instance (we run one instance)
