"""T1/T2: our paging returns every row CMS says exists. Hits the live CMS APIs (deselect with -m 'not network')."""

import httpx
import pytest

from atlas import cms, config
from atlas.http import CmsClient

pytestmark = pytest.mark.network


async def test_T1_inpatient_ny_rows_match_stats():
    stats = httpx.get(f"{config.DATA_API}/{config.INPATIENT_BY_PROVIDER}/data/stats", params={"filter[Rndrng_Prvdr_State_Abrvtn]": "NY"}, timeout=30).json()
    f = await CmsClient(fallback_dir=None).get_slice(cms.INPATIENT)
    assert f.served_from == "live" and len(f.rows) == stats["found_rows"]


async def test_T2_complications_ny_rows_match_count():
    params = {"limit": 1, "count": "true", "conditions[0][property]": "state", "conditions[0][value]": "NY", "conditions[0][operator]": "="}
    count = httpx.get(f"{config.PROVIDER_API}/{config.COMPLICATIONS}/0", params=params, timeout=30).json()["count"]
    f = await CmsClient().get_slice(cms.COMPLICATIONS)
    assert f.served_from == "live" and len(f.rows) == int(count) > config.PROVIDER_PAGE  # forced more than one page
