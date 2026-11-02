# Waterlogging

Goal: warn the person, with sources, when a locality is repeatedly reported as waterlogged or flooded in rain. The warning shows as ⚠️ on every listing in that area. It does not change the score; it is a risk the person weighs (and `--exclude-waterlogged` can hide those listings).

## 1. Gather evidence

Search news and civic sources for the locality **and its major roads, junctions, underpasses, lakes and stormwater drains**. Waterlogging is often reported by road, not by neighbourhood.

Queries, with the city:

- `"<locality> waterlogging"`, `"<locality> flooding rain"`, `"<locality> roads waterlogged"`
- `"<locality> apartment flooded"`, `"<locality> basement water entered"`
- the civic body's list of flood-prone or vulnerable spots (municipal corporation, disaster-management authority, traffic police advisories during rain)
- a lake or drain near the locality, plus `overflow`

Look back at least three monsoon seasons. One heavy-rain event is a report; the same area across years is a pattern.

Record each finding once:

```json
{"area": "Varthur Road", "date": "2026-06-21", "note": "Severe accumulation; water entered apartment complexes", "source_url": "https://...", "official_list": false}
```

`date` is the **reporting** date. Set `official_list: true` only when the finding comes from a civic body's own list of vulnerable spots.

## 2. Check

```bash
python3 <skill-dir>/scripts/hs.py waterlog --locality "<locality>" --city "<city>" --findings findings.json
```

The helper merges your findings with `assets/waterlogging-seed.json` (a short, sourced starter list; never a substitute for your live search) and returns:

| `status` | Meaning |
|---|---|
| `frequent` | On an official vulnerable-spot list, or reported in 2+ distinct years. Warning shown. |
| `reported` | At least one report. Warning shown. |
| `none_found` | Nothing found. **Not** a guarantee. No warning, with a note to check the specific street. |

The result also has `reports_by_year` (for example `{"2022": 1, "2024": 2, "2026": 1}`) and `undated_reports`. Use it for the trend: repeated across years is a pattern, a single year is an event. Search back at least three monsoon seasons so the years are comparable, and say when older years simply had less coverage online.

Matching is whole-word: "Varthur Road" matches Varthur, "Varthuri" does not.

## 3. Say it well

In the report and chat answer, show `⚠️ Waterlogging frequent` or `reported` with one sentence and the link. Quote what was reported (road, apartments, year), not a vague "floods a lot". Mention that risk varies street by street and by floor; for ground-floor and basement-parking homes, suggest asking residents about the last two monsoons.

If the person chose `--exclude-waterlogged`, say how many listings were hidden and offer to show them.

## Maintaining the seed

Add an entry to `assets/waterlogging-seed.json` only with a real source URL and a reporting date, under the lower-cased city name. Remove entries that civic works have demonstrably resolved, with a source. The seed is a convenience; the live search is the check.
