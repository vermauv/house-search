import json

import pytest

from housesearch import geo, http, places


def fake(payload, seen=None):
    def transport(req, timeout):
        if seen is not None:
            seen.append(req)
        return json.dumps(payload).encode()
    return transport


def test_haversine_known_distance():
    # Bengaluru (MG Road) to Whitefield is roughly 17-19 km as the crow flies.
    assert 15 < geo.haversine_km(12.9756, 77.6068, 12.9698, 77.7500) < 19
    assert geo.haversine_km(1, 1, 1, 1) == 0


def test_nominatim_geocode_flags_ambiguity(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    payload = [
        {"display_name": "Mahadevapura, Bengaluru", "lat": "12.99", "lon": "77.69", "type": "suburb"},
        {"display_name": "Mahadevapura, Elsewhere", "lat": "15.0", "lon": "75.0", "type": "village"},
    ]
    r = geo.geocode("Mahadevapura", transport=fake(payload))
    assert r["provider"] == "nominatim" and r["ambiguous"] is True
    assert r["candidates"][0]["lat"] == 12.99


def test_single_or_close_candidates_are_not_ambiguous(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    payload = [
        {"display_name": "A", "lat": "12.99", "lon": "77.69"},
        {"display_name": "B", "lat": "12.995", "lon": "77.695"},
    ]
    assert geo.geocode("x", transport=fake(payload))["ambiguous"] is False


def test_google_geocode_used_when_key_set(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "secret-key")
    payload = {"status": "OK", "results": [{"formatted_address": "Mahadevapura, Bengaluru", "geometry": {"location": {"lat": 12.99, "lng": 77.69}}, "types": ["sublocality"]}]}
    seen = []
    r = geo.geocode("Mahadevapura Bengaluru", transport=fake(payload, seen))
    assert r["provider"] == "google" and r["candidates"][0]["kind"] == "sublocality"
    assert "secret-key" in seen[0].full_url  # sent, but never printed:
    assert "secret-key" not in http.redact(seen[0].full_url)


def test_google_error_status_raises(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "k")
    with pytest.raises(RuntimeError, match="REQUEST_DENIED"):
        geo.geocode("x", transport=fake({"status": "REQUEST_DENIED", "error_message": "bad key"}))


def test_overpass_query_and_parsing():
    q = places.build_query(12.99, 77.69, ["hospital", "metro"], 3000)
    assert '"amenity"="hospital"' in q and '"station"="subway"' in q and "around:3000,12.99,77.69" in q
    with pytest.raises(ValueError):
        places.build_query(0, 0, ["helipad"], 1)

    elements = [
        {"type": "node", "lat": 12.995, "lon": 77.69, "tags": {"amenity": "hospital", "name": "Far Hospital", "emergency": "yes"}},
        {"type": "way", "center": {"lat": 12.991, "lon": 77.691}, "tags": {"amenity": "hospital", "name": "Near Hospital"}},
        {"type": "node", "lat": 12.991, "lon": 77.691, "tags": {"amenity": "hospital", "name": "near hospital"}},  # duplicate
        {"type": "node", "lat": 12.99, "lon": 77.69, "tags": {"amenity": "hospital"}},  # unnamed: skipped
        {"type": "node", "lat": 12.98, "lon": 77.7, "tags": {"station": "subway", "name": "Metro Stn"}},
    ]
    r = places.parse_elements(elements, 12.99, 77.69, ["hospital", "metro"])
    assert [h["name"] for h in r["hospital"]] == ["Near Hospital", "Far Hospital"]
    assert r["hospital"][1]["tags"] == {"emergency": "yes"}
    assert r["metro"][0]["name"] == "Metro Stn"


def test_nearby_limits_results():
    els = [{"type": "node", "lat": 12.99 + i / 1000, "lon": 77.69, "tags": {"shop": "mall", "name": f"Mall {i}"}} for i in range(6)]
    r = places.nearby(12.99, 77.69, ["mall"], limit=3, transport=fake({"elements": els}))
    assert len(r["mall"]) == 3
    assert r["_meta"]["element_count"] == 6


def test_overpass_tries_mirrors_when_primary_fails(monkeypatch):
    calls: list[str] = []

    def fake_request_json(url, **kwargs):
        calls.append(url)
        if "overpass-api.de" in url:
            raise http.HttpError("HTTP 504", 504)
        return {"elements": []}

    monkeypatch.setattr(places, "request_json", fake_request_json)
    data, url = places.query_overpass(12.99, 77.69, ["mall"], 1000)
    assert data["elements"] == []
    assert "kumi.systems" in url
    assert len(calls) >= 2


def test_http_retries_then_raises_and_never_leaks_keys(monkeypatch):
    monkeypatch.setattr(http.time, "sleep", lambda s: None)
    calls = []

    def flaky(req, timeout):
        calls.append(1)
        raise http.HttpError(f"HTTP 503 from {http.redact(req.full_url)}", 503)

    with pytest.raises(http.HttpError) as exc:
        http.request_json("https://x.test/a", params={"key": "SECRET"}, transport=flaky, retries=2)
    assert len(calls) == 3 and "SECRET" not in str(exc.value)


def test_http_does_not_retry_client_errors():
    calls = []

    def denied(req, timeout):
        calls.append(1)
        raise http.HttpError("HTTP 403", 403)

    with pytest.raises(http.HttpError):
        http.request_json("https://x.test/a", transport=denied, retries=3)
    assert len(calls) == 1
