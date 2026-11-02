# Step 5: Rank and deliver

## 1. Rank

```bash
python3 <skill-dir>/scripts/hs.py rank \
  --listings <output-dir>/enriched.json \
  --requirements <output-dir>/requirements.json \
  --sort overall --out <output-dir>/ranked.json
```

What the ranker does:

- **Excludes** listings that explicitly contradict a hard requirement (furnishing, unit type, property type, budget cap +5%, a must-have confirmed absent, too few bathrooms, too old) and lists them with reasons.
- **Scores** six components 0-100: safety, medical (best emergency hospital by ambulance time), commute, amenities match, metro, entertainment (malls). Default weights favour safety (0.30) and medical (0.25); see `assets/weights.default.json`.
- **Renormalises** over the components that were measured, giving `overall`. `coverage` and `confidence` say how much of the score is real. Because thin data can look flattering, the default sort uses `adjusted`: `overall` pulled toward a neutral 50 in proportion to the missing coverage. The report shows `overall`; say so if a thinly-checked home sits low for that reason, and offer to check it properly.
- **Breaks ties** by lower rent. `--sort safety` (or any component) re-sorts on that component alone.
- **Waterlogging** never changes the score. It only warns.

Pick `--sort` from what the person said. "Safety matters most" is `--sort safety`. "Close to hospitals" is `--sort medical`. If they gave a more nuanced weighting, write a weights JSON and pass `--weights`.

## 2. Write the report

```bash
python3 <skill-dir>/scripts/hs.py report \
  --ranked <output-dir>/ranked.json --requirements <output-dir>/requirements.json \
  --out-dir <output-dir> --locality "<locality>"
```

This writes `report.md` and a self-contained `report.html` (responsive, light and dark, user content escaped). Both show the ranked table, a card per listing, ⚠️ waterlogging warnings with sources, "ask the owner" lines for unverified must-haves, the excluded list with reasons, and the caveats.

Open the report once and look at it. Fix anything that reads wrong (a missing link, a number with no source) in the data and re-run; do not hand-edit the output.

## 3. Answer in chat

Lead with the answer, not the process. Roughly:

1. **One line** on what was searched: locality, type, budget, how many listings across how many sources, how many survived the filters.
2. **Top 3 to 5**, each as: title (linked), rent, and the three numbers that decided it (safety with confidence, ambulance time, one of metro/commute), plus ⚠️ where flagged. A small table works; prose for the reasoning.
3. **Warnings that matter**: waterlogging with its source, must-haves to confirm with the owner, thin-data listings.
4. **What you could not verify**: blocked sources, missing traffic data (no API key), app-only listings. Name them. If the table has any `n/a` cell (safety, ambulance, metro, mall, commute), say in one line **why** for each column, using the reasons in `enrichment.gaps` (for example: no Maps key, geocoder unreachable, commute not requested, no locality-specific incident data found). Never leave an `n/a` unexplained, and never describe it as "safe" or "none".
5. **Assumptions** you made, in one line.
6. **One next step**: widen the radius, change the sort, shortlist and compare two homes, or draft a message to an owner. Do not contact anyone yourself.

Link or attach `report.html`. Cite the sources behind safety and waterlogging claims.

## What a good answer does not do

- Present a safety score without its confidence.
- Say an area "is safe", "is not flood-prone", or "has no crime" because nothing was found.
- Convert distances to ambulance minutes without traffic data.
- Quote a rent from a search snippet that was never opened.
- Bury a ⚠️ below the fold.
- Show an `n/a` without saying why. The report prints each reason under the listing; if one reads "no reason recorded", go back to step 4 and fill in `enrichment.gaps`.

**Gate:** `report.md` and `report.html` exist; every ⚠️ has a cited source; the chat answer states confidence, assumptions, and what was not verified.
