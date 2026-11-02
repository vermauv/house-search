# Step 2: Locate the area

Know exactly where "Mahadevapura" is before searching. Localities share names across cities, and listing portals draw their boundaries differently.

## 1. Resolve on the map

```bash
python3 <skill-dir>/scripts/hs.py geocode "<locality>, <city>"
```

With `GOOGLE_MAPS_API_KEY` this uses Google Geocoding; without it, OpenStreetMap Nominatim. The result lists `candidates` and sets `ambiguous: true` when the top candidates are more than 3 km apart.

- **Not ambiguous:** take the first candidate.
- **Ambiguous:** ask which one (show the formatted addresses). If the person is away, pick the candidate in the city they named, or the largest city, and record the assumption.
- **No result:** retry with the city appended, then with the portal's spelling (search the locality on a portal and copy its label), then fall back to a web search for the area and read coordinates from a map page. Never proceed with guessed coordinates.

## 2. Choose the search area

- **Radius.** Default 3 km around the centre. Use 1.5 km for dense inner-city localities, 5 km for suburbs and outskirts, or whatever `--radius` says. The bounding box in the candidate shows how large the locality itself is; a locality bigger than the radius should use its own extent.
- **Neighbours.** List 3 to 6 adjacent micro-localities and societies inside the radius (portals filter by these names). Pull them from the map, from portal locality pickers, and from search. They matter because the best match is often one lane over the portal's boundary.
- **Boundary caution.** If the user's locality sits on a zone boundary, note both. Civic data such as waterlogging lists and police jurisdictions are organised by ward, zone and station, not by the neighbourhood names portals use.

## Output

`<output-dir>/area.json`:

```json
{
  "query": "Mahadevapura, Bengaluru",
  "city": "Bengaluru",
  "centre": {"lat": 12.99, "lon": 77.69},
  "formatted": "Mahadevapura, Bengaluru, Karnataka, India",
  "radius_km": 3,
  "search_localities": ["Mahadevapura", "Marathahalli", "KR Puram", "Kundalahalli"],
  "provider": "nominatim",
  "assumptions": []
}
```

**Gate:** coordinates are confirmed (not guessed), the city is settled, and `search_localities` is non-empty.
