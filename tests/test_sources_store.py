from atlas.context import RequestContext
from atlas.sources import SourceRegistry, data_api_url, provider_url
from atlas.store import TableStore


def test_data_api_url_is_reproducible():
    url = data_api_url("690ddc6c-2767-4618-b277-420ffb2bf27c", {"Rndrng_Prvdr_State_Abrvtn": "NY", "DRG_Cd": "470"}, size=5000)
    assert url == ("https://data.cms.gov/data-api/v1/dataset/690ddc6c-2767-4618-b277-420ffb2bf27c/data"
                   "?filter[Rndrng_Prvdr_State_Abrvtn]=NY&filter[DRG_Cd]=470&size=5000")


def test_provider_url_with_in_operator():
    url = provider_url("ynj2-r877", [("state", "=", "NY"), ("measure_id", "IN", ["MORT_30_HF", "MORT_30_PN"])], limit=1500)
    assert "conditions[1][value][]=MORT_30_HF&conditions[1][value][]=MORT_30_PN&conditions[1][operator]=IN" in url
    assert url.endswith("limit=1500&count=true")


def test_registry_dedupes_and_numbers():
    reg = SourceRegistry()
    a = reg.add("Inpatient", "ds1", "CY2024", "2026-11-03", "http://x/1")
    b = reg.add("Inpatient", "ds1", "CY2024", "2026-11-03", "http://x/1")
    c = reg.add("HRRP", "ds2", "2021-2024", "2026-11-03", "http://x/2", note="fallback")
    assert a.id == b.id == "S1" and c.id == "S2" and c.note == "fallback"
    assert [s.id for s in reg.all()] == ["S1", "S2"] and reg.get("S9") is None


def test_table_store_handles():
    store = TableStore()
    t = store.add("rows", [{"x": i} for i in range(10)], source_id="S1")
    assert t.id == "T1" and t.columns == ["x"]
    assert store.get("T1") is t


def test_table_store_unknown_handle_message():
    store = TableStore()
    store.add("a", [])
    try:
        store.get("T9")
    except KeyError as e:
        assert "T1" in str(e)
    else:
        raise AssertionError("expected KeyError")


def test_context_budget():
    ctx = RequestContext(budget_s=240)
    assert 239 < ctx.remaining() <= 240 and ctx.rounds_used == 0
