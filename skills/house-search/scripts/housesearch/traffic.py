"""Traffic-aware drive times and ambulance estimates (Google Routes API).

One call returns both the traffic-aware duration at a chosen departure time and
the free-flow ("static") duration, so the ratio is the congestion multiplier:
1.0x is an empty road, 3x means the trip takes three times as long.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .http import Transport, request_json

ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
FIELD_MASK = "routes.duration,routes.staticDuration,routes.distanceMeters"

# Assumption, not a measurement: sirens and lane-clearing shave time off a
# car's journey. Always reported as an estimate next to the car figure.
DEFAULT_SIREN_FACTOR = 0.7

# (upper bound of multiplier, label). Order matters.
CONGESTION_BANDS = [
    (1.3, "normal"),
    (2.0, "busy (up to 2x)"),
    (3.0, "heavy (2-3x)"),
    (4.0, "very heavy (3-4x)"),
]
CONGESTION_MAX_LABEL = "severe (4x+)"

_WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class MissingKeyError(RuntimeError):
    """GOOGLE_MAPS_API_KEY is not set."""


@dataclass(frozen=True)
class RouteTimes:
    distance_km: float
    free_flow_min: float
    traffic_min: float
    multiplier: float
    label: str
    depart_at: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_duration(value: str) -> float:
    """Google durations look like '1234s' or '1234.5s'. Returns seconds."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)s\s*", value)
    if not m:
        raise ValueError(f"Unrecognised duration {value!r}")
    return float(m.group(1))


def classify(multiplier: float) -> str:
    for upper, label in CONGESTION_BANDS:
        if multiplier < upper:
            return label
    return CONGESTION_MAX_LABEL


def departure_datetime(spec: str, tz: str = "Asia/Kolkata", now: datetime | None = None) -> datetime:
    """Next occurrence of 'HH:MM' or 'Mon 09:00', strictly in the future.

    Google only gives forecast traffic for future departures, so a past time
    is rolled forward to the next matching day.
    """
    m = re.fullmatch(r"\s*(?:([A-Za-z]{3})[a-z]*\s+)?(\d{1,2}):(\d{2})\s*", spec)
    if not m:
        raise ValueError(f"Expected 'HH:MM' or 'Mon HH:MM', got {spec!r}")
    day, hh, mm = m.group(1), int(m.group(2)), int(m.group(3))
    if not (0 <= hh < 24 and 0 <= mm < 60):
        raise ValueError(f"Invalid time in {spec!r}")
    zone = ZoneInfo(tz)
    now = (now or datetime.now(zone)).astimezone(zone)
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if day:
        if day.lower() not in _WEEKDAYS:
            raise ValueError(f"Unknown weekday {day!r}")
        target += timedelta(days=(_WEEKDAYS.index(day.lower()) - target.weekday()) % 7)
        if target <= now:
            target += timedelta(days=7)
    elif target <= now:
        target += timedelta(days=1)
    return target


def route_times(
    origin: tuple[float, float],
    dest: tuple[float, float],
    depart_at: datetime,
    *,
    transport: Transport | None = None,
) -> RouteTimes:
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        raise MissingKeyError(
            "GOOGLE_MAPS_API_KEY is not set. Traffic multipliers need the Google Routes API; "
            "see references/step-4-enrich.md for the manual Google Maps fallback."
        )

    def wp(p: tuple[float, float]) -> dict:
        return {"location": {"latLng": {"latitude": p[0], "longitude": p[1]}}}

    body = {
        "origin": wp(origin),
        "destination": wp(dest),
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
        "departureTime": depart_at.isoformat(),
    }
    data = request_json(
        ROUTES_URL,
        json_body=body,
        headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": FIELD_MASK},
        transport=transport,
    )
    routes = data.get("routes") or []
    if not routes:
        raise RuntimeError("Routes API returned no route between these points")
    r = routes[0]
    traffic_s = parse_duration(r["duration"])
    free_s = parse_duration(r["staticDuration"])
    mult = traffic_s / free_s if free_s else 1.0
    return RouteTimes(
        distance_km=round(r.get("distanceMeters", 0) / 1000, 2),
        free_flow_min=round(free_s / 60, 1),
        traffic_min=round(traffic_s / 60, 1),
        multiplier=round(mult, 2),
        label=classify(mult),
        depart_at=depart_at.isoformat(),
    )


def worst_of(times: list[RouteTimes]) -> RouteTimes:
    """The slowest sample: 'full traffic' means the worst slot we looked at."""
    return max(times, key=lambda t: t.traffic_min)


def ambulance_estimate(route: RouteTimes, siren_factor: float = DEFAULT_SIREN_FACTOR) -> dict[str, Any]:
    """Wrap a hospital -> home route as an ambulance figure.

    `peak_drive_min` is the car time (conservative upper bound). The ambulance
    estimate applies `siren_factor`, an assumption, never below free-flow time.
    """
    est = max(route.free_flow_min, route.traffic_min * siren_factor)
    return {
        "peak_drive_min": route.traffic_min,
        "free_flow_min": route.free_flow_min,
        "ambulance_est_min": round(est, 1),
        "multiplier": route.multiplier,
        "label": route.label,
        "assumption": f"siren factor {siren_factor} applied to peak drive time; dispatch delay not included",
    }


# Leave-home slots a typical weekday morning commute spans.
DEFAULT_PROFILE_TIMES = ["Mon 07:30", "Mon 08:15", "Mon 09:00", "Mon 09:45", "Mon 10:30"]


def summarize_profile(samples: list[RouteTimes]) -> dict[str, Any]:
    """Turn samples at different departure times into a time-of-day profile.

    Google's Routes API gives the *typical* traffic for a future departure
    time, not a history. Sampling several times shows how the trip changes
    through the morning and what leaving earlier or later would save.
    """
    if not samples:
        raise ValueError("no samples")
    ordered = sorted(samples, key=lambda t: t.depart_at)
    best = min(ordered, key=lambda t: t.traffic_min)
    worst = worst_of(ordered)
    return {
        "slots": [
            {"depart_at": t.depart_at, "traffic_min": t.traffic_min, "multiplier": t.multiplier, "label": t.label}
            for t in ordered
        ],
        "best_slot": best.depart_at,
        "worst_slot": worst.depart_at,
        "free_flow_min": min(t.free_flow_min for t in ordered),
        "minutes_saved_by_best_slot": round(worst.traffic_min - best.traffic_min, 1),
        "basis": "typical traffic for each departure time (Google Routes API forecast), not observed history",
    }


def commute_profile(
    origin: tuple[float, float],
    dest: tuple[float, float],
    specs: list[str] | None = None,
    tz: str = "Asia/Kolkata",
    transport: Transport | None = None,
) -> dict[str, Any]:
    samples = [route_times(origin, dest, departure_datetime(s, tz), transport=transport) for s in (specs or DEFAULT_PROFILE_TIMES)]
    return summarize_profile(samples)
