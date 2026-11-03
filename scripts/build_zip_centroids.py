"""Build data/ny_zip_centroids.json: {zip5: [lat, lon]} for the ZIPs of NY hospitals, from the Census 2023 ZCTA gazetteer
(public domain). The download is read in memory (never extracted or executed).

Run: uv run python scripts/build_zip_centroids.py
"""

import asyncio
import csv
import io
import json
import sys
import zipfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from atlas import cms  # noqa: E402

URL = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_Gaz_zcta_national.zip"


async def main():
    hospitals = (await cms.general_info_ny()).rows
    wanted = {h.zip[:5] for h in hospitals if h.zip}
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        r = await client.get(URL)
        r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        name = next(n for n in z.namelist() if n.endswith(".txt"))
        text = z.read(name).decode("utf-8")
    reader = csv.reader(io.StringIO(text), delimiter="\t")
    header = [h.strip() for h in next(reader)]
    i_zip, i_lat, i_lon = header.index("GEOID"), header.index("INTPTLAT"), header.index("INTPTLONG")
    out = {}
    for row in reader:
        z = row[i_zip].strip()
        if z in wanted:
            out[z] = [round(float(row[i_lat]), 4), round(float(row[i_lon]), 4)]
    missing = sorted(wanted - set(out))
    (ROOT / "data" / "ny_zip_centroids.json").write_text(json.dumps(out, separators=(",", ":"), sort_keys=True))
    print(f"{len(out)} of {len(wanted)} hospital ZIPs; missing: {missing}")


if __name__ == "__main__":
    asyncio.run(main())
