"""Canonical vocabulary and rule-based extraction for rental requirements.

The agent reads the user's sentence and proposes structured requirements.
This module is the single source of truth for what the canonical values are,
maps free-text synonyms onto them, and catches what a regex can catch
deterministically (BHK, furnishing, budget, amenities...). Anything it cannot
map is returned in `unmapped` so the agent can ask rather than silently drop it.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

FURNISHING: dict[str, list[str]] = {
    "unfurnished": ["unfurnished", "un furnished", "empty", "bare shell"],
    "semi_furnished": ["semi furnished", "semi-furnished", "semifurnished", "partly furnished", "part furnished"],
    "furnished": ["fully furnished", "full furnished", "furnished"],
}

PROPERTY_TYPES: dict[str, list[str]] = {
    "apartment": ["apartment", "flat", "condo"],
    "independent_house": ["independent house", "house", "home"],
    "villa": ["villa", "row house", "townhouse"],
    "bungalow": ["bungalow"],
    "serviced_apartment": ["serviced apartment", "service apartment", "serviced apt"],
    "builder_floor": ["builder floor", "independent floor"],
}

# key -> (label, group, synonyms). Longer synonyms win, so list freely.
AMENITIES: dict[str, tuple[str, str, list[str]]] = {
    # parking
    "parking_2w": ("2-wheeler parking", "parking", ["2 wheeler parking", "two wheeler parking", "2wheeler parking", "bike parking", "scooter parking", "2w parking", "2 wheeler"]),
    "parking_4w": ("4-wheeler parking", "parking", ["4 wheeler parking", "four wheeler parking", "4wheeler parking", "car parking", "covered parking", "4w parking", "4 wheeler", "parking"]),
    # safety and society
    "gated_community": ("Gated community", "society", ["gated community", "gated society", "gated"]),
    "security_24x7": ("24x7 security", "society", ["24x7 security", "24/7 security", "24 x 7 security", "round the clock security", "security guard", "security"]),
    "cctv": ("CCTV camera security", "society", ["cctv camera security", "cctv cameras", "cctv"]),
    "intercom": ("Intercom facilities", "society", ["intercom facilities", "intercom"]),
    "entrance_lobby": ("Entrance lobby", "society", ["entrance lobby", "lobby"]),
    "power_backup": ("24/7 power backup", "society", ["24/7 power backup", "24x7 power backup", "power backup", "dg backup", "generator backup", "inverter backup"]),
    "lift": ("Lift", "society", ["lift", "elevator"]),
    # utilities
    "sewage_treatment_plant": ("Sewage treatment plant", "utilities", ["sewage treatment plant", "sewage treatment", "stp"]),
    "rain_water_harvesting": ("Rain water harvesting", "utilities", ["rain water harvesting", "rainwater harvesting", "rwh"]),
    "water_treatment_plant": ("Water treatment plant", "utilities", ["water treatment plant", "water treatment", "wtp"]),
    "paved_compound": ("Paved compound", "utilities", ["paved compound"]),
    # recreation
    "swimming_pool": ("Swimming pool", "recreation", ["swimming pool", "pool"]),
    "gym": ("Gymnasium", "recreation", ["gymnasium", "gym", "fitness centre", "fitness center"]),
    "club_house": ("Club house", "recreation", ["club house", "clubhouse"]),
    "childrens_play_area": ("Children's play area", "recreation", ["children's play area", "childrens play area", "kids play area", "kids' play area", "play area"]),
    "theatre": ("Theatre", "recreation", ["mini theatre", "home theatre", "theatre", "theater"]),
    "landscape_garden": ("Landscape garden", "recreation", ["landscape garden", "landscaped garden", "garden"]),
    "park": ("Park", "recreation", ["park"]),
    "amphitheatre": ("Amphitheatre", "recreation", ["amphitheatre", "amphitheater"]),
    "jogging_track": ("Jogging track", "recreation", ["jogging track", "running track", "jogging"]),
    "yoga_meditation": ("Yoga / meditation area", "recreation", ["yoga meditation area", "yoga area", "meditation area", "yoga", "meditation"]),
    "multipurpose_hall": ("Multipurpose hall", "recreation", ["multipurpose hall", "multi purpose hall"]),
    "party_lawn": ("Party lawn", "recreation", ["party lawn"]),
    "indoor_games": ("Indoor games", "recreation", ["indoor games"]),
    "reflexology_park": ("Reflexology park", "recreation", ["reflexology park", "reflexology"]),
    "open_space": ("Open space", "recreation", ["open space"]),
    "senior_citizen_sitout": ("Senior citizen sit-out", "recreation", ["senior citizen sit out", "senior citizen sitout", "senior citizen"]),
    "sit_out_area": ("Sit-out area", "recreation", ["sit out area", "sitout area", "sit out", "sitout"]),
    # sports
    "basketball_court": ("Basketball court", "sports", ["basketball court", "basketball"]),
    "skating_rink": ("Skating rink", "sports", ["skating rink", "skating"]),
    "cricket_pitch": ("Cricket pitch", "sports", ["cricket pitch", "cricket"]),
    "multipurpose_court": ("Multipurpose court", "sports", ["multipurpose court", "multi purpose court"]),
    "tennis_court": ("Tennis court", "sports", ["tennis court", "tennis"]),
    "badminton_court": ("Badminton court", "sports", ["badminton court", "badminton"]),
    # household policies / features
    "pets_allowed": ("Pets allowed", "features", ["pet friendly", "pets allowed", "pet allowed", "pets ok", "pets"]),
    "vastu_compliant": ("Vastu compliant", "features", ["vastu compliant", "vastu complaint", "vastu"]),
}

# Amenities that are deal-breakers unless the user says otherwise.
DEFAULT_MUST = {"pets_allowed", "parking_2w", "parking_4w"}

MUST_CUES = re.compile(r"\b(must|need|needs|needed|have to|has to|essential|mandatory|compulsory|required|no compromise|only)\b")

DIRECTIONS = ["north_east", "north_west", "south_east", "south_west", "north", "south", "east", "west"]

_SPACE = re.compile(r"[\s_]+")


def _norm(text: str) -> str:
    return _SPACE.sub(" ", text.casefold().replace("’", "'")).strip()


def _synonym_table(table: Mapping[str, list[str]]) -> list[tuple[str, str]]:
    pairs = [(_norm(s), key) for key, syns in table.items() for s in syns + [key]]
    return sorted(pairs, key=lambda p: -len(p[0]))


_FURNISHING_SYN = _synonym_table(FURNISHING)
_PROPERTY_SYN = _synonym_table(PROPERTY_TYPES)
_AMENITY_SYN = sorted(
    ((_norm(s), key) for key, (_, _, syns) in AMENITIES.items() for s in syns + [key]),
    key=lambda p: -len(p[0]),
)


def _find_all(text: str, table: list[tuple[str, str]]) -> list[str]:
    """Match synonyms longest-first, blanking each match so 'car parking' is
    not also counted as 'parking' and 'gym' inside 'gymnasium' counts once."""
    found: list[str] = []
    work = f" {_norm(text)} "
    for syn, key in table:
        pat = re.compile(rf"(?<![a-z0-9]){re.escape(syn)}(?![a-z0-9])")
        if pat.search(work):
            if key not in found:
                found.append(key)
            work = pat.sub(" ", work)
    return found


def canonical_furnishing(text: str) -> str | None:
    found = _find_all(text, _FURNISHING_SYN)
    return found[0] if found else None


def canonical_property_types(text: str) -> list[str]:
    return _find_all(text, _PROPERTY_SYN)


def canonical_amenities(text: str) -> list[str]:
    return _find_all(text, _AMENITY_SYN)


def canonical_unit_type(text: str) -> str | None:
    """'2 bhk' -> '2bhk', '2.5BHK' -> '2.5bhk', '1 rk' -> '1rk', 'studio' -> 'studio'."""
    t = _norm(text)
    if re.search(r"\bstudio\b", t):
        return "studio"
    m = re.search(r"(\d(?:\.5)?)\s*-?\s*(bhk|rk)\b", t)
    return f"{m.group(1)}{m.group(2)}" if m else None


def canonical_direction(text: str) -> str | None:
    t = _norm(text).replace("-", " ")
    for d in DIRECTIONS:
        if re.search(rf"\b{d.replace('_', ' ')}\b", t):
            return d
    return None


def _money(num: str, unit: str | None) -> int:
    value = float(num.replace(",", ""))
    unit = (unit or "").lower()
    if unit in {"k", "thousand"}:
        value *= 1_000
    elif unit in {"l", "lac", "lakh", "lakhs"}:
        value *= 100_000
    return int(round(value))


_NUM = r"(\d[\d,]*(?:\.\d+)?)\s*(k|thousand|lakhs?|lacs?|l)?"
_BUDGET_CUE = re.compile(r"(budget|rent|under|below|upto|up to|within|max|maximum|around|₹|rs\.?|inr|/\s*month|per month|\bpm\b)")


def extract_budget(text: str) -> dict[str, Any] | None:
    t = _norm(text)
    if not _BUDGET_CUE.search(t):
        return None
    rng = re.search(rf"{_NUM}\s*(?:-|to)\s*{_NUM}", t)
    if rng:
        hi_unit = rng.group(4) or rng.group(2)  # '30-40k' applies k to both
        lo_unit = rng.group(2) or hi_unit
        lo, hi = _money(rng.group(1), lo_unit), _money(rng.group(3), hi_unit)
        if lo >= 1_000 and hi >= 1_000:
            return {"min": min(lo, hi), "max": max(lo, hi), "currency": "INR", "period": "month"}
    m = re.search(rf"(under|below|upto|up to|within|max(?:imum)?|budget(?: of)?|around|rent(?: of)?|₹|rs\.?|inr)\s*(?:₹|rs\.?|inr)?\s*{_NUM}", t)
    if m:
        amount = _money(m.group(2), m.group(3))
        if amount >= 1_000:
            key = "approx" if m.group(1) == "around" else "max"
            return {key: amount, "currency": "INR", "period": "month"}
    return None


def extract_hints(text: str) -> dict[str, Any]:
    """Deterministic first pass over the user's sentence."""
    t = _norm(text)
    assumptions: list[str] = []
    hints: dict[str, Any] = {
        "furnishing": canonical_furnishing(t),
        "unit_types": [],
        "property_types": canonical_property_types(re.sub(r"\d(?:\.5)?\s*-?\s*(bhk|rk)\b", " ", t)),
        "budget": extract_budget(text),
        "amenities": {"must": [], "nice": []},
        "assumptions": assumptions,
    }
    for m in re.finditer(r"(\d(?:\.5)?)\s*-?\s*(bhk|rk)\b", t):
        unit = f"{m.group(1)}{m.group(2)}"
        if unit not in hints["unit_types"]:
            hints["unit_types"].append(unit)
    if re.search(r"\bstudio\b", t):
        hints["unit_types"].append("studio")

    face = re.search(r"(?:main door\s+)?(?:facing\s+)?(north[\s-]?east|north[\s-]?west|south[\s-]?east|south[\s-]?west|north|south|east|west)[\s-]*(?:facing|door)|facing\s+(north[\s-]?east|north[\s-]?west|south[\s-]?east|south[\s-]?west|north|south|east|west)", t)
    if face:
        hints["facing"] = canonical_direction(face.group(1) or face.group(2))

    area = re.findall(r"(\d{3,5})\s*(?:-|to)?\s*(\d{3,5})?\s*(?:sq\.?\s*ft|sqft|sft|square feet)", t)
    if area:
        lo, hi = area[0]
        hints["area_sqft"] = {"min": int(lo), "max": int(hi)} if hi else {"approx": int(lo)}

    bath = re.search(r"(\d)\s*(?:bath|bathroom|toilet)s?\b", t)
    if bath:
        hints["bathrooms_min"] = int(bath.group(1))

    age = re.search(r"(?:under|less than|within|below|<)\s*(\d+)\s*(?:years?|yrs?)(?:\s*old)?", t)
    if age:
        hints["property_age_max_years"] = int(age.group(1))
    elif re.search(r"\b(new construction|newly built|brand new)\b", t):
        hints["property_age_max_years"] = 3

    floor = re.search(r"(\d+)(?:st|nd|rd|th)\s*floor", t)
    if floor:
        hints["floor"] = {"exact": int(floor.group(1))}
    elif "ground floor" in t:
        hints["floor"] = {"exact": 0}
    else:
        pref = re.search(r"\b(top|high|low|mid)\s*floor", t)
        if pref:
            hints["floor"] = {"pref": pref.group(1)}

    # Split into clauses so a "must" in one clause does not promote every amenity.
    for clause in re.split(r"[,;\n]| and | with ", t):
        keys = canonical_amenities(clause)
        is_must = bool(MUST_CUES.search(clause))
        for key in keys:
            bucket = "must" if is_must or key in DEFAULT_MUST else "nice"
            other = "nice" if bucket == "must" else "must"
            if key in hints["amenities"][other]:
                hints["amenities"][other].remove(key)
            if key not in hints["amenities"][bucket]:
                hints["amenities"][bucket].append(key)
    if re.search(r"(?<![a-z0-9])parking(?![a-z0-9])", t) and not re.search(r"(car|4 ?w|four|covered|bike|2 ?w|two|scooter)\w*[ -]*(wheeler)?\s*parking", t):
        assumptions.append("'parking' read as car (4-wheeler) parking; confirm if you meant bikes")
    return hints


