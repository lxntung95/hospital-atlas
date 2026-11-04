"""Async access to the CMS APIs: paging, retries, a whole-slice TTL cache, single-flight, stale-while-error,
and a last-resort fallback to the snapshot shipped in data/fallback (always disclosed through `served_from`)."""

import asyncio
import gzip
import json
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

from atlas import config
from atlas.sources import data_api_url, provider_url


class DataUnavailable(Exception):
    """Live fetch failed and there is neither a cached copy nor a shipped fallback."""


@dataclass(frozen=True)
class SliceSpec:
    """One cacheable slice of a CMS dataset. NY filters are part of the spec, never a caller argument."""

    name: str
    kind: str  # "data_api" or "provider"
    dataset_id: str
    filters: tuple = ()  # data_api: ((field, value), ...)
    conditions: tuple = ()  # provider: ((property, operator, value or list), ...)
    columns: tuple | None = None  # keep only these columns (smaller memory and fallback files)

    @property
    def url(self) -> str:
        if self.kind == "data_api":
            return data_api_url(self.dataset_id, dict(self.filters))
        return provider_url(self.dataset_id, list(self.conditions))


@dataclass
class Fetched:
    rows: list
    fetched_at: float  # epoch seconds
    served_from: str  # live | cache | stale | fallback
    url: str
    built_at: str | None = None  # fallback snapshots only
    checked_at: float = 0.0  # last live attempt; degraded copies are not re-tried for RETRY_DEGRADED_S

    @property
    def retrieved(self) -> str:
        return datetime.fromtimestamp(self.fetched_at, timezone.utc).strftime("%Y-%m-%d")

    @property
    def note(self) -> str:
        if self.served_from == "fallback":
            return f"live CMS API unavailable; served from the shipped snapshot built {self.built_at}"
        if self.served_from == "stale":
            return "live CMS API unavailable; served from an earlier cached copy"
        return ""


def _trim(rows: list[dict], columns: tuple | None) -> list[dict]:
    return rows if not columns else [{c: r.get(c) for c in columns} for r in rows]


def fallback_path(name: str, directory: Path | None = None) -> Path:
    return (directory or config.FALLBACK_DIR) / f"{name}.json.gz"


