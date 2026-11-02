import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from housesearch import traffic, waterlog

IST = ZoneInfo("Asia/Kolkata")
NOW = datetime(2026, 10, 30, 11, 0, tzinfo=IST)  # a Friday


def routes_payload(traffic_s, static_s, meters=8000):
    return {"routes": [{"duration": f"{traffic_s}s", "staticDuration": f"{static_s}s", "distanceMeters": meters}]}


def fake(payload, seen=None):
    def transport(req, timeout):
        if seen is not None:
            seen.append(req)
        return json.dumps(payload).encode()
    return transport


@pytest.mark.parametrize("m,label", [(1.0, "normal"), (1.5, "busy (up to 2x)"), (2.5, "heavy (2-3x)"), (3.5, "very heavy (3-4x)"), (4.0, "severe (4x+)"), (6, "severe (4x+)")])
def test_classify(m, label):
    assert traffic.classify(m) == label


def test_parse_duration():
    assert traffic.parse_duration("1234s") == 1234.0
    assert traffic.parse_duration("12.5s") == 12.5
    with pytest.raises(ValueError):
        traffic.parse_duration("12 min")


def test_departure_rolls_forward_and_is_always_future():
    assert traffic.departure_datetime("09:00", now=NOW) == datetime(2026, 10, 31, 9, 0, tzinfo=IST)  # already past today
    assert traffic.departure_datetime("18:00", now=NOW) == datetime(2026, 10, 30, 18, 0, tzinfo=IST)
    mon = traffic.departure_datetime("Mon 09:00", now=NOW)
    assert mon == datetime(2026, 11, 2, 9, 0, tzinfo=IST) and mon.weekday() == 0
    # same weekday but time already passed -> next week
    assert traffic.departure_datetime("Fri 08:00", now=NOW) == datetime(2026, 11, 6, 8, 0, tzinfo=IST)
    for bad in ("9am", "25:00", "Foo 09:00"):
        with pytest.raises(ValueError):
            traffic.departure_datetime(bad, now=NOW)


def test_route_times_computes_multiplier_and_sends_key_in_header(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "k")
    seen = []
    r = traffic.route_times((12.99, 77.69), (12.97, 77.75), NOW, transport=fake(routes_payload(3600, 1200), seen))
    assert (r.free_flow_min, r.traffic_min, r.multiplier, r.label, r.distance_km) == (20.0, 60.0, 3.0, "very heavy (3-4x)", 8.0)
    assert seen[0].headers["X-goog-api-key"] == "k" and "k" not in seen[0].full_url


def test_route_times_without_key_explains_the_fallback(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    with pytest.raises(traffic.MissingKeyError, match="step-4-enrich"):
        traffic.route_times((1, 1), (2, 2), NOW)


def test_ambulance_estimate_never_beats_free_flow():
    slow = traffic.RouteTimes(5, 10.0, 40.0, 4.0, "severe (4x+)", "t")
    e = traffic.ambulance_estimate(slow)
    assert e["peak_drive_min"] == 40.0 and e["ambulance_est_min"] == 28.0 and "assumption" in e
    quiet = traffic.RouteTimes(5, 10.0, 11.0, 1.1, "normal", "t")
    assert traffic.ambulance_estimate(quiet)["ambulance_est_min"] == 10.0  # floor at free flow
    assert traffic.worst_of([quiet, slow]) is slow


# --- waterlogging -------------------------------------------------------------

SEED = {"cities": {"bengaluru": [
    {"area": "Varthur", "aliases": ["Varthur Road"], "date": "2026-06-21", "note": "n", "source_url": "https://e/1"},
    {"area": "Old Spot", "date": "2020-06-05", "note": "n", "source_url": "https://e/2", "official_list": True},
]}}


def test_seed_hit_with_one_report_is_reported_not_frequent():
    r = waterlog.check("Varthur Road", "Bengaluru", seed=SEED)
    assert r["status"] == "reported" and r["warning"] and r["icon"] == waterlog.WARNING_ICON


def test_two_distinct_years_make_it_frequent():
    live = [{"area": "Varthur", "date": "2024-09-01", "source_url": "https://e/3", "note": "again"}]
    assert waterlog.check("Varthur", "Bengaluru", live, SEED)["status"] == "frequent"


def test_official_list_alone_is_frequent():
    assert waterlog.check("Old Spot", "Bengaluru", seed=SEED)["status"] == "frequent"


def test_no_reports_is_not_called_safe():
    r = waterlog.check("Indiranagar", "Bengaluru", seed=SEED)
    assert r["status"] == "none_found" and not r["warning"] and r["icon"] == "" and "not a guarantee" in r["note"]


def test_matching_is_whole_word_not_substring():
    assert waterlog.check("Varthuri Colony", "Bengaluru", seed=SEED)["status"] == "none_found"
    assert waterlog.check("Near Varthur Road, Bengaluru", "Bengaluru", seed=SEED)["warning"]


def test_unknown_city_has_no_seed_but_live_findings_still_count():
    live = [{"area": "Anytown", "date": "2025-07-01", "source_url": "https://e/9"}]
    assert waterlog.check("Anytown", "Nowhere", live, SEED)["status"] == "reported"


def test_shipped_seed_is_well_formed():
    seed = waterlog.load_seed()
    for city, entries in seed["cities"].items():
        for e in entries:
            assert e["area"] and e["source_url"].startswith("https://"), (city, e)


# --- commute profile, trends ---------------------------------------------------

def test_commute_profile_shows_what_leaving_earlier_saves(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "k")
    durations = iter([1500, 2400, 3300, 2700, 1800])  # seconds, one per slot; free flow 1200

    def transport(req, timeout):
        return json.dumps(routes_payload(next(durations), 1200)).encode()

    prof = traffic.commute_profile((12.99, 77.69), (12.97, 77.75), transport=transport)
    assert len(prof["slots"]) == 5
    assert prof["minutes_saved_by_best_slot"] == 30.0  # 55 min worst vs 25 min best
    assert prof["best_slot"] < prof["worst_slot"]  # earliest slot is best, 09:00 worst
    assert "not observed history" in prof["basis"]


def test_summarize_profile_rejects_empty():
    with pytest.raises(ValueError):
        traffic.summarize_profile([])


def test_waterlog_reports_by_year_and_counts_undated():
    live = [{"area": "Varthur", "date": "2024-09-01", "source_url": "https://e/3"}, {"area": "Varthur", "source_url": "https://e/4"}]
    r = waterlog.check("Varthur", "Bengaluru", live, SEED)
    assert r["reports_by_year"] == {"2024": 1, "2026": 1} and r["undated_reports"] == 1
