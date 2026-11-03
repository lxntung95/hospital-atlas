"""T5/T6 and friends: deterministic lookups over data/*.json and a hospital list."""

from types import SimpleNamespace as H

import pytest

from atlas import crosswalk as cw

HOSPITALS = [
    H(ccn="330059", name="MONTEFIORE MEDICAL CENTER", city="BRONX", county="Bronx"),
    H(ccn="330086", name="MONTEFIORE MOUNT VERNON HOSPITAL", city="MOUNT VERNON", county="Westchester"),
    H(ccn="330009", name="BRONXCARE HOSPITAL CENTER", city="BRONX", county="Bronx"),
    H(ccn="330101", name="NEW YORK-PRESBYTERIAN HOSPITAL", city="NEW YORK", county="New York"),
    H(ccn="330214", name="NYU LANGONE HOSPITALS", city="NEW YORK", county="New York"),
    H(ccn="33016F", name="BRONX VA MEDICAL CENTER", city="BRONX", county="Bronx"),
]


def test_T5_find_hospitals_montefiore_first():
    res = cw.find_hospitals("Montefiore", HOSPITALS)
    assert res.matches[0].ccn == "330059" and res.unresolved is None


def test_T5_out_of_state_is_out_of_scope():
    res = cw.find_hospitals("Mass General", HOSPITALS)
    assert res.matches == [] and "outside NY scope" in res.unresolved


def test_find_hospitals_typo_alias_and_unknown():
    assert cw.find_hospitals("Montefior", HOSPITALS).matches[0].ccn == "330059"
    assert cw.find_hospitals("NYP", HOSPITALS).matches[0].ccn == "330101"
    assert cw.find_hospitals("Nonexistent Clinic", HOSPITALS).unresolved == "no NY hospital matched that name"


def test_T6_heart_failure_services():
    (svc,) = cw.find_services("heart failure")
    assert 291 in svc.drgs and {"READM-30-HF-HRRP", "MORT_30_HF"} <= set(svc.measures)


def test_services_by_alias_and_drg_number():
    assert cw.find_services("knee replacement")[0].condition == "hip_knee_replacement"
    assert cw.find_services("DRG 470")[0].condition == "hip_knee_replacement"
    assert cw.find_services("CHF")[0].condition == "heart_failure"
    assert cw.find_services("quantum physics") == []


def test_services_catalog_fallback_for_unknown_drg():
    out = cw.find_services("DRG 603", drg_catalog={603: "CELLULITIS WITHOUT MCC"})
    assert out[0].drgs == [603] and "Cellulitis" in out[0].label


def test_detect_q2_style_message():
    d = cw.detect("Compare Montefiore with other Bronx hospitals on heart failure DRG 291", HOSPITALS)
    assert d.condition == "heart_failure" and d.counties == ["Bronx"] and d.drgs == [291]
    assert d.hospital_hints == ["MONTEFIORE MEDICAL CENTER"] and not d.vague


def test_detect_vague_and_out_of_scope():
    assert cw.detect("Which NY hospitals are the best?", HOSPITALS).vague
    d = cw.detect("How does Boston compare to New York for knee replacement?", HOSPITALS)
    assert "boston" in d.out_of_scope and d.condition == "hip_knee_replacement"


def test_washington_and_delaware_are_not_treated_as_other_states():
    assert cw.out_of_scope_terms("hospitals in Washington County or Delaware County") == []


def test_shipped_reference_data_is_consistent():
    measures = cw.measures()
    for key, c in cw.crosswalk().items():
        for m in (c["hrrp_measure"], c["mort_measure"], c["comp_measure"], *c["psi"]):
            assert m is None or m in measures, f"{key}: {m} missing from measures.json"
        assert c["drgs"] and 293 not in c["drgs"]
    assert cw.crosswalk()["heart_failure"]["drgs"] == [291, 292]


def test_regions_cover_all_known_ny_counties():
    known = {"ALBANY", "ALLEGANY", "BRONX", "BROOME", "CATTARAUGUS", "CAYUGA", "CHAUTAUQUA", "CHEMUNG", "CHENANGO", "CLINTON", "COLUMBIA",
             "CORTLAND", "DELAWARE", "DUTCHESS", "ERIE", "ESSEX", "FRANKLIN", "FULTON", "GENESEE", "HERKIMER", "JEFFERSON", "KINGS", "LEWIS",
             "LIVINGSTON", "MADISON", "MONROE", "MONTGOMERY", "NASSAU", "NEW YORK", "NIAGARA", "ONEIDA", "ONONDAGA", "ONTARIO", "ORANGE",
             "ORLEANS", "OSWEGO", "OTSEGO", "PUTNAM", "QUEENS", "RENSSELAER", "RICHMOND", "ROCKLAND", "SARATOGA", "SCHENECTADY", "SCHOHARIE",
             "SCHUYLER", "ST. LAWRENCE", "STEUBEN", "SUFFOLK", "SULLIVAN", "TOMPKINS", "ULSTER", "WARREN", "WAYNE", "WESTCHESTER", "WYOMING", "YATES"}
    covered = {c.upper() for cs in cw.regions()["regions"].values() for c in cs}
    assert known <= covered, known - covered


@pytest.mark.parametrize("text,region", [("hospitals on Long Island", "Long Island"), ("upstate Rochester area", "Finger Lakes"), ("in Brooklyn", "New York City")])
def test_regions(text, region):
    assert cw.find_region(text)[0] == region
