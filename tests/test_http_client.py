"""Offline tests for atlas/http.py using httpx.MockTransport (no network)."""

import asyncio

import httpx
import pytest

from atlas import config
from atlas.http import CmsClient, DataUnavailable, SliceSpec, save_fallback

DATA_SPEC = SliceSpec("t_data", "data_api", "abc", filters=(("State", "NY"),), columns=("a",))
PROV_SPEC = SliceSpec("t_prov", "provider", "xyz-1234", conditions=(("state", "=", "NY"),))


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make(handler, tmp_path, **kw):
    sleeps = []

    async def fake_sleep(s):
        sleeps.append(s)

    client = CmsClient(transport=httpx.MockTransport(handler), fallback_dir=tmp_path, sleep=fake_sleep, **kw)
    client.sleeps = sleeps
    return client


async def test_data_api_pages_until_short_page(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_API_PAGE", 3)
    offsets = []

    def handler(req):
        off = int(req.url.params["offset"])
        offsets.append(off)
        assert req.url.params["filter[State]"] == "NY"
        return httpx.Response(200, json=[{"a": i, "b": 0} for i in range(off, min(off + 3, 7))])

    f = await make(handler, tmp_path).get_slice(DATA_SPEC)
    assert offsets == [0, 3, 6]
    assert [r["a"] for r in f.rows] == list(range(7))
    assert f.rows[0] == {"a": 0}  # columns trimmed
    assert f.served_from == "live"


async def test_provider_pages_by_count(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROVIDER_PAGE", 2)
    calls = []

    def handler(req):
        off = int(req.url.params["offset"])
        calls.append((int(req.url.params["limit"]), off))
        assert req.url.params["conditions[0][value]"] == "NY"
        return httpx.Response(200, json={"results": [{"i": i} for i in range(off, min(off + 2, 5))], "count": 5})

    f = await make(handler, tmp_path).get_slice(PROV_SPEC)
    assert len(f.rows) == 5 and calls == [(2, 0), (2, 2), (2, 4)]


async def test_provider_in_operator_sends_repeated_values(tmp_path):
    seen = {}

    def handler(req):
        seen["q"] = req.url.query.decode()
        return httpx.Response(200, json={"results": [], "count": 0})

    spec = SliceSpec("t_in", "provider", "xyz-1234", conditions=(("measure_id", "IN", ["A", "B"]),))
    await make(handler, tmp_path).get_slice(spec)
    assert seen["q"].count("conditions%5B0%5D%5Bvalue%5D%5B%5D=") == 2


async def test_retries_then_succeeds(tmp_path):
    n = {"calls": 0}

    def handler(req):
        n["calls"] += 1
        return httpx.Response(503) if n["calls"] < 3 else httpx.Response(200, json=[{"a": 1}])

    client = make(handler, tmp_path)
    f = await client.get_slice(DATA_SPEC)
    assert f.rows == [{"a": 1}] and n["calls"] == 3
    assert client.sleeps == [0.5, 1.5]


async def test_client_error_is_not_retried(tmp_path):
    n = {"calls": 0}

    def handler(req):
        n["calls"] += 1
        return httpx.Response(400, text="bad")

    with pytest.raises(DataUnavailable):
        await make(handler, tmp_path).get_slice(DATA_SPEC)
    assert n["calls"] == 1


async def test_single_flight(tmp_path):
    gate = asyncio.Event()

    async def slow(req):
        await gate.wait()
        return httpx.Response(200, json=[{"a": 1}])

    client = CmsClient(transport=httpx.MockTransport(slow), fallback_dir=tmp_path)
    tasks = [asyncio.create_task(client.get_slice(DATA_SPEC)) for _ in range(10)]
    await asyncio.sleep(0.05)
    gate.set()
    results = await asyncio.gather(*tasks)
    assert client.live_calls == 1
    assert all(r.rows == [{"a": 1}] for r in results)


async def test_ttl_cache(tmp_path):
    clock = Clock()
    client = make(lambda req: httpx.Response(200, json=[{"a": 1}]), tmp_path, clock=clock, ttl=100)
    assert (await client.get_slice(DATA_SPEC)).served_from == "live"
    clock.now += 50
    assert (await client.get_slice(DATA_SPEC)).served_from == "cache"
    assert client.live_calls == 1
    clock.now += 100
    assert (await client.get_slice(DATA_SPEC)).served_from == "live"
    assert client.live_calls == 2


async def test_stale_while_error(tmp_path):
    clock = Clock()
    state = {"ok": True}

    def handler(req):
        return httpx.Response(200, json=[{"a": 1}]) if state["ok"] else httpx.Response(500)

    client = make(handler, tmp_path, clock=clock, ttl=100)
    await client.get_slice(DATA_SPEC)
    state["ok"] = False
    clock.now += 200
    f = await client.get_slice(DATA_SPEC)
    assert f.served_from == "stale" and f.rows == [{"a": 1}]
    assert "earlier cached copy" in f.note


async def test_degraded_copy_not_retried_immediately(tmp_path):
    clock = Clock()
    client = make(lambda req: httpx.Response(500), tmp_path, clock=clock)
    save_fallback(DATA_SPEC, [{"a": 9}], tmp_path)
    await client.get_slice(DATA_SPEC)
    calls = client.live_calls
    clock.now += 5
    await client.get_slice(DATA_SPEC)
    assert client.live_calls == calls  # within RETRY_DEGRADED_S: no new attempt
    clock.now += config.RETRY_DEGRADED_S
    await client.get_slice(DATA_SPEC)
    assert client.live_calls > calls


async def test_fallback_when_live_fails_and_disclosed(tmp_path):
    save_fallback(DATA_SPEC, [{"a": 7, "b": 1}], tmp_path)
    f = await make(lambda req: httpx.Response(500), tmp_path).get_slice(DATA_SPEC)
    assert f.rows == [{"a": 7}] and f.served_from == "fallback" and f.built_at
    assert "shipped snapshot" in f.note


async def test_unavailable_without_fallback(tmp_path):
    with pytest.raises(DataUnavailable):
        await make(lambda req: httpx.Response(500), tmp_path).get_slice(DATA_SPEC)
