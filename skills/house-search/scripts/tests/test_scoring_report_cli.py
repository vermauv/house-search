import json
from datetime import date

import pytest

import hs
from housesearch import report, scoring

TODAY = date(2026, 10, 30)
W = scoring.Weights()
REQ = {
    "furnishing": "semi_furnished", "unit_types": ["2bhk"], "property_types": ["apartment"],
    "budget": {"max": 50000}, "amenities": {"must": ["parking_2w"], "nice": ["gym", "swimming_pool"]},
}


def listing(id, rent=45000, safety=70, eta=10, metro=1.0, mall=2.0, flood=None, **kw):
    enr = {
        "safety": {"score": safety, "confidence": "medium"},
        "medical": {"hospitals": [{"name": "H", "km": 2, "ambulance_est_min": eta, "peak_drive_min": eta * 1.4, "emergency": True}]},
        "metro": {"name": "M", "km": metro},
        "malls": [{"name": "Mall", "km": mall}],
    }
    if flood:
        enr["waterlogging"] = flood
    base = {"id": id, "title": id, "rent": rent, "furnishing": "semi_furnished", "unit_type": "2bhk", "property_type": "apartment",
            "amenities": ["parking_2w", "gym"], "enrichment": enr, "url": f"https://x.test/{id}"}
    return {**base, **kw}


def test_linear_clamps_and_handles_none():
    assert scoring.linear(5, 5, 30) == 100 and scoring.linear(30, 5, 30) == 0
    assert scoring.linear(100, 5, 30) == 0 and scoring.linear(0, 5, 30) == 100
    assert scoring.linear(None, 5, 30) is None
    assert scoring.linear(17.5, 5, 30) == 50


def test_news_safety_score_is_severity_and_recency_aware():
    none = scoring.news_safety_score([], TODAY)
    minor_recent = scoring.news_safety_score([{"severity": "minor", "date": "2026-10-01"}], TODAY)
    violent_recent = scoring.news_safety_score([{"severity": "violent", "date": "2026-10-01"}], TODAY)
    violent_old = scoring.news_safety_score([{"severity": "violent", "date": "2022-01-01"}], TODAY)
    assert none == 100 and 100 > minor_recent > violent_recent
    assert violent_old > violent_recent  # old incidents fade
    with pytest.raises(KeyError):
        scoring.news_safety_score([{"severity": "bogus", "date": "2026-01-01"}], TODAY)


def test_combine_safety_renormalises_and_reports_confidence():
    assert scoring.combine_safety({"station": None, "news": None, "property": None})["score"] is None
    one = scoring.combine_safety({"news": 60})
    assert one["score"] == 60 and one["confidence"] == "low"
    three = scoring.combine_safety({"station": 80, "news": 60, "property": 100})
    assert three["score"] == 76 and three["confidence"] == "high"


def test_hard_failures_only_for_explicit_mismatches():
    assert scoring.hard_failures(listing("ok"), REQ) == []
    assert scoring.hard_failures(listing("x", furnishing="furnished"), REQ)
    assert scoring.hard_failures(listing("x", unit_type="3bhk"), REQ)
    assert scoring.hard_failures(listing("x", rent=60000), REQ)
    assert scoring.hard_failures(listing("x", rent=51000), REQ) == []  # within 5% tolerance
    assert scoring.hard_failures(listing("x", amenities_absent=["parking_2w"]), REQ)
    # unknown fields never exclude
    assert scoring.hard_failures({"id": "bare"}, REQ) == []


def test_amenity_match_separates_missing_from_unverified():
    m = scoring.amenity_match(listing("a", amenities=["gym"]), REQ)
    assert m["must_unverified"] == ["parking_2w"] and m["nice_hit"] == ["gym"] and m["nice_missing"] == ["swimming_pool"] and m["score"] == 50


def test_missing_components_are_dropped_not_zeroed():
    bare = {"id": "b", "enrichment": {"safety": {"score": 80}}}
    s = scoring.score_listing(bare, {}, W)
    assert s["overall"] == 80 and s["coverage"] == 0.3 and s["confidence"] == "low"


def test_rank_orders_by_overall_and_supports_sort_override():
    safe_far = listing("safe_far", safety=95, eta=28)
    risky_near = listing("risky_near", safety=40, eta=6)
    r = scoring.rank([risky_near, safe_far], REQ, W)
    assert [i["id"] for i in r["ranked"]] == ["risky_near", "safe_far"] or [i["id"] for i in r["ranked"]] == ["safe_far", "risky_near"]
    by_safety = scoring.rank([risky_near, safe_far], REQ, W, sort_by="safety")
    assert [i["id"] for i in by_safety["ranked"]] == ["safe_far", "risky_near"] and by_safety["ranked"][0]["rank"] == 1
    with pytest.raises(ValueError):
        scoring.rank([], REQ, W, sort_by="vibes")


def test_thin_data_cannot_outrank_thoroughly_checked_listings():
    thorough = listing("thorough", safety=60, eta=14)  # all six components measured
    thin = {"id": "thin", "rent": 40000, "enrichment": {"safety": {"score": 85}}}  # one component
    r = scoring.rank([thin, thorough], {}, W)
    assert r["ranked"][0]["id"] == "thorough"
    assert thin["enrichment"]["safety"]["score"] == 85
    s = next(i for i in r["ranked"] if i["id"] == "thin")["scores"]
    assert s["overall"] == 85 and s["adjusted"] < 85 and s["confidence"] == "low"


def test_ties_break_on_lower_rent():
    r = scoring.rank([listing("pricey", rent=48000), listing("cheap", rent=40000)], REQ, W)
    assert [i["id"] for i in r["ranked"]] == ["cheap", "pricey"]


