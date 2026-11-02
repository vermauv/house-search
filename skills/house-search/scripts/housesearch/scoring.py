"""Hard-filter, score and rank listings.

Design rules:
  * Missing data is never treated as bad data. A component with no input is
    left out and the remaining weights are renormalised; `coverage` and
    `confidence` tell the reader how much of the score was actually measured.
  * Explicit mismatches exclude a listing; unknowns only flag it
    ("unverified: ask the owner").
  * Waterlogging never changes the score. It is a warning the user weighs.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, fields
from datetime import date
from pathlib import Path
from typing import Any, Mapping

WEIGHTS_PATH = Path(__file__).resolve().parents[2] / "assets" / "weights.default.json"

SEVERITY_WEIGHT = {"minor": 1.0, "property": 2.0, "violent": 4.0, "sexual": 6.0}

NEUTRAL = 50.0

COMPONENTS = ("safety", "medical", "commute", "amenities", "metro", "entertainment")


@dataclass(frozen=True)
class Weights:
    safety: float = 0.30
    medical: float = 0.25
    commute: float = 0.15
    amenities: float = 0.15
    metro: float = 0.075
    entertainment: float = 0.075

    @classmethod
    def load(cls, path: Path | None = None) -> "Weights":
        with (path or WEIGHTS_PATH).open(encoding="utf-8") as fh:
            raw = json.load(fh)
        known = {f.name for f in fields(cls)}
        unknown = set(raw) - known - {"_comment"}
        if unknown:
            raise ValueError(f"Unknown weight keys: {sorted(unknown)}")
        return cls(**{k: float(v) for k, v in raw.items() if k in known})

    def as_dict(self) -> dict[str, float]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


# --- primitives ---------------------------------------------------------------


def linear(value: float | None, best: float, worst: float) -> float | None:
    """Map a lower-is-better value onto 0-100: `best` -> 100, `worst` -> 0."""
    if value is None:
        return None
    if best == worst:
        raise ValueError("best and worst must differ")
    frac = (worst - value) / (worst - best)
    return round(100 * min(1.0, max(0.0, frac)), 1)


def _parse_date(value: str) -> date:
    parts = [int(p) for p in str(value).split("-")]
    return date(parts[0], parts[1] if len(parts) > 1 else 6, parts[2] if len(parts) > 2 else 15)


# --- safety -------------------------------------------------------------------


def news_safety_score(
    incidents: list[Mapping[str, Any]],
    today: date | None = None,
    k: float = 8.0,
    half_life_months: float = 12.0,
) -> float:
    """100 * exp(-load / k), where load is severity-weighted, recency-decayed incidents.

    Each incident: {"severity": minor|property|violent|sexual, "date": "YYYY[-MM[-DD]]"}.
    `k` sets how many weighted incidents halve-ish the score (k=8 -> a load of 8 gives ~37).
    Compare localities against each other rather than reading the number in
    isolation: busier, bigger areas generate more headlines.
    """
    today = today or date.today()
    load = 0.0
    for inc in incidents:
        weight = SEVERITY_WEIGHT[inc["severity"]]
        months = max(0.0, (today - _parse_date(inc["date"])).days / 30.44)
        load += weight * 0.5 ** (months / half_life_months)
    return round(100 * math.exp(-load / k), 1)


def combine_safety(parts: Mapping[str, float | None]) -> dict[str, Any]:
    """Blend station statistics, news and property-level security.

    Keys: "station", "news", "property". Missing parts are dropped and the
    weights renormalised; confidence reflects how many independent parts exist.
    """
    weights = {"station": 0.4, "news": 0.4, "property": 0.2}
    present = {k: v for k, v in parts.items() if v is not None and k in weights}
    if not present:
        return {"score": None, "confidence": None, "parts": dict(parts)}
    total = sum(weights[k] for k in present)
    score = sum(weights[k] * v for k, v in present.items()) / total
    confidence = {1: "low", 2: "medium"}.get(len(present), "high")
    return {"score": round(score, 1), "confidence": confidence, "parts": dict(parts)}


# --- proximity components ------------------------------------------------------


def medical_score(medical: Mapping[str, Any] | None) -> float | None:
    """Best emergency-capable hospital, judged on ambulance ETA (5 min -> 100, 30 min -> 0).

    Without an ETA, fall back to distance (1 km -> 100, 10 km -> 0) discounted 20%
    because straight-line distance understates peak-hour travel.
    """
    hospitals = [h for h in (medical or {}).get("hospitals", []) if h.get("emergency") is not False]
    if not hospitals:
        return None
    etas = [h["ambulance_est_min"] for h in hospitals if h.get("ambulance_est_min") is not None]
    if etas:
        return linear(min(etas), 5, 30)
    kms = [h["km"] for h in hospitals if h.get("km") is not None]
    s = linear(min(kms), 1, 10) if kms else None
    return None if s is None else round(s * 0.8, 1)


def commute_score(commute: Mapping[str, Any] | None) -> float | None:
    if not commute or commute.get("peak_min") is None:
        return None
    by_time = linear(commute["peak_min"], 20, 90)
    by_mult = linear(commute.get("multiplier", 1.0), 1.2, 4.0)
    return round(0.6 * by_time + 0.4 * by_mult, 1)


def nearest_km_score(item: Mapping[str, Any] | list | None, best: float, worst: float) -> float | None:
    if isinstance(item, list):
        kms = [i["km"] for i in item if i.get("km") is not None]
        km = min(kms) if kms else None
    else:
        km = (item or {}).get("km")
    return linear(km, best, worst)


# --- requirements matching -----------------------------------------------------


def hard_failures(listing: Mapping[str, Any], req: Mapping[str, Any], budget_tolerance: float = 0.05) -> list[str]:
    """Reasons a listing contradicts the requirements. Unknown fields never fail."""
    why: list[str] = []
    if req.get("furnishing") and listing.get("furnishing") and listing["furnishing"] != req["furnishing"]:
        why.append(f"furnishing is {listing['furnishing']}, wanted {req['furnishing']}")
    units = req.get("unit_types") or []
    if units and listing.get("unit_type") and listing["unit_type"] not in units:
        why.append(f"unit type {listing['unit_type']} not in {units}")
    ptypes = req.get("property_types") or []
    if ptypes and listing.get("property_type") and listing["property_type"] not in ptypes:
        why.append(f"property type {listing['property_type']} not in {ptypes}")
    cap = (req.get("budget") or {}).get("max")
    if cap and listing.get("rent") and listing["rent"] > cap * (1 + budget_tolerance):
        why.append(f"rent {listing['rent']} over budget {cap}")
    absent = set(listing.get("amenities_absent") or [])
    for key in (req.get("amenities") or {}).get("must", []):
        if key in absent:
            why.append(f"must-have '{key}' confirmed absent")
    baths = req.get("bathrooms_min")
    if baths and listing.get("bathrooms") is not None and listing["bathrooms"] < baths:
        why.append(f"{listing['bathrooms']} bathrooms, wanted {baths}+")
    max_age = req.get("property_age_max_years")
    if max_age is not None and listing.get("age_years") is not None and listing["age_years"] > max_age:
        why.append(f"{listing['age_years']} years old, wanted under {max_age}")
    return why


def amenity_match(listing: Mapping[str, Any], req: Mapping[str, Any]) -> dict[str, Any]:
    have = set(listing.get("amenities") or [])
    absent = set(listing.get("amenities_absent") or [])
    wanted = req.get("amenities") or {}
    must, nice = wanted.get("must", []), wanted.get("nice", [])
    unverified_must = [k for k in must if k not in have and k not in absent]
    nice_hit = [k for k in nice if k in have]
    return {
        "must_confirmed": [k for k in must if k in have],
        "must_unverified": unverified_must,
        "nice_hit": nice_hit,
        "nice_missing": [k for k in nice if k not in have],
        "score": round(100 * len(nice_hit) / len(nice), 1) if nice else None,
    }


# --- ranking --------------------------------------------------------------------


def score_listing(listing: Mapping[str, Any], req: Mapping[str, Any], weights: Weights) -> dict[str, Any]:
    enr = listing.get("enrichment") or {}
    am = amenity_match(listing, req)
    parts: dict[str, float | None] = {
        "safety": (enr.get("safety") or {}).get("score"),
        "medical": medical_score(enr.get("medical")),
        "commute": commute_score(enr.get("commute")),
        "amenities": am["score"],
        "metro": nearest_km_score(enr.get("metro"), 0.5, 5.0),
        "entertainment": nearest_km_score(enr.get("malls"), 1.0, 10.0),
    }
    w = weights.as_dict()
    live = {k: v for k, v in parts.items() if v is not None and w[k] > 0}
    total_w = sum(w[k] for k in live)
    overall = round(sum(w[k] * v for k, v in live.items()) / total_w, 1) if total_w else None
    coverage = round(total_w / sum(w.values()), 2) if sum(w.values()) else 0.0
    # Shrink toward a neutral 50 when little was measured, so a home we know
    # little about cannot outrank one we checked thoroughly on thin evidence.
    adjusted = None if overall is None else round(overall * coverage + NEUTRAL * (1 - coverage), 1)
    return {
        "overall": overall,
        "adjusted": adjusted,
        **parts,
        "coverage": coverage,
        "confidence": "high" if coverage >= 0.8 else "medium" if coverage >= 0.5 else "low",
        "amenity_match": am,
    }


def rank(
    listings: list[Mapping[str, Any]],
    req: Mapping[str, Any],
    weights: Weights | None = None,
    sort_by: str = "overall",
    hide_waterlogged: bool = False,
) -> dict[str, Any]:
    if sort_by != "overall" and sort_by not in COMPONENTS:
        raise ValueError(f"sort_by must be 'overall' or one of {COMPONENTS}")
    weights = weights or Weights.load()
    ranked, excluded = [], []
    for lst in listings:
        reasons = hard_failures(lst, req)
        wl = ((lst.get("enrichment") or {}).get("waterlogging") or {}).get("warning")
        if hide_waterlogged and wl:
            reasons.append("area flagged for waterlogging (hidden by request)")
        if reasons:
            excluded.append({"id": lst.get("id"), "title": lst.get("title"), "reasons": reasons})
            continue
        ranked.append({**lst, "scores": score_listing(lst, req, weights)})

    sort_field = "adjusted" if sort_by == "overall" else sort_by

    def key(item: Mapping[str, Any]) -> tuple[int, float, float]:
        s = item["scores"].get(sort_field)
        return (0 if s is not None else 1, -(s or 0.0), item.get("rent") or math.inf)

    ranked.sort(key=key)
    for i, item in enumerate(ranked, 1):
        item["rank"] = i
    return {"sort_by": sort_by, "weights": weights.as_dict(), "ranked": ranked, "excluded": excluded}
