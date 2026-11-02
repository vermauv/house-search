# Step 1: Understand the request

Turn a sentence into `requirements.json`. The deterministic helper does the boring 80%; you do the judgement.

## 1. Run the helper

```bash
python3 <skill-dir>/scripts/hs.py normalize --text "<the person's words, verbatim>"
```

It returns canonical values for furnishing, unit types, property types, budget, facing, area, bathrooms, age, floor and amenities (split into `must` and `nice`), plus `unmapped` and `assumptions`. It cannot read the locality or city; you add those.

Canonical values:

| Field | Values |
|---|---|
| `furnishing` | `unfurnished`, `semi_furnished`, `furnished` |
| `unit_types` | `studio`, `1rk`, `1bhk`, `2bhk`, `2.5bhk`, `3bhk`, `4bhk`, `5bhk` (any `N`/`N.5` + `bhk`) |
| `property_types` | `apartment`, `independent_house`, `villa`, `bungalow`, `serviced_apartment`, `builder_floor` |
| `facing` | `north`, `south`, `east`, `west`, `north_east`, `north_west`, `south_east`, `south_west` |
| amenity keys | see [amenities.md](amenities.md) |

"Flat" means `apartment`. "House" means `independent_house`. If the person lists several unit types or property types, keep all of them; they are alternatives.

## 2. Fill the gaps yourself

Add to the JSON:

- `locality`: what the person named (e.g. "Mahadevapura"). May be several.
- `city`: from the text, else from context, else ask.
- `original_text`: their words, verbatim.
- Anything the helper left in `unmapped`. Map it by judgement ("lake view" is not an amenity key: keep it as a free-text `notes` entry and use it when reading listings), or ask.

**Must vs nice.** The helper treats parking and pets as must-haves by default (they are the usual deal-breakers) and everything else as nice-to-have unless the person used words like "must", "need" or "essential". Override when the context says otherwise. A wrong must-have excludes good homes; a wrong nice-to-have only reorders them, so when unsure choose nice-to-have and say so.

**Structural fields are hard filters:** unit type, property type, furnishing, locality, budget cap. Everything else shapes the ranking.

## 3. Ask, once

Use `AskUserQuestion` if available, otherwise one plain message. At most three questions, and only the ones that apply:

1. **City**, if the locality is ambiguous (several "Mahadevapura"s) and the text does not say.
2. **Budget**, if absent. Offer ranges, accept "no limit".
3. **Commute.** Always offer, once: *"Want me to check Google Maps traffic from each home to your office at the time you leave? I'll show whether the trip stays normal or stretches to 2x, 3x or 4x on a weekday. If yes: office address and when you usually leave home (and leave office, if different)."* Record `commute: {office, depart_home, depart_office}` or `commute: null`.

Do not ask about amenities the person already gave, or about things with a sensible default (radius, sort order). If the person is not around to answer, take the default, record it under `assumptions`, and continue.

## 4. Echo it back, briefly

One line, in the person's own words where possible, e.g. *"Semi-furnished 2.5BHK apartment in Mahadevapura, Bengaluru, up to ₹55,000, must have 2-wheeler parking and pets allowed; nice to have gym, pool, vastu. Searching now."* This lets them correct you cheaply. Then continue; do not wait for a "yes".

## Output

`<output-dir>/requirements.json`, see [data-model.md](data-model.md#requirements).

**Gate:** locality, city, at least one unit type, and a budget (or explicit "no limit") are present; `unmapped` is empty or each item has been resolved.
