"""Pure lookups over the shipped reference data (data/*.json) and the cached hospital list.

No network, no model. These are the deterministic hints the Lead and the Cohort Retriever lean on:
which condition, region and hospitals a message mentions, and which DRGs and quality measures belong to a condition.
"""

import difflib
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache

from atlas.config import DATA_DIR

STOPWORDS = {"hospital", "hospitals", "medical", "center", "centre", "health", "system", "the", "of", "at", "and", "campus", "inc", "in", "for", "a"}
TOKEN_ALIASES = {"nyp": "presbyterian", "presby": "presbyterian", "mt": "mount", "st": "saint", "stlukes": "luke"}

OTHER_STATES = [
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey", "new mexico", "north carolina",
    "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota", "tennessee",
    "texas", "utah", "vermont", "virginia", "west virginia", "wisconsin", "wyoming",  # washington and delaware are NY counties
]
OUT_OF_SCOPE_NAMES = [
    "mass general", "massachusetts general", "brigham", "cleveland clinic", "mayo clinic", "johns hopkins", "cedars-sinai", "cedars sinai",
    "ucla", "ucsf", "stanford", "md anderson", "boston", "chicago", "los angeles", "philadelphia", "houston", "miami", "seattle", "atlanta",
]


@lru_cache
def _load(name: str):
    return json.loads((DATA_DIR / name).read_text())


def crosswalk() -> dict:
    return _load("crosswalk.json")


def measures() -> dict:
    return _load("measures.json")


def regions() -> dict:
    return _load("regions.json")


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9/ ]+", " ", text.lower().replace("'", "")).strip()


