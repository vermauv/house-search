from datetime import date

from housesearch import report, scoring, trends

TODAY = date(2026, 11, 1)


def inc(sev, d):
    return {"severity": sev, "date": d}


def test_improving_when_recent_year_is_quieter():
    items = [inc("violent", "2025-01-10"), inc("property", "2025-03-01"), inc("property", "2024-12-01"), inc("minor", "2026-05-01")]
    t = trends.incident_trend(items, TODAY)
    # recent 12m (since 2025-11-01): minor only = 1; prior 12m: violent+property+property = 8
    assert t["direction"] == "improving" and t["recent_12m_load"] == 1.0 and t["prior_12m_load"] == 8.0
    assert [y["year"] for y in t["by_year"]] == [2024, 2025, 2026]


def test_worsening_and_steady():
    worse = [inc("minor", "2024-12-01"), inc("property", "2026-02-01"), inc("violent", "2026-03-01"), inc("property", "2026-06-01")]
    assert trends.incident_trend(worse, TODAY)["direction"] == "worsening"
    steady = [inc("property", "2025-02-01"), inc("property", "2025-08-01"), inc("property", "2026-02-01"), inc("property", "2026-08-01")]
    assert trends.incident_trend(steady, TODAY)["direction"] == "steady"


def test_too_few_incidents_makes_no_claim():
    t = trends.incident_trend([inc("violent", "2026-01-01")], TODAY)
    assert t["direction"] == "insufficient_data" and t["caveat"]


def test_report_shows_trend_and_commute_profile():
    prof = {"slots": [{"depart_at": "2026-11-02T07:30:00+05:30", "traffic_min": 25, "multiplier": 1.5}, {"depart_at": "2026-11-02T09:00:00+05:30", "traffic_min": 55, "multiplier": 3.2}],
            "best_slot": "2026-11-02T07:30:00+05:30", "minutes_saved_by_best_slot": 30}
    item = {"id": "a", "title": "A", "rent": 1, "amenities": [], "enrichment": {
        "safety": {"score": 70, "confidence": "medium", "trend": trends.incident_trend([inc("property", "2025-02-01")] * 4, TODAY)},
        "commute": {"peak_min": 55, "multiplier": 3.2, "profile": prof},
        "waterlogging": {"status": "frequent", "warning": True, "evidence": [{"note": "n", "source_url": "https://e", "date": "2026-06-21"}], "reports_by_year": {"2024": 1, "2026": 1}}}}
    md = report.render_markdown(scoring.rank([item], {}, scoring.Weights()), {}, {})
    assert "Safety trend:" in md and "Leaving at 07:30 saves 30 min" in md and "Reports by year: 2024: 1, 2026: 1" in md
