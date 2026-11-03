"""T9: with HTTP forced to fail, the adapters serve the shipped snapshot and the Source discloses it."""

import httpx

from atlas import cms
from atlas.config import FALLBACK_DIR
from atlas.http import CmsClient
from atlas.sources import SourceRegistry


def failing_client():
    return CmsClient(transport=httpx.MockTransport(lambda req: httpx.Response(503)), sleep=lambda s: _noop())


async def _noop():
    return None


def test_fallback_files_exist_and_are_small():
    files = list(FALLBACK_DIR.glob("*.json.gz"))
    assert {"general_info", "ny_inpatient", "hrrp", "complications", "complications_national", "hcahps_star", "geo_470"} <= {f.name.removesuffix(".json.gz") for f in files}
    assert sum(f.stat().st_size for f in files) < 2 * 1024 * 1024


async def test_T9_adapters_serve_fallback_and_disclose():
    client = failing_client()
    hospitals = await cms.general_info_ny(client)
    inpatient = await cms.ny_inpatient(client)
    assert hospitals.served_from == inpatient.served_from == "fallback"
    assert len(hospitals.rows) == 192 and len(inpatient.rows) > 8000
    src = inpatient.source(SourceRegistry())
    assert "shipped snapshot built" in src.note


async def test_fallback_benchmark_drg_470():
    res = await cms.geo_benchmark(470, failing_client())
    ny = next(r for r in res.rows if r.geo == "New York")
    assert abs(ny.avg_total_payment - 23235.41) < 1.0


async def test_fallback_covers_every_crosswalk_measure():
    from atlas import crosswalk
    client = failing_client()
    hrrp = {r.measure for r in (await cms.hrrp_ny(client)).rows}
    comp = {r.measure_id for r in (await cms.complications_ny(client)).rows}
    for c in crosswalk.crosswalk().values():
        assert c["hrrp_measure"] is None or c["hrrp_measure"] in hrrp
        for m in (c["mort_measure"], c["comp_measure"], *c["psi"]):
            assert m is None or m in comp, m
