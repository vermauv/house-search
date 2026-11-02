import pytest

from housesearch import vocab


def test_extracts_core_fields_from_the_users_example():
    r = vocab.parse_text(
        "I want a semi furnished 2.5 bhk apartment in Mahadevapura with 2 wheeler parking, "
        "gym, swimming pool, pets allowed, vastu compliant, east facing, 24/7 power backup, under 55k"
    )
    assert r["furnishing"] == "semi_furnished"
    assert r["unit_types"] == ["2.5bhk"]
    assert r["property_types"] == ["apartment"]
    assert r["facing"] == "east"
    assert r["budget"] == {"max": 55000, "currency": "INR", "period": "month"}
    assert {"parking_2w", "pets_allowed"} <= set(r["amenities"]["must"])  # blockers default to must
    assert {"gym", "swimming_pool", "vastu_compliant", "power_backup"} <= set(r["amenities"]["nice"])
    assert r["unmapped"] == []


@pytest.mark.parametrize(
    "text,expected",
    [("2 BHK", "2bhk"), ("1rk", "1rk"), ("Studio flat", "studio"), ("3-bhk", "3bhk"), ("5 bhk villa", "5bhk")],
)
def test_unit_types(text, expected):
    assert vocab.canonical_unit_type(text) == expected


def test_furnished_does_not_swallow_unfurnished_or_semi():
    assert vocab.canonical_furnishing("unfurnished") == "unfurnished"
    assert vocab.canonical_furnishing("semi-furnished") == "semi_furnished"
    assert vocab.canonical_furnishing("fully furnished") == "furnished"


def test_longest_match_wins_and_is_not_double_counted():
    assert vocab.canonical_amenities("car parking") == ["parking_4w"]
    assert vocab.canonical_amenities("two wheeler parking") == ["parking_2w"]
    assert vocab.canonical_amenities("gymnasium") == ["gym"]
    # 'park' must not match inside 'parking'
    assert "park" not in vocab.canonical_amenities("covered parking")


def test_bare_parking_is_assumed_to_be_cars_and_says_so():
    r = vocab.parse_text("2bhk flat with parking")
    assert "parking_4w" in r["amenities"]["must"]
    assert any("parking" in a for a in r["assumptions"])


def test_must_cue_only_promotes_its_own_clause():
    r = vocab.extract_hints("2bhk, must have gym, swimming pool")
    assert r["amenities"]["must"] == ["gym"]
    assert r["amenities"]["nice"] == ["swimming_pool"]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("budget 30-40k", {"min": 30000, "max": 40000}),
        ("rent below 45,000", {"max": 45000}),
        ("up to 1.2 lakh", {"max": 120000}),
        ("around ₹35000", {"approx": 35000}),
    ],
)
def test_budget(text, expected):
    got = vocab.extract_budget(text)
    assert {k: got[k] for k in expected} == expected


def test_budget_ignores_numbers_that_are_not_money():
    assert vocab.extract_budget("1200 sqft 3bhk") is None
    assert vocab.extract_hints("2bhk 1000 sqft flat")["area_sqft"] == {"approx": 1000}


def test_other_attributes():
    h = vocab.extract_hints("3rd floor, 2 bathrooms, under 5 years old, north-east facing")
    assert h["floor"] == {"exact": 3}
    assert h["bathrooms_min"] == 2
    assert h["property_age_max_years"] == 5
    assert h["facing"] == "north_east"


def test_normalize_requirements_reports_what_it_cannot_map():
    r = vocab.normalize_requirements(
        {"furnishing": "fully furnished", "unit_type": "2 bhk", "property_type": "flat",
         "amenities": {"must": ["car parking"], "nice": ["helipad", "gym"]}}
    )
    assert r["furnishing"] == "furnished"
    assert r["unit_types"] == ["2bhk"]
    assert r["property_types"] == ["apartment"]
    assert r["amenities"] == {"must": ["parking_4w"], "nice": ["gym"]}
    assert r["unmapped"] == ["amenity: helipad"]


def test_overlap_keeps_must_have():
    r = vocab.normalize_requirements({"amenities": {"must": ["gym"], "nice": ["gym"]}})
    assert r["amenities"] == {"must": ["gym"], "nice": []}
    assert r["warnings"]


def test_user_supplied_amenity_list_is_fully_covered():
    """Every amenity named in the original request resolves to a key."""
    names = """Swimming Pool|Gymnasium|Club House|Children's Play Area|Theatre|Landscape Garden|Park|Amphitheatre|
    Jogging Track|Basketball Court|Skating Rink|Yoga/Meditation Area|Cricket Pitch|Multipurpose Hall|Multipurpose court|
    Party Lawn|Indoor Games|Reflexology Park|Open Space|Senior Citizen Sitout|Sit Out Area|Gated Community|Paved Compound|
    CCTV Camera Security|24x7 Security|Intercom Facilities|Entrance Lobby|24/7 Power Backup|Sewage Treatment Plant|
    Rain Water Harvesting|Water Treatment Plant|2wheeler parking|4wheeler parking|Vastu compliant|pets allowed""".replace("\n", "").split("|")
    for n in names:
        assert vocab.canonical_amenities(n.strip()), f"unmapped: {n}"
