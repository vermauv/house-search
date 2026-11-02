"""Waterlogging risk flags.

Two inputs are merged:
  1. assets/waterlogging-seed.json, a small curated list of areas that public
     reporting has repeatedly linked to waterlogging. A starting point only.
  2. `findings` the agent collected live from news / civic sources for this run.

Absence of reports is never reported as "safe": the status is `none_found`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SEED_PATH = Path(__file__).resolve().parents[2] / "assets" / "waterlogging-seed.json"

WARNING_ICON = "⚠️"

STATUS_FREQUENT = "frequent"
STATUS_REPORTED = "reported"
STATUS_NONE = "none_found"

# Distinct calendar years with an incident before an area counts as "frequent".
FREQUENT_YEARS = 2


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def load_seed(path: Path = SEED_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _names(entry: dict[str, Any]) -> list[str]:
    return [_slug(n) for n in [entry["area"], *entry.get("aliases", [])]]


def _matches(locality: str, names: list[str]) -> bool:
    loc = _slug(locality)
    return bool(loc) and any(n == loc or f" {n} " in f" {loc} " or f" {loc} " in f" {n} " for n in names)


def check(
    locality: str,
    city: str,
    findings: list[dict[str, Any]] | None = None,
    seed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a risk record for one locality.

    `findings` items: {"area", "date" (YYYY-MM-DD or YYYY), "source_url", "note"?, "official_list"?}
    Only findings whose `area` matches `locality` are used.
    """
    seed = seed if seed is not None else load_seed()
    evidence: list[dict[str, Any]] = []

    for entry in seed.get("cities", {}).get(_slug(city), []):
        if _matches(locality, _names(entry)):
            evidence.append({**{k: entry[k] for k in ("area", "note") if k in entry}, "source_url": entry["source_url"], "date": entry.get("date"), "origin": "seed", "official_list": entry.get("official_list", False)})

    for f in findings or []:
        if _matches(locality, [_slug(f["area"])]):
            evidence.append({**f, "origin": "live"})

    years = {str(e["date"])[:4] for e in evidence if e.get("date")}
    by_year: dict[str, int] = {}
    for e in evidence:
        if e.get("date"):
            by_year[str(e["date"])[:4]] = by_year.get(str(e["date"])[:4], 0) + 1
    official = any(e.get("official_list") for e in evidence)
    if official or len(years) >= FREQUENT_YEARS:
        status = STATUS_FREQUENT
    elif evidence:
        status = STATUS_REPORTED
    else:
        status = STATUS_NONE

    return {
        "locality": locality,
        "city": city,
        "status": status,
        "warning": status in (STATUS_FREQUENT, STATUS_REPORTED),
        "icon": WARNING_ICON if status in (STATUS_FREQUENT, STATUS_REPORTED) else "",
        "evidence": evidence,
        "reports_by_year": dict(sorted(by_year.items())),
        "undated_reports": sum(1 for e in evidence if not e.get("date")),
        "note": "No reports found is not a guarantee: check the specific street and ground floor with residents."
        if status == STATUS_NONE
        else "",
    }
