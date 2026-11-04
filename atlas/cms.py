"""Typed adapters over the CMS datasets. The NY filter lives inside each SliceSpec; callers cannot change the state.

Every adapter returns a Result: typed rows plus what a Source needs (dataset, period, URL, retrieved date, fallback note).
"""

from dataclasses import dataclass

from atlas import config
from atlas.http import CmsClient, Fetched, SliceSpec, get_client
from atlas.sources import Source, SourceRegistry, data_api_url, provider_url

MISSING = {"", "Not Available", "Not Applicable", "N/A", "n/a", "NA"}


def clean(value) -> str | None:
    """CMS uses text placeholders for missing values; turn them into None."""
    if value is None:
        return None
    s = str(value).strip()
    return None if s in MISSING else s


def num(value) -> float | None:
    s = clean(value)
    if s is None:
        return None
    try:
        return float(s.replace(",", "").replace("$", ""))
    except ValueError:
        return None


def integer(value) -> int | None:
    n = num(value)
    return None if n is None else int(round(n))


def _iso(mdy: str | None) -> str | None:
    s = clean(mdy)
    if not s or s.count("/") != 2:
        return None
    m, d, y = s.split("/")
    return f"{y}-{int(m):02d}-{int(d):02d}"


def period(start, end) -> str:
    a, b = _iso(start), _iso(end)
    return f"{a} to {b}" if a and b else "unspecified"


@dataclass
class Result:
    rows: list
    dataset: str
    dataset_id: str
    period: str
    url: str
    retrieved_at: str
    served_from: str
    note: str = ""
    built_at: str | None = None

    def source(self, registry: SourceRegistry, url: str | None = None) -> Source:
        """Register this pull; pass a narrower reproducible `url` when the caller used a subset."""
        return registry.add(self.dataset, self.dataset_id, self.period, self.retrieved_at, url or self.url, self.note)


# --- typed rows ---

@dataclass
class Hospital:
    ccn: str
    name: str
    city: str
    county: str
    zip: str
    type: str
    ownership: str | None
    rating: int | None
    emergency: bool


@dataclass
class InpatientRow:
    ccn: str
    name: str
    city: str
    zip: str
    drg: int
    drg_desc: str
    discharges: int | None
    avg_charge: float | None
    avg_total_payment: float | None
    avg_medicare_payment: float | None


@dataclass
class GeoBenchmark:
    level: str  # National | State
    geo: str
    drg: int
    drg_desc: str
    discharges: int | None
    avg_charge: float | None
    avg_total_payment: float | None
    avg_medicare_payment: float | None


@dataclass
class HrrpRow:
    ccn: str
    name: str
    measure: str
    discharges: int | None
    err: float | None  # excess readmission ratio; > 1 is worse than expected
    predicted: float | None
    expected: float | None
    readmissions: int | None
    footnote: str | None
    period: str


@dataclass
class ComplicationRow:
    ccn: str
    name: str
    measure_id: str
    measure_name: str
    compared_to_national: str | None  # only PSI measures carry this
    denominator: int | None
    score: float | None
    lower: float | None
    upper: float | None
    footnote: str | None
    period: str


@dataclass
class NationalMeasure:
    measure_id: str
    name: str
    national_rate: float | None
    better: int | None
    same: int | None
    worse: int | None
    too_few: int | None
    period: str


@dataclass
class HcahpsStar:
    ccn: str
    name: str
    stars: int | None
    surveys: int | None
    period: str


# --- slice specs (NY constant lives here) ---

_NY_PROVIDER = (("state", "=", config.STATE),)

