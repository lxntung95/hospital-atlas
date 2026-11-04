"""Recompute the README's expected answers (Q1-Q3) straight from the CMS endpoints, with plain code that shares nothing
with the agent (no atlas imports). Prints values with the exact endpoint URLs and today's date.

    uv run python scripts/expected_answers.py
"""

import datetime as dt
import json
from urllib.parse import urlencode

import httpx

DATA = "https://data.cms.gov/data-api/v1/dataset"
PROV = "https://data.cms.gov/provider-data/api/1/datastore/query"
BY_PROVIDER, BY_GEO = "690ddc6c-2767-4618-b277-420ffb2bf27c", "2941ab09-8cee-49d8-9703-f3c5b854e388"
GENERAL, HRRP, COMP, NATIONAL = "xubh-q36u", "9n3s-kdb3", "ynj2-r877", "qqw3-t4ie"
NYC = {"BRONX", "KINGS", "NEW YORK", "QUEENS", "RICHMOND"}
client = httpx.Client(timeout=60, follow_redirects=True)
urls: list[str] = []


def data_api(dataset: str, **flt) -> list[dict]:
    url = f"{DATA}/{dataset}/data?" + "&".join(f"filter[{k}]={v}" for k, v in flt.items())
    urls.append(url)
    out, off = [], 0
    while True:
        rows = client.get(url + f"&size=5000&offset={off}").json()
        out += rows
        if len(rows) < 5000:
            return out
        off += 5000


def provider(dataset: str, conds: list[tuple[str, str, str]]) -> list[dict]:
    params = []
    for i, (p, op, v) in enumerate(conds):
        params += [(f"conditions[{i}][property]", p), (f"conditions[{i}][value]", v), (f"conditions[{i}][operator]", op)]
    urls.append(f"{PROV}/{dataset}/0?" + urlencode(params) + "&count=true")
    out, off = [], 0
    while True:
        rows = client.get(f"{PROV}/{dataset}/0?" + urlencode(params) + f"&limit=1500&offset={off}").json()["results"]
        out += rows
        if len(rows) < 1500:
            return out
        off += 1500


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def money(x):
    return f"${x:,.0f}"


def drg_rows(drg: int) -> list[dict]:
    rows = [r for r in data_api(BY_PROVIDER, Rndrng_Prvdr_State_Abrvtn="NY", DRG_Cd=drg) if f(r["Avg_Tot_Pymt_Amt"]) is not None]
    return sorted(rows, key=lambda r: -f(r["Avg_Tot_Pymt_Amt"]))


def benchmarks(drg: int) -> dict:
    out = {}
    for r in data_api(BY_GEO, DRG_Cd=drg):
        if r["Rndrng_Prvdr_Geo_Lvl"] == "National" or r["Rndrng_Prvdr_Geo_Desc"] == "New York":
            out[r["Rndrng_Prvdr_Geo_Lvl"]] = f(r["Avg_Tot_Pymt_Amt"])
    return out


def ny(dataset: str, extra=()):
    return provider(dataset, [("state", "=", "NY"), *extra])


def q1():
    print("\n=== Q1: DRG 470, top five NY hospitals by average total Medicare payment ===")
    rows = drg_rows(470)
    for i, r in enumerate(rows[:5], 1):
        n = int(r["Tot_Dschrgs"])
        print(f"{i}. {r['Rndrng_Prvdr_Org_Name']} {r['Rndrng_Prvdr_CCN']}: {money(f(r['Avg_Tot_Pymt_Amt']))}, {n} discharges{'  (low volume, <20)' if n < 20 else ''}")
    b = benchmarks(470)
    print(f"Benchmarks: NY {money(b['State'])}, national {money(b['National'])}. {len(rows)} NY hospitals have data.")


def bronx_ccns() -> dict:
    return {r["facility_id"]: r["facility_name"] for r in ny(GENERAL) if r["countyparish"].upper() == "BRONX" and r["hospital_type"] == "Acute Care Hospitals"}


