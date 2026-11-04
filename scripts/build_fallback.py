"""Build the last-known-good NY snapshot shipped in data/fallback/ (used only when the live CMS APIs fail).

Run: uv run python -m scripts.build_fallback
Re-run it whenever you want a fresher snapshot, then commit data/fallback/.
"""

import asyncio
from pathlib import Path
from tempfile import mkdtemp

from atlas import cms
from atlas.config import FALLBACK_DIR
from atlas.crosswalk import crosswalk
from atlas.http import CmsClient, save_fallback


async def main():
    drgs = sorted({d for c in crosswalk().values() for d in c["drgs"]})
    specs = [*cms.NY_SLICES, *(cms.geo_spec(d) for d in drgs)]
    client = CmsClient(fallback_dir=Path(mkdtemp()))  # empty dir: if live fails we want the error, not a stale snapshot
    total = 0
    for spec in specs:
        fetched = await client.get_slice(spec)
        path = save_fallback(spec, fetched.rows, FALLBACK_DIR)
        total += path.stat().st_size
        print(f"{spec.name:28} {len(fetched.rows):6} rows  {path.stat().st_size / 1024:7.1f} KB")
    print(f"total {total / 1024 / 1024:.2f} MB in {FALLBACK_DIR}")
    await client.aclose()


asyncio.run(main())