GENERAL_INFO = SliceSpec(
    "general_info", "provider", config.GENERAL_INFO, conditions=_NY_PROVIDER,
    columns=("facility_id", "facility_name", "address", "citytown", "zip_code", "countyparish", "hospital_type",
             "hospital_ownership", "emergency_services", "hospital_overall_rating"),
)
INPATIENT = SliceSpec(
    "ny_inpatient", "data_api", config.INPATIENT_BY_PROVIDER, filters=(("Rndrng_Prvdr_State_Abrvtn", config.STATE),),
    columns=("Rndrng_Prvdr_CCN", "Rndrng_Prvdr_Org_Name", "Rndrng_Prvdr_City", "Rndrng_Prvdr_Zip5", "DRG_Cd", "DRG_Desc",
             "Tot_Dschrgs", "Avg_Submtd_Cvrd_Chrg", "Avg_Tot_Pymt_Amt", "Avg_Mdcr_Pymt_Amt"),
)
HRRP = SliceSpec(
    "hrrp", "provider", config.HRRP, conditions=_NY_PROVIDER,
    columns=("facility_id", "facility_name", "measure_name", "number_of_discharges", "footnote", "excess_readmission_ratio",
             "predicted_readmission_rate", "expected_readmission_rate", "number_of_readmissions", "start_date", "end_date"),
)
COMPLICATIONS = SliceSpec(
    "complications", "provider", config.COMPLICATIONS, conditions=_NY_PROVIDER,
    columns=("facility_id", "facility_name", "measure_id", "measure_name", "compared_to_national", "denominator", "score",
             "lower_estimate", "higher_estimate", "footnote", "start_date", "end_date"),
)
NATIONAL = SliceSpec(
    "complications_national", "provider", config.COMPLICATIONS_NATIONAL,
    columns=("measure_id", "measure_name", "national_rate", "number_of_hospitals_worse", "number_of_hospitals_same",
             "number_of_hospitals_better", "number_of_hospitals_too_few", "start_date", "end_date"),
)
HCAHPS_STAR = SliceSpec(
    "hcahps_star", "provider", config.HCAHPS, conditions=_NY_PROVIDER + (("hcahps_measure_id", "=", "H_STAR_RATING"),),
    columns=("facility_id", "facility_name", "patient_survey_star_rating", "number_of_completed_surveys", "start_date", "end_date"),
)

GEO_COLUMNS = ("Rndrng_Prvdr_Geo_Lvl", "Rndrng_Prvdr_Geo_Desc", "DRG_Cd", "DRG_Desc", "Tot_Dschrgs", "Avg_Submtd_Cvrd_Chrg",
               "Avg_Tot_Pymt_Amt", "Avg_Mdcr_Pymt_Amt")


def drg_code(drg: int | str) -> str:
    return f"{int(drg):03d}"  # CMS stores DRG codes as zero-padded text ("061", "470")


def geo_spec(drg: int | str) -> SliceSpec:
    code = drg_code(drg)
    return SliceSpec(f"geo_{code}", "data_api", config.INPATIENT_BY_GEOGRAPHY, filters=(("DRG_Cd", code),), columns=GEO_COLUMNS)


def _result(f: Fetched, dataset: str, dataset_id: str, rows: list, per: str) -> Result:
    return Result(rows, dataset, dataset_id, per, f.url, f.retrieved, f.served_from, f.note, f.built_at)


# --- adapters ---

async def general_info_ny(client: CmsClient | None = None) -> Result:
    f = await (client or get_client()).get_slice(GENERAL_INFO)
    rows = [Hospital(r["facility_id"], r["facility_name"], clean(r["citytown"]) or "", (clean(r["countyparish"]) or "").title(),
                     clean(r["zip_code"]) or "", clean(r["hospital_type"]) or "", clean(r["hospital_ownership"]),
                     integer(r["hospital_overall_rating"]), clean(r["emergency_services"]) == "Yes") for r in f.rows]
    return _result(f, "Hospital General Information", config.GENERAL_INFO, rows, "current (Care Compare release)")


async def ny_inpatient(client: CmsClient | None = None) -> Result:
    f = await (client or get_client()).get_slice(INPATIENT)
    rows = [InpatientRow(r["Rndrng_Prvdr_CCN"], r["Rndrng_Prvdr_Org_Name"], r["Rndrng_Prvdr_City"], r["Rndrng_Prvdr_Zip5"],
                         int(r["DRG_Cd"]), r["DRG_Desc"], integer(r["Tot_Dschrgs"]), num(r["Avg_Submtd_Cvrd_Chrg"]),
                         num(r["Avg_Tot_Pymt_Amt"]), num(r["Avg_Mdcr_Pymt_Amt"])) for r in f.rows]
    return _result(f, "Medicare Inpatient Hospitals by Provider and Service", config.INPATIENT_BY_PROVIDER, rows, "CY2024")