def _has(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


def out_of_scope_terms(message: str) -> list[str]:
    text = _norm(message)
    return [t for t in OTHER_STATES + OUT_OF_SCOPE_NAMES if _has(text, t)]


# --- hospitals ---

@dataclass
class HospitalMatch:
    ccn: str
    name: str
    city: str
    county: str
    score: float


@dataclass
class HospitalSearch:
    matches: list[HospitalMatch]
    unresolved: str | None = None  # reason when nothing usable was found


def _tokens(text: str) -> list[str]:
    return [TOKEN_ALIASES.get(t, t) for t in _norm(text).replace("/", " ").split()]


def _token_matches(q: str, name_tokens: list[str]) -> bool:
    for t in name_tokens:
        if q == t:
            return True
    return bool(difflib.get_close_matches(q, name_tokens, n=1, cutoff=0.85))


def find_hospitals(query: str, hospitals: list, limit: int = 5) -> HospitalSearch:
    """Match a hospital name (or part of one) against NY hospitals. Out-of-state names are unresolved by design."""
    outside = out_of_scope_terms(query)
    qtokens = [t for t in _tokens(query) if t not in STOPWORDS] or _tokens(query)
    if not qtokens:
        return HospitalSearch([], "empty query")
    scored = []
    for h in hospitals:
        ntokens = _tokens(h.name)
        if all(_token_matches(q, ntokens) for q in qtokens):
            extra = len([t for t in ntokens if t not in STOPWORDS]) - len(qtokens)
            scored.append((extra, h.name, h))
    scored.sort(key=lambda s: (s[0], s[1]))
    matches = [HospitalMatch(h.ccn, h.name, h.city, h.county, round(1 / (1 + max(extra, 0)), 2)) for extra, _, h in scored[:limit]]
    if matches:
        return HospitalSearch(matches)
    if outside:
        return HospitalSearch([], f"outside NY scope ({outside[0]})")
    return HospitalSearch([], "no NY hospital matched that name")


# --- services (conditions, DRGs, measures) ---

@dataclass
class ServiceMatch:
    condition: str | None
    label: str
    drgs: list[int]
    hrrp_measure: str | None = None
    mort_measure: str | None = None
    comp_measure: str | None = None
    psi: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def measures(self) -> list[str]:
        return [m for m in (self.hrrp_measure, self.mort_measure, self.comp_measure, *self.psi) if m]


def _service(key: str) -> ServiceMatch:
    c = crosswalk()[key]
    return ServiceMatch(key, c["label"], list(c["drgs"]), c["hrrp_measure"], c["mort_measure"], c["comp_measure"], list(c["psi"]), c["notes"])


def find_condition(text: str) -> str | None:
    """Longest alias that appears in the text, or None."""
    norm = _norm(text)
    best, best_len = None, 0
    for key, c in crosswalk().items():
        for alias in c["aliases"] + [c["label"].lower()]:
            if _has(norm, _norm(alias)) and len(alias) > best_len:
                best, best_len = key, len(alias)
    return best


def find_services(query: str, drg_catalog: dict[int, str] | None = None, limit: int = 5) -> list[ServiceMatch]:
    """Condition -> DRGs + quality measure ids. Also accepts DRG numbers and (if given) fuzzy DRG descriptions."""
    found: dict[str, ServiceMatch] = {}
    cond = find_condition(query)
    if cond:
        found[cond] = _service(cond)
    else:  # whole-query fuzzy match against aliases
        names = {a: k for k, c in crosswalk().items() for a in c["aliases"] + [c["label"].lower()]}
        close = difflib.get_close_matches(_norm(query), list(names), n=1, cutoff=0.85)
        if close:
            found[names[close[0]]] = _service(names[close[0]])
    for code in {int(n) for n in re.findall(r"\b(\d{2,3})\b", query)}:
        owner = next((k for k, c in crosswalk().items() if code in c["drgs"]), None)
        if owner:
            found.setdefault(owner, _service(owner))
        elif drg_catalog and code in drg_catalog:
            found[f"drg_{code}"] = ServiceMatch(None, f"DRG {code}: {drg_catalog[code].title()}", [code])
    if not found and drg_catalog:
        qt = [t for t in _tokens(query) if t not in STOPWORDS and len(t) > 3]
        if qt:
            for code, desc in sorted(drg_catalog.items()):
                if all(t in _norm(desc) for t in qt):
                    found[f"drg_{code}"] = ServiceMatch(None, f"DRG {code}: {desc.title()}", [code])
    return list(found.values())[:limit]


# --- region and the overall read of a message ---

def find_region(text: str) -> tuple[str | None, list[str]]:
    """(region name, counties) for a region or county mentioned in the text."""
    norm = _norm(text)
    reg = regions()
    for borough, county in sorted(reg["boroughs"].items(), key=lambda kv: -len(kv[0])):
        if _has(norm, borough):
            return "New York City", [county]
    for alias, name in sorted(reg["aliases"].items(), key=lambda kv: -len(kv[0])):
        if _has(norm, alias):
            return name, reg["regions"][name]
    for name, counties in reg["regions"].items():
        if _has(norm, _norm(name)):
            return name, counties
        for county in counties:
            if county not in ("New York",) and _has(norm, _norm(county) + " county"):
                return name, [county]
    return None, []


def _place_words() -> set[str]:
    reg = regions()
    names = set(reg["aliases"]) | set(reg["boroughs"]) | {_norm(r) for r in reg["regions"]} | {"ny", "nyc", "new york", "new york state"}
    names |= {_norm(c) for cs in reg["regions"].values() for c in cs}
    return names


@dataclass
class Detected:
    condition: str | None
    region: str | None
    counties: list[str]
    drgs: list[int]
    hospital_hints: list[str]
    out_of_scope: list[str]
    vague: bool


def detect(message: str, hospitals: list | None = None) -> Detected:
    """A deterministic first read of the user's message (hints for the Lead; never a substitute for its judgment)."""
    cond = find_condition(message)
    region, counties = find_region(message)
    drgs = sorted({int(n) for n in re.findall(r"\bdrg\s*#?\s*(\d{2,3})\b", message.lower())})
    hints: list[str] = []
    if hospitals:
        place_words = _place_words()
        for phrase in re.findall(r"(?:[A-Z][\w'’./-]*)(?:\s+(?:of\s+|at\s+)?[A-Z][\w'’./-]*)*", message):
            words = phrase.split()
            for i in range(len(words)):  # drop leading words like "Compare" or "Which"
                sub = " ".join(words[i:])
                if _norm(sub) in place_words:
                    continue
                res = find_hospitals(sub, hospitals, limit=1)
                if res.matches:
                    if res.matches[0].name not in hints:
                        hints.append(res.matches[0].name)
                    break
    outside = out_of_scope_terms(message)
    vague = not (cond or drgs or hints or outside)
    return Detected(cond, region, counties, drgs, hints, outside, vague)
