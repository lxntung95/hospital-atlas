"""Static checks on the single-page UI: pinned CDN versions, no innerHTML with data."""

import re
from pathlib import Path

HTML = (Path(__file__).parent.parent / "web" / "index.html").read_text()


def test_cdn_assets_are_pinned():
    urls = re.findall(r"https://cdn\.jsdelivr\.net/npm/([^\"']+)", HTML)
    assert any(u.startswith("leaflet@1.9.4/") for u in urls) and any(u.startswith("chart.js@4.4.3/") for u in urls)
    assert all(re.match(r"[a-z.\-]+@\d+\.\d+\.\d+/", u) for u in urls)


def test_no_inner_html_assignments():
    hits = re.findall(r".*\.innerHTML\s*=.*", HTML)
    assert len(hits) == 1 and "tpl.innerHTML = html" in hits[0]  # the sanitised markdown path only (DOMPurify output)


def test_evidence_hooks_present():
    for name in ("renderMap", "renderTables", "renderCharts", "onProgress", "timelineBox"):
        assert name in HTML