def q2():
    print("\n=== Q2: Bronx heart failure (DRG 291, sibling 292), readmissions and mortality ===")
    bronx = bronx_ccns()
    hrrp = {r["facility_id"]: r for r in ny(HRRP, [("measure_name", "=", "READM-30-HF-HRRP")])}
    mort = {r["facility_id"]: r for r in ny(COMP, [("measure_id", "=", "MORT_30_HF")])}
    nat = {r["measure_id"]: r for r in provider(NATIONAL, [])}
    for drg in (291, 292):
        by = {r["Rndrng_Prvdr_CCN"]: r for r in drg_rows(drg)}
        print(f"\nDRG {drg}")
        print("| Hospital | Avg total payment | Discharges | HF ERR | MORT_30_HF (denominator) |")
        for ccn in sorted(bronx, key=lambda c: f(by[c]["Avg_Tot_Pymt_Amt"]) if c in by else 1e9):
            p, h, m = by.get(ccn), hrrp.get(ccn), mort.get(ccn)
            print(f"| {bronx[ccn]} {ccn} | {money(f(p['Avg_Tot_Pymt_Amt'])) if p else 'n/a'} | {p['Tot_Dschrgs'] if p else 'n/a'} | "
                  f"{h['excess_readmission_ratio'] if h else 'n/a'} | {(m['score'] + ' (n=' + str(m['denominator']) + ')') if m else 'n/a'} |")
        b = benchmarks(drg)
        print(f"Benchmarks DRG {drg}: NY {money(b['State']) if b.get('State') else 'n/a'}, national {money(b['National']) if b.get('National') else 'n/a'}")
    print(f"National MORT_30_HF rate: {nat['MORT_30_HF']['national_rate']}")
    print("DRG 293 rows in NY:", len(data_api(BY_PROVIDER, Rndrng_Prvdr_State_Abrvtn="NY", DRG_Cd=293)), "(expected 0)")


def q3():
    print("\n=== Q3: hip and knee replacement in NYC, cost and quality (after clarification) ===")
    nyc = {r["facility_id"]: r for r in ny(GENERAL) if r["countyparish"].upper() in NYC and r["hospital_type"] == "Acute Care Hospitals"}
    comp = {r["facility_id"]: r for r in ny(COMP, [("measure_id", "=", "COMP_HIP_KNEE")])}
    hrrp = {r["facility_id"]: r for r in ny(HRRP, [("measure_name", "=", "READM-30-HIP-KNEE-HRRP")])}
    nat = {r["measure_id"]: r for r in provider(NATIONAL, [])}
    print(f"{len(nyc)} acute-care hospitals in the five NYC counties. National COMP_HIP_KNEE rate: {nat['COMP_HIP_KNEE']['national_rate']}")
    for drg in (470, 469):
        rows = [r for r in drg_rows(drg) if r["Rndrng_Prvdr_CCN"] in nyc]
        print(f"\nDRG {drg}: {len(rows)} NYC hospitals, ranked by payment")
        print("| # | Hospital | Avg total payment | Discharges | COMP_HIP_KNEE | Hip/knee ERR |")
        for i, r in enumerate(rows[:10], 1):
            c = r["Rndrng_Prvdr_CCN"]
            print(f"| {i} | {r['Rndrng_Prvdr_Org_Name']} {c} | {money(f(r['Avg_Tot_Pymt_Amt']))} | {r['Tot_Dschrgs']} | {comp[c]['score'] if c in comp else 'n/a'} | {hrrp[c]['excess_readmission_ratio'] if c in hrrp else 'n/a'} |")


if __name__ == "__main__":
    print("Verified on", dt.date.today().isoformat())
    q1(); q2(); q3()
    print("\nEndpoints used:")
    for u in dict.fromkeys(urls):
        print(" ", u)
