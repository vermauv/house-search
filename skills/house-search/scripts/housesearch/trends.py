"""Year-by-year trends for safety incidents.

Only describes what the dated, sourced incidents show. With too few incidents
it says `insufficient_data` instead of inventing a direction.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from .scoring import SEVERITY_WEIGHT, _parse_date

MIN_INCIDENTS = 4
CAVEAT = (
    "Built from incidents that made the news or published data; reporting volume changes "
    "with media attention, so treat the direction as a hint, not a measurement."
)


def incident_trend(
    incidents: list[Mapping[str, Any]],
    today: date | None = None,
    min_incidents: int = MIN_INCIDENTS,
) -> dict[str, Any]:
    """Compare the last 12 months with the 12 before, and list counts per year.

    `direction` is improving / steady / worsening (by severity-weighted load) or
    insufficient_data when fewer than `min_incidents` dated incidents exist.
    """
    today = today or date.today()
    by_year: dict[int, dict[str, float]] = {}
    recent = prior = 0.0
    for inc in incidents:
        when = _parse_date(inc["date"])
        weight = SEVERITY_WEIGHT[inc["severity"]]
        slot = by_year.setdefault(when.year, {"count": 0, "load": 0.0})
        slot["count"] += 1
        slot["load"] += weight
        age = (today - when).days
        if 0 <= age <= 365:
            recent += weight
        elif 365 < age <= 730:
            prior += weight

    if len(incidents) < min_incidents:
        direction = "insufficient_data"
    else:
        delta = recent - prior
        threshold = max(1.0, 0.25 * max(recent, prior))
        direction = "improving" if delta < -threshold else "worsening" if delta > threshold else "steady"

    return {
        "direction": direction,
        "recent_12m_load": round(recent, 1),
        "prior_12m_load": round(prior, 1),
        "by_year": [{"year": y, "count": int(v["count"]), "load": round(v["load"], 1)} for y, v in sorted(by_year.items())],
        "incidents_used": len(incidents),
        "caveat": CAVEAT,
    }
