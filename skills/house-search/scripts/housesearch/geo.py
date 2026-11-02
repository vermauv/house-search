"""Geocoding and distance helpers.

Uses the Google Geocoding API when GOOGLE_MAPS_API_KEY is set, otherwise
OpenStreetMap Nominatim (no key, 1 request/second policy).
"""

from __future__ import annotations

import math
import os
import time
from dataclasses import asdict, dataclass
from typing import Any

from .http import Transport, request_json

GOOGLE_GEOCODE = "https://maps.googleapis.com/maps/api/geocode/json"
NOMINATIM = "https://nominatim.openstreetmap.org/search"

# Two candidates further apart than this mean the query is ambiguous and the
# user should pick (e.g. two localities with the same name in different cities).
AMBIGUITY_KM = 3.0

_last_nominatim_call = 0.0


@dataclass(frozen=True)
class Place:
    name: str
    lat: float
    lon: float
    source: str  # "google" | "nominatim"
    kind: str = ""
    bbox: tuple[float, float, float, float] | None = None  # south, north, west, east

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(a))


def _google(query: str, region: str, key: str, transport: Transport | None) -> list[Place]:
    data = request_json(
        GOOGLE_GEOCODE,
        params={"address": query, "region": region, "key": key},
        transport=transport,
    )
    status = data.get("status")
    if status == "ZERO_RESULTS":
        return []
    if status != "OK":
        raise RuntimeError(f"Google Geocoding returned {status}: {data.get('error_message', '')}")
    places = []
    for r in data["results"]:
        loc = r["geometry"]["location"]
        vp = r["geometry"].get("bounds") or r["geometry"].get("viewport")
        bbox = (
            (vp["southwest"]["lat"], vp["northeast"]["lat"], vp["southwest"]["lng"], vp["northeast"]["lng"])
            if vp
            else None
        )
        places.append(
            Place(r["formatted_address"], loc["lat"], loc["lng"], "google", (r.get("types") or [""])[0], bbox)
        )
    return places


def _nominatim(query: str, region: str, transport: Transport | None) -> list[Place]:
    global _last_nominatim_call
    wait = 1.0 - (time.monotonic() - _last_nominatim_call)
    if wait > 0 and transport is None:  # only throttle real traffic
        time.sleep(wait)
    data = request_json(
        NOMINATIM,
        params={"q": query, "format": "jsonv2", "limit": 5, "countrycodes": region, "addressdetails": 0},
        transport=transport,
    )
    _last_nominatim_call = time.monotonic()
    places = []
    for r in data:
        bb = r.get("boundingbox")
        bbox = (float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])) if bb else None
        places.append(Place(r["display_name"], float(r["lat"]), float(r["lon"]), "nominatim", r.get("type", ""), bbox))
    return places


def geocode(query: str, *, region: str = "in", transport: Transport | None = None) -> dict[str, Any]:
    """Resolve a free-text locality or address.

    Returns {"candidates": [...], "ambiguous": bool}. When `ambiguous` is true the
    agent must ask the user which candidate they meant instead of guessing.
    """
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    places = _google(query, region, key, transport) if key else _nominatim(query, region, transport)
    ambiguous = len(places) > 1 and any(
        haversine_km(places[0].lat, places[0].lon, p.lat, p.lon) > AMBIGUITY_KM for p in places[1:]
    )
    return {
        "query": query,
        "provider": "google" if key else "nominatim",
        "ambiguous": ambiguous,
        "candidates": [p.as_dict() for p in places],
    }