async def geo_benchmark(drg: int | str, client: CmsClient | None = None) -> Result:
    """National and New York State rows for one DRG (the other states are dropped)."""
    f = await (client or get_client()).get_slice(geo_spec(drg))
    keep = [r for r in f.rows if r["Rndrng_Prvdr_Geo_Lvl"] == "National" or (r["Rndrng_Prvdr_Geo_Lvl"] == "State" and r["Rndrng_Prvdr_Geo_Desc"] == "New York")]
    rows = [GeoBenchmark(r["Rndrng_Prvdr_Geo_Lvl"], r["Rndrng_Prvdr_Geo_Desc"], int(r["DRG_Cd"]), r["DRG_Desc"], integer(r["Tot_Dschrgs"]),
                         num(r["Avg_Submtd_Cvrd_Chrg"]), num(r["Avg_Tot_Pymt_Amt"]), num(r["Avg_Mdcr_Pymt_Amt"])) for r in keep]
    res = _result(f, "Medicare Inpatient Hospitals by Geography and Service", config.INPATIENT_BY_GEOGRAPHY, rows, "CY2024")
    res.url = data_api_url(config.INPATIENT_BY_GEOGRAPHY, {"DRG_Cd": drg_code(drg)})
    return res


async def hrrp_ny(client: CmsClient | None = None) -> Result:
    f = await (client or get_client()).get_slice(HRRP)
    rows = [HrrpRow(r["facility_id"], r["facility_name"], r["measure_name"], integer(r["number_of_discharges"]),
                    num(r["excess_readmission_ratio"]), num(r["predicted_readmission_rate"]), num(r["expected_readmission_rate"]),
                    integer(r["number_of_readmissions"]), clean(r["footnote"]), period(r["start_date"], r["end_date"])) for r in f.rows]
    per = rows[0].period if rows else "unspecified"
    return _result(f, "Hospital Readmissions Reduction Program", config.HRRP, rows, per)


async def complications_ny(client: CmsClient | None = None) -> Result:
    f = await (client or get_client()).get_slice(COMPLICATIONS)
    rows = [ComplicationRow(r["facility_id"], r["facility_name"], r["measure_id"], r["measure_name"], clean(r["compared_to_national"]),
                            integer(r["denominator"]), num(r["score"]), num(r["lower_estimate"]), num(r["higher_estimate"]),
                            clean(r["footnote"]), period(r["start_date"], r["end_date"])) for r in f.rows]
    per = rows[0].period if rows else "unspecified"
    return _result(f, "Complications and Deaths - Hospital", config.COMPLICATIONS, rows, per)


async def complications_national(client: CmsClient | None = None) -> Result:
    f = await (client or get_client()).get_slice(NATIONAL)
    rows = [NationalMeasure(r["measure_id"], r["measure_name"], num(r["national_rate"]), integer(r["number_of_hospitals_better"]),
                            integer(r["number_of_hospitals_same"]), integer(r["number_of_hospitals_worse"]),
                            integer(r["number_of_hospitals_too_few"]), period(r["start_date"], r["end_date"])) for r in f.rows]
    per = rows[0].period if rows else "unspecified"
    return _result(f, "Complications and Deaths - National Data", config.COMPLICATIONS_NATIONAL, rows, per)


async def hcahps_star_ny(client: CmsClient | None = None) -> Result:
    f = await (client or get_client()).get_slice(HCAHPS_STAR)
    rows = [HcahpsStar(r["facility_id"], r["facility_name"], integer(r["patient_survey_star_rating"]), integer(r["number_of_completed_surveys"]),
                       period(r["start_date"], r["end_date"])) for r in f.rows]
    per = rows[0].period if rows else "unspecified"
    res = _result(f, "HCAHPS Patient Survey - Hospital", config.HCAHPS, rows, per)
    res.url = provider_url(config.HCAHPS, [("state", "=", config.STATE), ("hcahps_measure_id", "=", "H_STAR_RATING")])
    return res
