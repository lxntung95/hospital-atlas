"""Sources (S#): every dataset pull the report may cite, with a reproducible URL."""

from dataclasses import dataclass
from urllib.parse import quote, urlencode

from atlas.config import DATA_API, PROVIDER_API


def data_api_url(dataset_id: str, filters: dict[str, str] | None = None, size: int | None = None, offset: int | None = None) -> str:
    """Reproducible data-api URL (unencoded brackets so it can be pasted into a browser or curl -g)."""
    parts = [f"filter[{k}]={quote(str(v))}" for k, v in (filters or {}).items()]
    if size is not None:
        parts.append(f"size={size}")
    if offset:
        parts.append(f"offset={offset}")
    return f"{DATA_API}/{dataset_id}/data" + ("?" + "&".join(parts) if parts else "")


def provider_url(dataset_id: str, conditions: list[tuple[str, str, str | list[str]]] | None = None, limit: int | None = None, offset: int | None = None) -> str:
    """Reproducible Provider Data URL. conditions: [(property, operator, value or list)]."""
    parts = []
    for i, (prop, op, value) in enumerate(conditions or []):
        parts.append(f"conditions[{i}][property]={prop}")
        for v in value if isinstance(value, list) else [value]:
            parts.append(f"conditions[{i}][value]{'[]' if isinstance(value, list) else ''}={quote(str(v))}")
        parts.append(f"conditions[{i}][operator]={quote(op)}")
    if limit is not None:
        parts.append(f"limit={limit}")
    if offset:
        parts.append(f"offset={offset}")
    parts.append("count=true")
    return f"{PROVIDER_API}/{dataset_id}/0?" + "&".join(parts)


@dataclass
class Source:
    id: str
    dataset: str
    dataset_id: str
    period: str
    retrieved_at: str
    url: str
    note: str = ""  # e.g. "served from shipped fallback snapshot built <date>"


class SourceRegistry:
    """Hands out S1, S2, ... and reuses an id when the same dataset and URL is added again."""

    def __init__(self):
        self._sources: dict[str, Source] = {}
        self._by_key: dict[tuple[str, str], str] = {}

    def add(self, dataset: str, dataset_id: str, period: str, retrieved_at: str, url: str, note: str = "") -> Source:
        key = (dataset_id, url)
        if key in self._by_key:
            return self._sources[self._by_key[key]]
        src = Source(f"S{len(self._sources) + 1}", dataset, dataset_id, period, retrieved_at, url, note)
        self._sources[src.id] = src
        self._by_key[key] = src.id
        return src

    def get(self, source_id: str) -> Source | None:
        return self._sources.get(source_id)

    def all(self) -> list[Source]:
        return list(self._sources.values())
