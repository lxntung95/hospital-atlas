"""Sources (S#): every dataset pull the report may cite, with a reproducible URL."""

from dataclasses import dataclass
from urllib.parse import quote

from atlas.config import DATA_API, PROVIDER_API


def data_api_params(filters: dict[str, str] | None = None) -> list[tuple[str, str]]:
    return [(f"filter[{k}]", str(v)) for k, v in (filters or {}).items()]


def provider_params(conditions: list[tuple[str, str, str | list[str]]] | None = None) -> list[tuple[str, str]]:
    """Provider Data query pairs. conditions: [(property, operator, value or list of values)]."""
    out = []
    for i, (prop, op, value) in enumerate(conditions or []):
        out.append((f"conditions[{i}][property]", prop))
        out += [(f"conditions[{i}][value][]", v) for v in value] if isinstance(value, (list, tuple)) else [(f"conditions[{i}][value]", value)]
        out.append((f"conditions[{i}][operator]", op))
    return out


def _url(base: str, pairs: list[tuple[str, str]]) -> str:
    """Reproducible URL with unencoded brackets so it can be pasted into a browser or curl -g."""
    return base + ("?" + "&".join(f"{k}={quote(str(v))}" for k, v in pairs) if pairs else "")


def data_api_url(dataset_id: str, filters: dict[str, str] | None = None) -> str:
    return _url(f"{DATA_API}/{dataset_id}/data", data_api_params(filters))


def provider_url(dataset_id: str, conditions: list[tuple[str, str, str | list[str]]] | None = None) -> str:
    return _url(f"{PROVIDER_API}/{dataset_id}/0", provider_params(conditions) + [("count", "true")])


def sid_key(source_id: str) -> int:
    """Sort key for S# ids (S2 before S10)."""
    return int(source_id[1:])


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
