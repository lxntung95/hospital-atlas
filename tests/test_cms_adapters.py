"""Adapters normalise CMS text into typed rows. Uses a fake client, no network."""

from dataclasses import replace

from atlas import cms
from atlas.http import Fetched


class FakeClient:
    def __init__(self, rows, served_from="live"):
        self.f = Fetched(rows, 1_700_000_000.0, served_from, "http://example", "2026-11-03" if served_from == "fallback" else None)

    async def get_slice(self, spec):
        self.spec = spec
        return replace(self.f, url=spec.url)


def test_clean_and_num():
    assert cms.clean("Not Available") is None and cms.clean(" x ") == "x" and cms.clean("") is None
    assert cms.num("1,234.5") == 1234.5 and cms.num("Not Applicable") is None and cms.num("abc") is None
    assert cms.integer("12.0") == 12
    assert cms.period("04/01/2023", "03/31/2025") == "2023-04-01 to 2025-03-31" and cms.period("", "") == "unspecified"
    assert cms.drg_code(61) == "061" and cms.drg_code("470") == "470"


def test_ny_is_constant_in_every_spec():
    for spec in (cms.GENERAL_INFO, cms.INPATIENT, cms.HRRP, cms.COMPLICATIONS, cms.HCAHPS_STAR):
        assert "NY" in str(spec.filters) + str(spec.conditions)
    assert cms.geo_spec(470).filters == (("DRG_Cd", "470"),)


async def test_complications_normalises_missing_ci():
    row = {"facility_id": "330059", "facility_name": "MONTEFIORE", "measure_id": "MORT_30_HF", "measure_name": "Death rate",
           "compared_to_national": "Not Available", "denominator": "412", "score": "11.9", "lower_estimate": "Not Available",
           "higher_estimate": "Not Available", "footnote": "", "start_date": "07/01/2021", "end_date": "06/30/2024"}
    res = await cms.complications_ny(FakeClient([row]))
    r = res.rows[0]
    assert r.compared_to_national is None and r.lower is None and r.score == 11.9 and r.denominator == 412
    assert res.period == "2021-07-01 to 2024-06-30" and res.dataset_id == "ynj2-r877"


async def test_geo_benchmark_keeps_national_and_ny_only():
    def g(level, desc, pay):
        return {"Rndrng_Prvdr_Geo_Lvl": level, "Rndrng_Prvdr_Geo_Desc": desc, "DRG_Cd": "470", "DRG_Desc": "JOINT", "Tot_Dschrgs": "10",
                "Avg_Submtd_Cvrd_Chrg": "1", "Avg_Tot_Pymt_Amt": pay, "Avg_Mdcr_Pymt_Amt": "1"}
    res = await cms.geo_benchmark(470, FakeClient([g("National", "National", "17364.02"), g("State", "Alabama", "1"), g("State", "New York", "23235.41")]))
    assert [(r.level, r.geo) for r in res.rows] == [("National", "National"), ("State", "New York")]
    assert "filter[DRG_Cd]=470" in res.url


async def test_source_carries_fallback_note():
    from atlas.sources import SourceRegistry
    res = await cms.general_info_ny(FakeClient([], served_from="fallback"))
    src = res.source(SourceRegistry())
    assert src.id == "S1" and "shipped snapshot" in src.note
