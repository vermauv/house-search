#!/usr/bin/env python3
"""Command-line entry point for the /house-search skill helpers.

Every subcommand prints JSON to stdout (report writes files) and exits non-zero
with a JSON error on failure, so the agent can parse results reliably.

  hs.py normalize --text "2bhk semi furnished flat near mahadevapura, gym, pets"
  hs.py geocode "Mahadevapura, Bengaluru"
  hs.py nearby --lat 12.99 --lon 77.69 --kinds hospital,metro,mall
  hs.py traffic --origin 12.99,77.69 --dest 12.97,77.75 --depart "Mon 09:00"
  hs.py ambulance --home 12.99,77.69 --hospital 12.98,77.70 --depart "Mon 19:00"
  hs.py profile --origin 12.99,77.69 --dest 12.97,77.75 [--depart "Mon 08:00" ...]
  hs.py waterlog --locality Marathahalli --city Bengaluru [--findings f.json]
  hs.py safety-news --incidents incidents.json
  hs.py safety-trend --incidents incidents.json
  hs.py rank --listings listings.json --requirements req.json [--sort safety]
  hs.py report --ranked ranked.json --requirements req.json --out-dir house-search-output
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from housesearch import geo, places, report, scoring, traffic, trends, vocab, waterlog  # noqa: E402


def _latlon(value: str) -> tuple[float, float]:
    try:
        lat, lon = (float(x) for x in value.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected 'lat,lon', got {value!r}") from None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise argparse.ArgumentTypeError(f"coordinates out of range: {value!r}")
    return lat, lon


def _load(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _emit(data: Any) -> int:
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def cmd_normalize(a: argparse.Namespace) -> int:
    if a.text:
        return _emit(vocab.parse_text(a.text))
    return _emit(vocab.normalize_requirements(_load(a.json)))


def cmd_geocode(a: argparse.Namespace) -> int:
    return _emit(geo.geocode(a.query, region=a.region))


def cmd_nearby(a: argparse.Namespace) -> int:
    kinds = [k.strip() for k in a.kinds.split(",") if k.strip()]
    raw, endpoint = places.query_overpass(a.lat, a.lon, kinds, a.radius)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    grouped = places.parse_elements(raw.get("elements", []), a.lat, a.lon, kinds)
    payload = {k: v[: a.limit] for k, v in grouped.items()}
    payload["_meta"] = {"overpass_endpoint": endpoint, "element_count": len(raw.get("elements", []))}
    if a.out:
        payload["_meta"]["raw_path"] = str(Path(a.out).resolve())
    return _emit(payload)


def cmd_traffic(a: argparse.Namespace) -> int:
    when = traffic.departure_datetime(a.depart, a.tz)
    return _emit(traffic.route_times(a.origin, a.dest, when).as_dict())


def cmd_profile(a: argparse.Namespace) -> int:
    return _emit(traffic.commute_profile(a.origin, a.dest, a.depart, a.tz))


def cmd_safety_trend(a: argparse.Namespace) -> int:
    return _emit(trends.incident_trend(_load(a.incidents)))


def cmd_ambulance(a: argparse.Namespace) -> int:
    """Ambulance travels hospital -> home. Samples several slots and keeps the worst."""
    slots = a.depart or ["Mon 08:45", "Mon 19:00"]
    samples = [traffic.route_times(a.hospital, a.home, traffic.departure_datetime(s, a.tz)) for s in slots]
    worst = traffic.worst_of(samples)
    return _emit({**traffic.ambulance_estimate(worst, a.siren_factor), "slots_sampled": slots, "worst_slot": worst.depart_at})


def cmd_waterlog(a: argparse.Namespace) -> int:
    findings = _load(a.findings) if a.findings else None
    return _emit(waterlog.check(a.locality, a.city, findings))


def cmd_safety_news(a: argparse.Namespace) -> int:
    score = scoring.news_safety_score(_load(a.incidents), k=a.k)
    return _emit({"score": score, "k": a.k})


def cmd_rank(a: argparse.Namespace) -> int:
    weights = scoring.Weights.load(Path(a.weights)) if a.weights else scoring.Weights.load()
    listings = _load(a.listings)
    if isinstance(listings, dict):  # accept the {"sources": [...], "listings": [...]} wrapper
        listings = listings["listings"]
    result = scoring.rank(listings, _load(a.requirements), weights, a.sort, a.hide_waterlogged)
    if a.out:
        Path(a.out).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return _emit(result)


def cmd_report(a: argparse.Namespace) -> int:
    result, req = _load(a.ranked), _load(a.requirements)
    meta = {"locality": a.locality or req.get("locality", "results"), "query": a.query or req.get("original_text", ""), "as_of": date.today().isoformat(), "assumptions": req.get("assumptions", [])}
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.md").write_text(report.render_markdown(result, req, meta), encoding="utf-8")
    (out / "report.html").write_text(report.render_html(result, req, meta), encoding="utf-8")
    return _emit({"markdown": str(out / "report.md"), "html": str(out / "report.html"), "listings": len(result["ranked"])})


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hs.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("normalize", help="canonicalise requirements from text or agent-proposed JSON")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--text")
    g.add_argument("--json")
    s.set_defaults(fn=cmd_normalize)

    s = sub.add_parser("geocode", help="resolve a locality or address")
    s.add_argument("query")
    s.add_argument("--region", default="in", help="country code bias (default: in)")
    s.set_defaults(fn=cmd_geocode)

    s = sub.add_parser("nearby", help="hospitals, metro, malls, police near a point (OpenStreetMap)")
    s.add_argument("--lat", type=float, required=True)
    s.add_argument("--lon", type=float, required=True)
    s.add_argument("--kinds", default="hospital,metro,mall", help=f"comma list of {sorted(places.KINDS)}")
    s.add_argument("--radius", type=int, default=5000, help="metres")
    s.add_argument("--limit", type=int, default=5)
    s.add_argument("--out", help="optional path to write raw Overpass JSON (for debugging or re-parse)")
    s.set_defaults(fn=cmd_nearby)

    s = sub.add_parser("traffic", help="traffic multiplier for a trip at a departure time (needs GOOGLE_MAPS_API_KEY)")
    s.add_argument("--origin", type=_latlon, required=True)
    s.add_argument("--dest", type=_latlon, required=True)
    s.add_argument("--depart", required=True, help="'HH:MM' or 'Mon HH:MM', next occurrence")
    s.add_argument("--tz", default="Asia/Kolkata")
    s.set_defaults(fn=cmd_traffic)

    s = sub.add_parser("profile", help="traffic by departure time, to see what leaving earlier or later changes (needs GOOGLE_MAPS_API_KEY)")
    s.add_argument("--origin", type=_latlon, required=True)
    s.add_argument("--dest", type=_latlon, required=True)
    s.add_argument("--depart", action="append", help="repeatable; default Mon 07:30 to 10:30 in 45-minute steps")
    s.add_argument("--tz", default="Asia/Kolkata")
    s.set_defaults(fn=cmd_profile)

    s = sub.add_parser("ambulance", help="hospital -> home estimate in worst sampled traffic (needs GOOGLE_MAPS_API_KEY)")
    s.add_argument("--home", type=_latlon, required=True)
    s.add_argument("--hospital", type=_latlon, required=True)
    s.add_argument("--depart", action="append", help="repeatable; default Mon 08:45 and Mon 19:00")
    s.add_argument("--tz", default="Asia/Kolkata")
    s.add_argument("--siren-factor", type=float, default=traffic.DEFAULT_SIREN_FACTOR)
    s.set_defaults(fn=cmd_ambulance)

    s = sub.add_parser("waterlog", help="waterlogging flag for a locality")
    s.add_argument("--locality", required=True)
    s.add_argument("--city", required=True)
    s.add_argument("--findings", help="JSON list of live news findings")
    s.set_defaults(fn=cmd_waterlog)

    s = sub.add_parser("safety-news", help="news-incident safety score from a JSON list of incidents")
    s.add_argument("--incidents", required=True)
    s.add_argument("--k", type=float, default=8.0)
    s.set_defaults(fn=cmd_safety_news)

    s = sub.add_parser("safety-trend", help="year-by-year incident trend from a JSON list of incidents")
    s.add_argument("--incidents", required=True)
    s.set_defaults(fn=cmd_safety_trend)

    s = sub.add_parser("rank", help="filter, score and sort enriched listings")
    s.add_argument("--listings", required=True)
    s.add_argument("--requirements", required=True)
    s.add_argument("--weights")
    s.add_argument("--sort", default="overall", choices=["overall", *scoring.COMPONENTS])
    s.add_argument("--hide-waterlogged", action="store_true")
    s.add_argument("--out")
    s.set_defaults(fn=cmd_rank)

    s = sub.add_parser("report", help="write report.md and report.html")
    s.add_argument("--ranked", required=True)
    s.add_argument("--requirements", required=True)
    s.add_argument("--out-dir", default="house-search-output")
    s.add_argument("--locality")
    s.add_argument("--query")
    s.set_defaults(fn=cmd_report)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fn: Callable[[argparse.Namespace], int] = args.fn
    try:
        return fn(args)
    except BrokenPipeError:  # e.g. piped into `head`; the reader left, not an error
        return 0
    except (traffic.MissingKeyError, RuntimeError, ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        json.dump({"error": type(exc).__name__, "message": str(exc)}, sys.stdout)
        sys.stdout.write("\n")
        return 3 if isinstance(exc, traffic.MissingKeyError) else 1


if __name__ == "__main__":
    raise SystemExit(main())
