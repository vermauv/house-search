# Safety

Goal: a defensible, comparable 0-100 safety figure per locality with an honest confidence level. It is a relative indicator built from public evidence, not a promise.

## Ground rules

- Measure **incidents and security**, never people. Do not use or mention residents' religion, caste, ethnicity, nationality, income or marital status. Do not describe an area as "good" or "bad" because of who lives there.
- Use aggregates. Do not collect FIRs or articles about named individuals.
- No evidence is "none found", not "safe".
- Show your sources. Every evidence item needs a URL and a date.

## Three components

Each is scored 0-100 (higher is safer). Use whichever you can measure; the blend renormalises.

### 1. Police statistics (`station`)

The most authoritative source and the hardest to get.

- Find the **police station jurisdiction** for the locality (police department website, map search "<locality> police station", news about the station).
- Look for published crime figures at the finest grain available, in this order: station-level or ward-level data from the city police or state open-data portal; the city police's annual report; the NCRB "Crime in India" city table (city-level only, so it ranks cities, not neighbourhoods).
- Convert to a rate where possible (incidents per lakh residents) and compare against the other localities in this search. Score by rank or percentile among them (best locality near 90, worst near 30). A city-level figure alone must not differentiate localities; use it only as context and leave `station` null.

If you cannot find fine-grained data, set `station: null` and say why. That is common, and fine.

### 2. News incidents (`news`)

Search local news archives for the last 24 months for incidents tied to the locality and its society names: chain snatching, burglary, theft, vehicle theft, assault, harassment, robbery, murder, sexual offences, cyber-enabled local fraud rings, drug raids. Use several query forms per locality (`"<locality> robbery"`, `"<locality> police arrested"`, `"<locality> chain snatching"`, and the same with the nearest police station's name).

Record each distinct incident once (the same event is reported by many outlets):

```json
{"severity": "property", "date": "2026-03-14", "note": "Two-wheeler thefts reported in X", "source_url": "https://..."}
```

Severity: `minor` (petty theft, nuisance), `property` (burglary, vehicle theft, snatching), `violent` (assault, robbery, murder), `sexual` (sexual offences, harassment of women). Then:

```bash
python3 <skill-dir>/scripts/hs.py safety-news --incidents incidents.json
```

Score = 100 × exp(−load / 8), where load sums severity weights (1, 2, 4, 6) with a 12-month half-life so old incidents fade. The constant is a scale, not a verdict: **compare localities with each other**.

News volume tracks population, media attention and reporting culture, not only risk. Compare like with like (similar-size localities), and read the headlines: a burglary ring caught is not the same as a burglary ring active.

### 3. Property security (`property`)

Per listing or society, from the listing and the society's own pages: gated community, 24x7 guards, CCTV, intercom, visitor management, controlled entry, lit approach. Score 100 when most are present, scaling down with each missing item; set `null` if the listing says nothing.

### Trend

Run the same dated incident list through:

```bash
python3 <skill-dir>/scripts/hs.py safety-trend --incidents incidents.json
```

It lists incident counts per year and compares the last 12 months with the 12 before, by severity-weighted load, returning `improving`, `steady`, `worsening` or `insufficient_data` (fewer than 4 dated incidents). Store it as `enrichment.safety.trend`. Search at least three years back so there is something to compare. Say that it reflects what was reported: a quiet year can mean fewer incidents or less coverage. Never present `insufficient_data` as "no change".

## Blend and confidence

```python
combine_safety({"station": s, "news": n, "property": p})   # weights 0.4 / 0.4 / 0.2, renormalised
```

Confidence: `high` with three parts, `medium` with two, `low` with one. Low confidence is shown in the report next to the number. With zero parts, `score: null`.

## What to write

```json
"safety": {
  "score": 74.2, "confidence": "medium",
  "parts": {"station": null, "news": 71.0, "property": 80.0},
  "evidence": [{"note": "...", "source_url": "https://...", "date": "2026-03-14"}],
  "searched": "news: 6 query forms, 24 months; station data: none published at ward level"
}
```

Always include `searched`. It lets the reader see that "no incidents" meant "I looked and found none", and how hard you looked.

## Also worth a line

Street lighting, late-night footfall, and what residents say (neighbourhood forums, society groups, reviews of the specific society) are useful colour for the written summary. Treat them as anecdote: quote or paraphrase with a source, and do not feed them into the score.
