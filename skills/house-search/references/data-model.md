# Data model

The JSON passed between steps. Unknown fields are allowed and ignored; missing fields are treated as unknown, never as zero.

## Requirements

`requirements.json` (written in step 1, read by `rank` and `report`):

```json
{
  "original_text": "semi furnished 2.5bhk apartment in Mahadevapura with 2 wheeler parking, gym, pets allowed, under 55k",
  "locality": "Mahadevapura",
  "city": "Bengaluru",
  "furnishing": "semi_furnished",
  "unit_types": ["2.5bhk"],
  "property_types": ["apartment"],
  "budget": {"max": 55000, "currency": "INR", "period": "month"},
  "amenities": {"must": ["parking_2w", "pets_allowed"], "nice": ["gym"]},
  "facing": "east",
  "area_sqft": {"min": 1000, "max": 1400},
  "bathrooms_min": 2,
  "property_age_max_years": 5,
  "floor": {"pref": "high"},
  "commute": {"office": "Embassy Tech Village", "depart_home": "08:45", "depart_office": "18:30"},
  "notes": ["lake view"],
  "assumptions": []
}
```

`budget` is `{max}`, `{min, max}` or `{approx}`. Only `max` is enforced as a hard filter (with 5% tolerance). `commute` is `null` when the person declined.

## Listing

```json
{
  "id": "nobroker-8a2f",
  "source": "nobroker.in",
  "url": "https://...",
  "also_listed_at": [],
  "title": "2.5 BHK in Prestige Xyz",
  "rent": 52000,
  "deposit": 300000,
  "maintenance": 3500,
  "furnishing": "semi_furnished",
  "unit_type": "2.5bhk",
  "property_type": "apartment",
  "society": "Prestige Xyz",
  "locality": "Mahadevapura",
  "lat": 12.99, "lon": 77.69,
  "area_sqft": 1250,
  "floor": 7, "total_floors": 14,
  "bathrooms": 2,
  "age_years": 4,
  "facing": "east",
  "available_from": "2026-11-15",
  "amenities": ["parking_2w", "gym", "swimming_pool"],
  "amenities_absent": [],
  "posted_at": "2026-10-25",
  "fetched_at": "2026-10-30T11:40:00+05:30",
  "notes": [
    "All-in ₹36,800/mo with ₹2,000 maintenance per portal breakup",
    "NoBroker livability 6.2 / transit 8.5 (portal scores, not verified independently)"
  ],
  "enrichment": {}
}
```

- `rent` is monthly, in the budget's currency. Keep the headline rent in `rent`; use `deposit`, `maintenance`, and related fields where the portal gives them; put brokerage, all-in totals, and other breakdown context in `notes` when there is no dedicated field.
- `notes` on a **listing** is a string array of facts from the **opened listing page** that do not belong in structured fields. Use it for: portal livability/transit scores, LIVE / verified-availability badges, "other units same rent", tenant-type restrictions, geocode or map-pin uncertainty, viewing-schedule text (never phone numbers), warnings that a post may be stale, and clarifications when the address is outside the locality the person named. Do not repeat amenity keys already captured in `amenities` / `amenities_absent` unless the portal wording is ambiguous.
- `amenities` are keys the listing **states**; `amenities_absent` are keys it **explicitly denies**. Silence is neither.
- No owner or broker contact details. The `url` is the route.
- `hs.py report` prints each listing's `notes` as bullets under that home (after "Ask the owner" lines).

## Enrichment

Filled in step 4, inside each listing:

```json
"enrichment": {
  "position": "listing_pin",
  "safety": {"score": 74.2, "confidence": "medium", "parts": {"station": null, "news": 71.0, "property": 80.0},
             "evidence": [{"note": "...", "source_url": "https://...", "date": "2026-03-14"}], "searched": "...",
             "trend": {"direction": "improving", "by_year": [{"year": 2025, "count": 3, "load": 6.0}], "recent_12m_load": 1.0, "prior_12m_load": 8.0}},
  "waterlogging": {"status": "frequent", "warning": true, "icon": "⚠️", "reports_by_year": {"2024": 1, "2026": 1}, "evidence": [{"note": "...", "source_url": "https://...", "date": "2026-06-21"}], "note": ""},
  "medical": {"hospitals": [
    {"name": "Example Hospital", "km": 2.1, "emergency": true,
     "peak_drive_min": 28.0, "ambulance_est_min": 19.6, "multiplier": 3.1, "label": "very heavy (3-4x)"}
  ]},
  "metro": {"name": "Example Metro", "km": 1.4},
  "malls": [{"name": "Example Mall", "km": 2.2}],
  "commute": {"peak_min": 52.0, "free_flow_min": 18.0, "multiplier": 2.9, "label": "heavy (2-3x)",
              "depart_home": "Mon 08:45", "depart_office": "Mon 18:30",
              "profile": {"slots": [{"depart_at": "...", "traffic_min": 25, "multiplier": 1.5, "label": "busy (up to 2x)"}], "best_slot": "...", "worst_slot": "...", "minutes_saved_by_best_slot": 30.0}},
  "gaps": {"commute": "no GOOGLE_MAPS_API_KEY and no browser available"}
}
```

Rules:

- `position` is `listing_pin` or `locality_centre`. The latter makes every distance approximate; the report says so.
- Use `null` for anything unmeasured and explain it under `gaps`. The scorer skips nulls and lowers `coverage`.
- `medical.hospitals[].emergency` is `true` (verified casualty ward), `false` (verified none, excluded from the medical score) or omitted (unverified).
- Distances (`km`) are straight-line. Times come from traffic data only.

## Ranked

`ranked.json`: `{sort_by, weights, ranked: [listing + {rank, scores}], excluded: [{id, title, reasons}]}` where `scores` holds `overall`, `adjusted` (the default sort key: `overall` shrunk toward 50 by missing coverage), the six component scores (or null), `coverage`, `confidence` (`high` ≥ 0.8, `medium` ≥ 0.5, else `low`) and `amenity_match`.
