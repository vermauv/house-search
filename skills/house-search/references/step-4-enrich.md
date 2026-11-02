# Step 4: Check the neighbourhood

This is where the ranking gets its substance. Work per **locality** where the answer is shared (safety, waterlogging) and per **listing** where position matters (hospitals, metro, malls, commute). Group listings by locality first so each locality is researched once.

Write into each listing's `enrichment` block ([data-model.md](data-model.md#enrichment)). Where you could not measure something, write `null` and a one-line `reason`; never omit silently and never estimate to fill a gap.

## Listing coordinates

Use the listing's own coordinates if the page shows a map pin. Otherwise geocode the society or building name with the locality (`hs.py geocode`). If that fails, use the locality centre and set `enrichment.position = "locality_centre"` so the report says the distances are approximate.

## 1. Safety (per locality)

**Read:** [safety.md](safety.md). It defines the sources (police statistics, news archives, society-level security), how to turn them into a 0-100 score, and how to state confidence. Use `hs.py safety-news` for the news component so the maths is the same every run.

## 2. Waterlogging (per locality)

**Read:** [waterlogging.md](waterlogging.md). Run a live news search, then:

```bash
python3 <skill-dir>/scripts/hs.py waterlog --locality "<locality>" --city "<city>" --findings findings.json
```

The result carries `warning` and `icon` (⚠️) and the evidence links. Attach it as `enrichment.waterlogging`. Always do this, even if the person did not mention rain.

## 3. Hospitals and ambulance time (per listing)

1. Find candidates (stdout is parsed JSON; do **not** invent a separate `osm_raw.json` unless you passed `--out` and the command succeeded):
   ```bash
   python3 <skill-dir>/scripts/hs.py nearby --lat <lat> --lon <lon> --kinds hospital --radius 6000 --limit 6
   ```
   Optional cache for debugging: add `--out <output-dir>/osm_nearby_hospital.json`. If `nearby` exits non-zero or prints `"error"`, record `enrichment.gaps.medical` with the message and continue — do not `json.load` a file that was never written.
2. **Verify emergency capability for the nearest 3.** A map "hospital" can be a clinic or a specialty centre without a casualty ward. Search each (`"<name> <city> 24x7 emergency casualty ambulance"`) and set `emergency: true/false`. Prefer multi-speciality and trauma-capable hospitals; note when the nearest real emergency department is further than the nearest hospital.
3. **Ambulance time** for each of the top 2 to 3 emergency hospitals, travelling **hospital → home**, in full traffic. The helper samples a morning and an evening weekday slot and keeps the worst:
   ```bash
   python3 <skill-dir>/scripts/hs.py ambulance --home <lat,lon> --hospital <lat,lon>
   ```
   It reports `peak_drive_min` (a car in peak traffic, the conservative figure), `ambulance_est_min` (applies an assumed siren factor of 0.7, never below free-flow time), `multiplier` and `label`. Always show both numbers and say the second is an estimate. Dispatch and call-handling delay are not included.
4. Save as `enrichment.medical.hospitals[]` with `name, km, emergency, peak_drive_min, ambulance_est_min, multiplier, label`.

**If there is no `GOOGLE_MAPS_API_KEY`** (the helper exits with code 3 and `MissingKeyError`): use a browser tool to open Google Maps directions for the same pair, set "Depart at" to the next Monday 08:45 and 19:00, and read the typical-traffic range; or ask the person to paste a Maps screenshot. If neither is possible, report the straight-line distance only, set `ambulance_est_min: null`, and write the reason. Do not convert distance into minutes yourself.

## 4. Metro and malls (per listing)

```bash
python3 <skill-dir>/scripts/hs.py nearby --lat <lat> --lon <lon> --kinds metro,mall,cinema --radius 8000
```

Record the nearest metro station (`enrichment.metro: {name, km}`) and the nearest 3 malls (`enrichment.malls: [{name, km}]`). These are straight-line kilometres; label them as such. Skip stations under construction unless a credible source gives an opening date, and mention it if you include one.

## 5. Office commute (per listing, only if opted in)

For each listing: home → office at `depart_home` and office → home at `depart_office`, on a weekday:

```bash
python3 <skill-dir>/scripts/hs.py traffic --origin <home lat,lon> --dest <office lat,lon> --depart "Mon 08:45"
```

Geocode the office first. The result gives `free_flow_min`, `traffic_min`, `multiplier` and a label: normal, busy (up to 2x), heavy (2-3x), very heavy (3-4x), severe (4x+). Save the worse direction as `enrichment.commute: {peak_min, free_flow_min, multiplier, label, depart_home, depart_office}`. In the report, show the multiplier plainly: "40 min instead of 14, 2.9x".

**Leaving-time profile.** Also run, for the top few listings (or the one the person is leaning towards):

```bash
python3 <skill-dir>/scripts/hs.py profile --origin <home lat,lon> --dest <office lat,lon>
```

It samples 07:30 to 10:30 in 45-minute steps (or repeat `--depart`) and returns the multiplier per slot, the best and worst slot, and `minutes_saved_by_best_slot`. Attach it as `enrichment.commute.profile`. This shows what leaving earlier or later changes. State plainly that it is Google's *typical-traffic forecast* for each time, not observed history: the API has no historical or month-by-month data, so the skill cannot say a commute is "getting worse".

Without the API key, use the same Maps fallback as above, or leave `commute: null` with a reason.

## 6. Pace yourself

Enrichment is the expensive step. Do per-locality work once, run per-listing calls in parallel, and stop adding detail once a listing's coverage is high. Never block the whole run on one failing lookup: record the gap and move on.

## Output

`<output-dir>/enriched.json`, same shape as `listings.json` with `enrichment` filled in.

**Gate:** each listing has `enrichment.safety`, `enrichment.waterlogging`, and either measured or explicitly-null values for medical, metro, malls and commute. Each null has a reason, written to `enrichment.gaps` under the keys `safety`, `medical`, `metro`, `malls` and `commute`. The report prints these reasons next to every `n/a`; a gap with no reason shows as "no reason recorded" and fails the gate. Say what actually happened (no Maps key, geocoder or map data unreachable, commute not requested, searched N query forms and found no locality-specific incidents), not just "unavailable".