def test_waterlogging_warns_but_does_not_change_score_and_can_be_hidden():
    flood = {"status": "frequent", "warning": True, "icon": "⚠️", "evidence": [{"note": "n", "source_url": "https://e", "date": "2026-06-21"}]}
    a, b = listing("dry"), listing("wet", flood=flood)
    r = scoring.rank([a, b], REQ, W)
    assert r["ranked"][0]["scores"]["overall"] == r["ranked"][1]["scores"]["overall"]
    hidden = scoring.rank([a, b], REQ, W, hide_waterlogged=True)
    assert [i["id"] for i in hidden["ranked"]] == ["dry"] and "waterlogging" in hidden["excluded"][0]["reasons"][0]


def test_weights_load_and_reject_unknown_keys(tmp_path):
    assert scoring.Weights.load().safety == 0.30
    p = tmp_path / "w.json"
    p.write_text(json.dumps({"safety": 1, "luck": 1}))
    with pytest.raises(ValueError, match="luck"):
        scoring.Weights.load(p)


def test_report_shows_warning_icon_unverified_and_escapes_html():
    flood = {"status": "frequent", "warning": True, "evidence": [{"note": "Water on Varthur Road", "source_url": "https://e/1", "date": "2026-06-21"}]}
    res = scoring.rank([listing("<b>x</b>", flood=flood, amenities=["gym"], title="<script>alert(1)</script>")], REQ, W)
    meta = {"locality": "Mahadevapura", "query": "2bhk", "as_of": "2026-10-30", "assumptions": ["a"]}
    md = report.render_markdown(res, REQ, meta)
    assert "⚠️" in md and "Ask the owner" in md and "Parking" not in md.split("Ask the owner")[0][-5:]
    page = report.render_html(res, REQ, meta)
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;" in page and "⚠️" in page


def test_report_explains_every_na_cell_and_escapes_the_reason():
    enr = {"gaps": {"medical": "no Google Maps key", "commute": "not requested <b>", "safety": "only citywide stories found"}}
    item = listing("a", enrichment=enr)
    item["enrichment"].update({"safety": None, "medical": None, "metro": {"name": "M", "km": 1.0}, "malls": [{"name": "Mall", "km": 2.0}]})
    res = scoring.rank([item], REQ, W)
    meta = {"locality": "X", "query": "q", "as_of": "2026-10-30"}
    md = report.render_markdown(res, REQ, meta)
    assert "Not measured" in md and "Ambulance: no Google Maps key" in md
    assert "Commute: not requested <b>" in md and "Safety: only citywide stories found" in md
    assert "Metro:" not in md.split("Not measured")[1].split("Data coverage")[0]
    page = report.render_html(res, REQ, meta)
    assert "not requested &lt;b&gt;" in page and "not requested <b>" not in page


def test_report_flags_an_na_with_no_recorded_reason():
    item = listing("a")
    item["enrichment"]["medical"] = None
    res = scoring.rank([item], REQ, W)
    md = report.render_markdown(res, REQ, {"locality": "X"})
    assert "Ambulance: " + report.NO_REASON in md


def test_report_handles_no_results():
    md = report.render_markdown({"sort_by": "overall", "ranked": [], "excluded": [{"id": "1", "title": "t", "reasons": ["too dear"]}]}, REQ, {})
    assert "No listing passed" in md and "too dear" in md


def test_cli_end_to_end(tmp_path, capsys):
    (tmp_path / "l.json").write_text(json.dumps([listing("a"), listing("b", rent=99999)]))
    (tmp_path / "r.json").write_text(json.dumps(REQ))
    assert hs.main(["rank", "--listings", str(tmp_path / "l.json"), "--requirements", str(tmp_path / "r.json"), "--out", str(tmp_path / "ranked.json")]) == 0
    out = json.loads(capsys.readouterr().out)
    assert [i["id"] for i in out["ranked"]] == ["a"] and out["excluded"][0]["id"] == "b"
    assert hs.main(["report", "--ranked", str(tmp_path / "ranked.json"), "--requirements", str(tmp_path / "r.json"), "--out-dir", str(tmp_path / "o")]) == 0
    assert (tmp_path / "o" / "report.md").read_text().startswith("# House search")
    assert (tmp_path / "o" / "report.html").exists()


def test_cli_rank_accepts_the_listings_wrapper(tmp_path, capsys):
    (tmp_path / "l.json").write_text(json.dumps({"sources": [], "listings": [listing("a")]}))
    (tmp_path / "r.json").write_text(json.dumps(REQ))
    assert hs.main(["rank", "--listings", str(tmp_path / "l.json"), "--requirements", str(tmp_path / "r.json")]) == 0
    assert [i["id"] for i in json.loads(capsys.readouterr().out)["ranked"]] == ["a"]


def test_cli_errors_are_json_and_missing_key_has_its_own_exit_code(capsys, monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    assert hs.main(["traffic", "--origin", "12.9,77.6", "--dest", "12.8,77.7", "--depart", "09:00"]) == 3
    assert json.loads(capsys.readouterr().out)["error"] == "MissingKeyError"
    assert hs.main(["normalize", "--json", "/nonexistent.json"]) == 1
    assert json.loads(capsys.readouterr().out)["error"] == "FileNotFoundError"


def test_cli_rejects_bad_coordinates():
    with pytest.raises(SystemExit):
        hs.main(["traffic", "--origin", "999,1", "--dest", "1,1", "--depart", "09:00"])


def test_cli_normalize_text(capsys):
    assert hs.main(["normalize", "--text", "1rk unfurnished flat, security"]) == 0
    r = json.loads(capsys.readouterr().out)
    assert r["unit_types"] == ["1rk"] and r["furnishing"] == "unfurnished" and r["amenities"]["nice"] == ["security_24x7"]
