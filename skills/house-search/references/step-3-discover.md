# Step 3: Discover listings

Collect real listings from every relevant source, normalise them, remove duplicates, and drop the ones that contradict a hard requirement.

## 1. Pick sources

Read [sources.md](sources.md). Search all the portals it lists for the city, plus managed-rental and community channels where they fit the request (furnished or serviced requests lean on managed-rental brands; budget and bachelor-friendly requests lean on community groups). More sources means fewer missed homes, but stop when new sources stop adding new listings.

"All rental platforms (web/apps)": an app-only listing has no URL you can open. Most portals mirror their app listings on the web; use the web version. For anything genuinely app-only, say so in the report and tell the person which app to check with which filters.

## 2. Search

For each source, in this order of preference:

1. **A browser tool, if present**, set the portal's own filters (city, locality, BHK, furnishing, property type, budget) so results are exactly what the portal considers a match. Re-read the URL after filtering once; URL patterns drift, so never rely on a remembered one.
2. **WebFetch** on a public search-result page.
3. **WebSearch** with `site:` queries, e.g. `site:nobroker.in 2bhk semi furnished Mahadevapura rent`. Results are often stale; open the listing to confirm it is still live.

Run searches for each locality in `area.json` and for each unit type the person wants. Send independent searches in parallel.

For each listing open the page and read: rent, deposit, maintenance, furnishing, unit type, property type, society, area, floor, bathrooms, age, facing, amenities, posted date, availability.

Also capture portal-only context in the listing's `notes` array (see [data-model.md](data-model.md#listing)): livability/transit scores, verified availability, multiple units at the same rent, pets or tenant restrictions already reflected in `amenities_absent`, all-in monthly cost, and whether the pin is outside the locality name the person asked for.

**Hygiene**

- Only public pages. No logins, no CAPTCHA solving, no bypassing blocks, no high-volume crawling. If a source blocks you, record `{"source": "...", "status": "blocked", "open_url": "<search link for the person>"}`.
- Do not store owner or broker phone numbers or emails. The listing URL is the contact route.
- A listing you did not open and cannot see in a search result does not exist. Never fill in details from "typical" values.
- Set `fetched_at` to the actual time you read it. Listings go stale in days.

## 3. Normalise to the shared record

Use the fields in [data-model.md](data-model.md#listing). Map amenity wording to canonical keys with [amenities.md](amenities.md): put what the listing states in `amenities`, what it explicitly denies ("no lift", "pets not allowed") in `amenities_absent`, and leave everything else out. Silence is not denial. Put remaining facts worth reporting in `notes`.

## 3b. Add a listing the person sends later

When the person shares a **specific listing URL** (including portal "similar" links) after the first pass:

1. Open that URL and normalise a full record like any other listing.
2. Append it to `<output-dir>/listings.json` and bump the source `count` / note in `sources`.
3. Enrich it (copy locality-level safety/waterlogging from a neighbour if needed; record approximation in `notes` and `enrichment.gaps`).
4. Re-run `hs.py rank` and `hs.py report`. Do not hand-edit `report.md` / `report.html`.

## 4. De-duplicate

The same flat is often listed on several portals and by several brokers. Treat two records as the same home when they share the society (or a ~100 m location), unit type and floor, and rents are within 5%. Keep the record with the most complete data, add the other URLs to `also_listed_at`, and keep the lowest rent seen as `rent` with the others in `rent_seen`.

## 5. Filter and cap

Drop listings that explicitly contradict a hard requirement (the ranker re-checks this, but filtering now saves enrichment work, which is the expensive part). Keep unknowns.

If more than `--max-listings` (default 12) remain, keep the best by: requirement match, completeness of data, and price fit. Say how many were found and how many are enriched. Offer to widen if there are fewer than 5.

## Output

`<output-dir>/listings.json`: `{"sources": [{name, status, count, note}], "listings": [...]}`

**Gate:** every listing has `url`, `source`, `fetched_at`, `rent`, and a locality; sources report `ok`, `empty`, `blocked` or `app_only`; no duplicates remain.
