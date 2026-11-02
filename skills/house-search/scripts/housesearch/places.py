"""Nearby hospitals, malls, metro stations and police stations via OpenStreetMap.

Overpass needs no API key. OSM coverage in India is good for hospitals, metro
stations and malls, patchier for small clinics, so results are candidates the
agent still verifies (for hospitals: is there a 24x7 emergency department?).
"""

from __future__ import annotations

from typing import Any

from .geo import haversine_km
from .http import HttpError, Transport, request_json

# Primary + public mirrors (tried in order when the first is slow or down).
OVERPASS_ENDPOINTS: tuple[str, ...] = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.fr/api/interpreter",
)
OVERPASS = OVERPASS_ENDPOINTS[0]

KINDS: dict[str, list[str]] = {
    "hospital": ['["amenity"="hospital"]'],
    "mall": ['["shop"="mall"]'],
    "metro": ['["station"="subway"]', '["railway"="station"]["subway"="yes"]'],
    "police": ['["amenity"="police"]'],
    "cinema": ['["amenity"="cinema"]'],
}

KEPT_TAGS = ("emergency", "operator", "healthcare:speciality", "opening_hours", "phone", "network", "website")


def build_query(lat: float, lon: float, kinds: list[str], radius_m: int) -> str:
    unknown = [k for k in kinds if k not in KINDS]
    if unknown:
        raise ValueError(f"Unknown kinds {unknown}; choose from {sorted(KINDS)}")
    clauses = [f"nwr{sel}(around:{radius_m},{lat},{lon});" for k in kinds for sel in KINDS[k]]
    return "[out:json][timeout:45];(" + "".join(clauses) + ");out center tags;"


def query_overpass(
    lat: float,
    lon: float,
    kinds: list[str],
    radius_m: int,
    transport: Transport | None = None,
) -> tuple[dict, str]:
    """Run Overpass and return (raw JSON, endpoint URL used)."""
    query = build_query(lat, lon, kinds, radius_m)
    endpoints = (OVERPASS,) if transport is not None else OVERPASS_ENDPOINTS
    last: HttpError | None = None
    for url in endpoints:
        try:
            data = request_json(
                url,
                form={"data": query},
                transport=transport,
                timeout=60.0,
                retries=1,
            )
            if not isinstance(data, dict):
                raise HttpError(f"Unexpected Overpass payload from {url}")
            return data, url
        except HttpError as exc:
            last = exc
            if transport is not None:
                raise
    msg = str(last) if last else "no Overpass endpoint responded"
    raise RuntimeError(f"OpenStreetMap Overpass unavailable after {len(endpoints)} mirror(s): {msg}") from last


def _kind_of(tags: dict[str, str], kinds: list[str]) -> str | None:
    if tags.get("amenity") == "hospital":
        return "hospital"
    if tags.get("shop") == "mall":
        return "mall"
    if tags.get("station") == "subway" or tags.get("subway") == "yes":
        return "metro"
    if tags.get("amenity") == "police":
        return "police"
    if tags.get("amenity") == "cinema":
        return "cinema"
    return None


def parse_elements(elements: list[dict[str, Any]], lat: float, lon: float, kinds: list[str]) -> dict[str, list[dict]]:
    """Group Overpass elements by kind, nearest first, de-duplicated by name."""
    out: dict[str, list[dict]] = {k: [] for k in kinds}
    seen: set[tuple[str, str]] = set()
    for el in elements:
        tags = el.get("tags") or {}
        name = tags.get("name")
        kind = _kind_of(tags, kinds)
        if not name or kind not in out:
            continue
        c = el.get("center") or el
        if "lat" not in c or "lon" not in c:
            continue
        if (kind, name.casefold()) in seen:  # OSM often maps one site as node + way
            continue
        seen.add((kind, name.casefold()))
        out[kind].append(
            {
                "name": name,
                "kind": kind,
                "lat": c["lat"],
                "lon": c["lon"],
                "km": round(haversine_km(lat, lon, c["lat"], c["lon"]), 2),
                "tags": {t: tags[t] for t in KEPT_TAGS if t in tags},
            }
        )
    for items in out.values():
        items.sort(key=lambda i: i["km"])
    return out


def nearby(
    lat: float,
    lon: float,
    kinds: list[str],
    radius_m: int = 5000,
    limit: int = 5,
    transport: Transport | None = None,
) -> dict[str, list[dict]]:
    """Return the `limit` nearest places per kind within `radius_m` metres.

    `km` is straight-line distance, not road distance; use traffic.py for
    drive times.
    """
    data, endpoint = query_overpass(lat, lon, kinds, radius_m, transport)
    grouped = parse_elements(data.get("elements", []), lat, lon, kinds)
    trimmed = {k: v[:limit] for k, v in grouped.items()}
    trimmed["_meta"] = {"overpass_endpoint": endpoint, "element_count": len(data.get("elements", []))}
    return trimmed