def save_fallback(spec: SliceSpec, rows: list[dict], directory: Path | None = None) -> Path:
    path = fallback_path(spec.name, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"built_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "url": spec.url, "rows": _trim(rows, spec.columns)}
    with gzip.open(path, "wt", encoding="utf-8", compresslevel=9) as f:
        json.dump(payload, f, separators=(",", ":"))
    return path


def load_fallback(name: str, directory: Path | None = None) -> dict | None:
    path = fallback_path(name, directory)
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


class CmsClient:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None, ttl: float = config.TTL_S,
                 fallback_dir: Path | None = None, sleep=asyncio.sleep, clock=time.time, backoff=config.RETRY_BACKOFF_S):
        self._transport = transport
        self._http: httpx.AsyncClient | None = None
        self.ttl = ttl
        self.fallback_dir = fallback_dir
        self._sleep = sleep
        self._clock = clock
        self._backoff = backoff
        self._cache: dict[str, Fetched] = {}
        self._inflight: dict[str, asyncio.Task] = {}
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self.live_calls = 0  # test visibility

    # --- public ---

    async def get_slice(self, spec: SliceSpec) -> Fetched:
        cached = self._cache.get(spec.name)
        if cached:
            now = self._clock()
            if cached.served_from in ("live", "cache") and now - cached.fetched_at < self.ttl:
                return replace(cached, served_from="cache")
            if cached.served_from in ("stale", "fallback") and now - cached.checked_at < config.RETRY_DEGRADED_S:
                return cached  # live source just failed; do not make every caller wait through retries again
        task = self._inflight.get(spec.name)
        if task is None:  # single-flight: concurrent callers share one fetch
            task = asyncio.ensure_future(self._load(spec))
            self._inflight[spec.name] = task
            task.add_done_callback(lambda _t, n=spec.name: self._inflight.pop(n, None))
        return await asyncio.shield(task)

    def status(self) -> dict:
        now = self._clock()
        return {n: {"rows": len(f.rows), "age_s": round(now - f.fetched_at), "served_from": f.served_from} for n, f in self._cache.items()}

    async def aclose(self):
        if self._http:
            await self._http.aclose()
            self._http = None

    # --- internals ---

    async def _load(self, spec: SliceSpec) -> Fetched:
        try:
            rows = await (self._fetch_data_api(spec) if spec.kind == "data_api" else self._fetch_provider(spec))
            fetched = Fetched(_trim(rows, spec.columns), self._clock(), "live", spec.url)
        except Exception as exc:
            stale = self._cache.get(spec.name)
            if stale:  # stale-while-error
                fetched = replace(stale, served_from="stale")
            else:
                snap = load_fallback(spec.name, self.fallback_dir)
                if snap is None:
                    raise DataUnavailable(f"{spec.name}: live fetch failed ({type(exc).__name__}: {exc}) and no fallback is shipped") from exc
                fetched = Fetched(snap["rows"], self._clock(), "fallback", spec.url, snap.get("built_at"))
        fetched.checked_at = self._clock()
        self._cache[spec.name] = fetched
        return fetched

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(transport=self._transport, timeout=config.HTTP_TIMEOUT_S)
        return self._http

    def _semaphore(self, url: str) -> asyncio.Semaphore:
        host = urlparse(url).hostname or ""
        if host not in self._semaphores:
            self._semaphores[host] = asyncio.Semaphore(config.HOST_CONCURRENCY.get(host, 4))
        return self._semaphores[host]

    async def _get_json(self, url: str, params: list[tuple[str, str]]):
        last: Exception | None = None
        for attempt in range(len(self._backoff) + 1):
            try:
                async with self._semaphore(url):
                    resp = await self._client().get(url, params=params)
                self.live_calls += 1
                if resp.status_code == 429 or resp.status_code >= 500:
                    last = httpx.HTTPStatusError(f"HTTP {resp.status_code}", request=resp.request, response=resp)
                elif resp.status_code >= 400:
                    raise DataUnavailable(f"HTTP {resp.status_code} from {url}: {resp.text[:200]}")
                else:
                    return resp.json()
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last = exc
            if attempt < len(self._backoff):
                await self._sleep(self._backoff[attempt])
        raise last or DataUnavailable(url)

    async def _fetch_data_api(self, spec: SliceSpec) -> list[dict]:
        url = f"{config.DATA_API}/{spec.dataset_id}/data"
        rows, offset = [], 0
        while True:
            params = [(f"filter[{k}]", v) for k, v in spec.filters] + [("size", str(config.DATA_API_PAGE)), ("offset", str(offset))]
            page = await self._get_json(url, params)
            rows += page
            if len(page) < config.DATA_API_PAGE:
                return rows
            offset += config.DATA_API_PAGE

    async def _fetch_provider(self, spec: SliceSpec) -> list[dict]:
        url = f"{config.PROVIDER_API}/{spec.dataset_id}/0"
        rows, offset = [], 0
        while True:
            params = [("limit", str(config.PROVIDER_PAGE)), ("offset", str(offset)), ("count", "true")]
            for i, (prop, op, value) in enumerate(spec.conditions):
                params += [(f"conditions[{i}][property]", prop), (f"conditions[{i}][operator]", op)]
                if isinstance(value, (list, tuple)):
                    params += [(f"conditions[{i}][value][]", v) for v in value]
                else:
                    params.append((f"conditions[{i}][value]", value))
            page = await self._get_json(url, params)
            batch = page["results"]
            rows += batch
            offset += len(batch)
            if not batch or offset >= int(page.get("count", offset)):
                return rows


_default: CmsClient | None = None


def get_client() -> CmsClient:
    global _default
    if _default is None:
        _default = CmsClient()
    return _default