def normalize_requirements(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and canonicalise requirements proposed by the agent.

    Accepts free-text values anywhere a canonical key is expected and returns
    the canonical form plus `unmapped` (things to ask the user about) and
    `warnings`. Unknown top-level keys pass through untouched.
    """
    out: dict[str, Any] = dict(raw)
    unmapped: list[str] = []
    warnings: list[str] = []

    if raw.get("furnishing"):
        f = canonical_furnishing(str(raw["furnishing"]))
        if f is None:
            unmapped.append(f"furnishing: {raw['furnishing']}")
        out["furnishing"] = f

    units = raw.get("unit_types") or ([raw["unit_type"]] if raw.get("unit_type") else [])
    canon_units = []
    for u in units:
        c = canonical_unit_type(str(u))
        if c:
            canon_units.append(c)
        else:
            unmapped.append(f"unit_type: {u}")
    out["unit_types"] = canon_units
    out.pop("unit_type", None)

    ptypes = raw.get("property_types") or ([raw["property_type"]] if raw.get("property_type") else [])
    canon_pt: list[str] = []
    for p in ptypes:
        found = canonical_property_types(str(p))
        if found:
            canon_pt.extend(x for x in found if x not in canon_pt)
        else:
            unmapped.append(f"property_type: {p}")
    out["property_types"] = canon_pt
    out.pop("property_type", None)

    am_in = raw.get("amenities") or {}
    if isinstance(am_in, list):  # tolerate a flat list: treat as nice-to-have
        am_in = {"nice": am_in}
    amenities: dict[str, list[str]] = {"must": [], "nice": []}
    for bucket in ("must", "nice"):
        for item in am_in.get(bucket, []):
            keys = [item] if item in AMENITIES else canonical_amenities(str(item))
            if not keys:
                unmapped.append(f"amenity: {item}")
            for k in keys:
                if k not in amenities[bucket]:
                    amenities[bucket].append(k)
    overlap = set(amenities["must"]) & set(amenities["nice"])
    for k in overlap:
        amenities["nice"].remove(k)
        warnings.append(f"{k} was in both lists; kept as must-have")
    out["amenities"] = amenities

    if raw.get("facing"):
        d = canonical_direction(str(raw["facing"]))
        if d is None:
            unmapped.append(f"facing: {raw['facing']}")
        out["facing"] = d

    out["unmapped"] = unmapped
    out["warnings"] = warnings
    return out


def parse_text(text: str) -> dict[str, Any]:
    """extract_hints() then normalize_requirements(); the CLI's `normalize --text`."""
    hints = extract_hints(text)
    assumptions = hints.pop("assumptions")
    result = normalize_requirements(hints)
    result["assumptions"] = assumptions
    return result
