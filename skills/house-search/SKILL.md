---
name: house-search
description: Find rental homes from a plain-English description and rank them on what matters beyond price - safety, hospital access and ambulance time in peak traffic, metro, malls, office commute, and waterlogging risk. Searches all major rental platforms (web and app listings), resolves the locality on the map, and returns a ranked shortlist. Use when someone says "/house-search", "find me a 2bhk in Mahadevapura", "looking for a flat to rent", "house hunting", "which area is safe to rent in", or describes a rental with furnishing, BHK, locality, budget or amenities, even if they never say "skill".
---

# /house-search

Describe the home you want in your own words. This skill finds real listings across rental platforms, checks the neighbourhood, and ranks what it finds.

## What this skill does

1. Turns the sentence into structured requirements (furnishing, BHK, property type, locality, budget, amenities).
2. Locates the area on the map and decides how wide to search.
3. Searches every relevant rental source and collects listings.
4. Checks each area: safety, nearest hospitals and ambulance time in peak traffic, metro, malls, optional office commute, waterlogging.
5. Ranks the shortlist and writes a report.

## Invocation

Natural language is the main interface. Flags are optional shortcuts:

```
/house-search 2bhk semi furnished flat in Mahadevapura with 2 wheeler parking, gym, pets allowed, under 55k
/house-search studio in Indiranagar --office "Embassy Tech Village" --depart 08:45
/house-search 3bhk villa Whitefield --sort safety --exclude-waterlogged
```

| Option | Values | Default |
|---|---|---|
| `--city` | city name | inferred from locality, else ask |
| `--budget` | monthly rent, e.g. `50k`, `30-40k` | ask if absent |
| `--office` | address or place name | none; the commute question is asked once |
| `--depart` / `--return` | `HH:MM` leaving home / leaving office | `08:45` / `18:30` |
| `--sort` | `overall`, `safety`, `medical`, `commute`, `amenities`, `metro`, `entertainment` | `overall` |
| `--radius` | km around the locality centre | `3` |
| `--max-listings` | how many listings to enrich | `12` |
| `--exclude-waterlogged` | flag | warn, do not hide |
| `--no-commute` | flag | commute asked once |

If the person says "safety matters most" or "I don't care about malls", translate that into `--sort` or a weights file (`assets/weights.default.json`) rather than ignoring it.

## Principles

These hold for every run. They exist because a wrong number here costs someone a lease.

**Never invent a listing or a number.** Every listing has a URL you actually opened or a search result you actually saw. Every figure carries its source and date. If you could not measure something, say so and leave it out; the scorer renormalises over what exists and shows a confidence level.

**No evidence is not good news.** "No waterlogging reports found" and "no incidents found" mean *none found*, never *safe*. Say that.

**Safety is about incidents, not people.** Score areas from reported crime, police data and property security. Never use or mention who lives there (religion, caste, ethnicity, nationality, income, marital status) as a safety or desirability signal, and do not compile information about named individuals from FIRs or news. Aggregate only.

**Respect the sources.** Read public pages and search results. Do not log in on the person's behalf without being asked, solve CAPTCHAs, bypass blocks, or scrape at volume. When a platform blocks you, mark it `blocked` in the report and hand the person a link to open themselves.

**Ask little, once.** One round of at most three questions, only for things a wrong guess would make expensive. Otherwise decide, state the assumption in the report, and move on.

**Unverified is a flag, not a failure.** Listings often omit amenities. A missing must-have becomes "ask the owner"; only an explicit "no" excludes a listing.

## Output directory

Write everything to `house-search-output/`. If it already exists, use `house-search-output-YYYY-MM-DD-HHmmss/` so earlier runs survive. Intermediate files: `requirements.json`, `area.json`, `listings.json`, `enriched.json`, `ranked.json`. Deliverables: `report.md`, `report.html`.

## Skill directory

`<skill-dir>` is the directory containing this `SKILL.md`. Claude Code prints it as "Base directory for this skill" when the skill loads; other agents use wherever it was installed. Helpers are at `<skill-dir>/scripts/hs.py` (standard-library Python 3.11+, no installs). Run `python3 <skill-dir>/scripts/hs.py --help`. Don't guess an install path.

Optional: set `GOOGLE_MAPS_API_KEY` for traffic multipliers and ambulance times and for better geocoding. Without it the skill still works, using OpenStreetMap for places and a manual Google Maps fallback for traffic.

---

## Step 1: Understand the request

**Read:** [references/step-1-understand.md](references/step-1-understand.md)

Run `hs.py normalize --text "<their words>"`, complete it with judgement, write `requirements.json`, and ask the few questions that matter, including the one-time commute offer.

**Gate:** `requirements.json` has a locality, a city, at least one unit type, and a budget or an explicit "no budget". Nothing in `unmapped` is left unresolved.

---

## Step 2: Locate the area

**Read:** [references/step-2-locate.md](references/step-2-locate.md)

Resolve the locality on the map, confirm it if ambiguous, pick the search radius and list the neighbouring micro-localities worth including.

**Gate:** `area.json` has coordinates, the confirmed city, a radius and a list of search localities.

---

## Step 3: Discover listings

**Read:** [references/step-3-discover.md](references/step-3-discover.md)
**Read:** [references/sources.md](references/sources.md)
**Read:** [references/amenities.md](references/amenities.md)

Search every relevant source, extract listings into the shared record format, de-duplicate across platforms, and drop what contradicts a hard requirement.

**Gate:** `listings.json` holds real, deduplicated listings, each with a URL, source and `fetched_at`. A source that was blocked or empty is recorded, not silently skipped.

---

## Step 4: Check the neighbourhood

**Read:** [references/step-4-enrich.md](references/step-4-enrich.md)
**Read:** [references/safety.md](references/safety.md)
**Read:** [references/waterlogging.md](references/waterlogging.md)

Per locality: safety and waterlogging, each with a year-by-year trend where the dated evidence allows. Per listing: hospitals and ambulance time, metro, malls, and the office commute (with a leaving-time profile) if the person opted in.

**Gate:** every listing in `enriched.json` has an `enrichment` block; gaps are explicit `null`s with a reason, not omissions.

---

## Step 5: Rank and deliver

**Read:** [references/step-5-rank-deliver.md](references/step-5-rank-deliver.md)
**Read:** [references/data-model.md](references/data-model.md)

Run `hs.py rank` then `hs.py report`. Answer in chat with the top few, the warnings, and what could not be verified.

If the person sends a **listing URL** after the first report, open it, append to `listings.json`, enrich, and re-run `rank` + `report` (see step 3b in [references/step-3-discover.md](references/step-3-discover.md)). Put portal-only facts in each listing's `notes` so they appear in the report.

**Gate:** `report.md` and `report.html` exist, every ⚠️ in the chat answer is backed by a cited source, the answer states data confidence and assumptions, and worthwhile listing-page detail is in `notes` (not only in chat).
