# /house-search

**Say what home you want. Get the ones worth visiting.**

`/house-search` is an agent skill. You describe a rental in your own words; it finds listings across the rental platforms, locates the area on the map, and ranks what it finds on the things portals do not show you:

- **Safety**, from police statistics, news incident reports and society-level security, with a confidence level.
- **Hospital access**, and how soon an **ambulance** could reach the home in peak traffic.
- **Metro** and **malls** nearby.
- **Office commute**: Google Maps traffic from each home to your office at the time you leave, shown as 1x, 2x, 3x or 4x the normal trip.
- **Waterlogging**: a ⚠️ on any area that news reports repeatedly link to flooding or waterlogged roads.

```text
/house-search semi furnished 2.5bhk apartment in Mahadevapura with 2 wheeler parking,
gym, swimming pool, pets allowed, vastu compliant, east facing, under 55k
```

It understands furnishing (unfurnished, semi-furnished, furnished), unit type (studio, 1RK, 1BHK, 2BHK, 2.5BHK, 3BHK, 5BHK...), property type (apartment, house, villa, bungalow, serviced apartment) and 38 amenities from parking and gated community to jogging track and rain water harvesting ([full list](skills/house-search/references/amenities.md)).

## Install

Replace `<owner>` with the GitHub account hosting this repository.

**Claude Code:**

```bash
/plugin marketplace add <owner>/house-search
/plugin install house-search@house-search
```

**Codex:**

```bash
codex plugin marketplace add <owner>/house-search
codex plugin add house-search@house-search
```

**Any other agent** (Cursor, Copilot, Gemini CLI, opencode, and more), via the [`skills`](https://github.com/vercel-labs/skills) CLI:

```bash
npx skills add https://github.com/<owner>/house-search --skill house-search
```

<details>
<summary>No installer? Copy the skill directly.</summary>

```bash
rsync -a --exclude '__pycache__' skills/house-search/ ~/.claude/skills/house-search/
```

Restart your agent after copying.
</details>

### Also works with

The repo exposes the skill at each agent's standard discovery path via symlinks.

| Agent | How it discovers |
|---|---|
| **Claude Code** | `.claude/skills/house-search/` (or the plugin install above) |
| **Codex CLI, Antigravity** | `.agents/skills/house-search/` |
| **opencode** | `.opencode/skills/house-search/` |
| **Other agents** | Point custom instructions at `skills/house-search/SKILL.md`; see [`docs/other-agents.md`](docs/other-agents.md) |

On Windows, symlinks need `git config core.symlinks true` and Developer Mode; otherwise copy `skills/house-search/` into the agent's skills folder.

## Requirements

- An agent that supports Agent Skills (or can follow `SKILL.md` instructions).
- Python 3.11+ for the helper scripts. They use only the standard library; nothing to install.
- Web search and page fetch in your agent. A browser tool helps with portals that need filters set by hand.
- **Optional but recommended:** `GOOGLE_MAPS_API_KEY` with the Geocoding and Routes APIs enabled. It powers the traffic multipliers and ambulance times. Without it, the skill still runs: places come from OpenStreetMap and traffic falls back to reading Google Maps in a browser, or is left out and said so.

## How it works

The agent does the reading and judging; small tested scripts do the parts that must be exact.

| Step | Agent | Script (`skills/house-search/scripts/hs.py`) |
|---|---|---|
| 1. Understand | Reads your sentence, asks at most three questions | `normalize`: canonical furnishing, BHK, amenities, budget |
| 2. Locate | Confirms the locality, picks the radius | `geocode`: Google or OpenStreetMap, flags ambiguity |
| 3. Discover | Searches portals, normalises, de-duplicates | none (judgement and browsing) |
| 4. Check | Researches safety and waterlogging, verifies hospitals | `nearby`, `ambulance`, `traffic`, `waterlog`, `safety-news` |
| 5. Rank | Writes the answer | `rank`, `report`: scores, filters, `report.md` + `report.html` |

Output lands in `house-search-output/`: requirements, listings, enriched data, ranked results, and a report you can open or share.

## What it will not do

- Invent listings or numbers. Every figure has a source, or is left out and flagged.
- Call an area "safe" because nothing was found. The wording is "none found".
- Judge neighbourhoods by who lives there. Safety is scored from incidents and security only.
- Log in, solve CAPTCHAs or bypass blocks. Blocked sources are reported so you can open them yourself.
- Contact owners or brokers for you, or store their phone numbers.

## Develop

```bash
cd skills/house-search/scripts
pip install pytest && pytest -q          # unit tests, no network needed
python3 hs.py normalize --text "2bhk furnished flat in Indiranagar under 40k"
cd ../../.. && python3 scripts/check_repo.py   # frontmatter, links, manifests, symlinks
```

Network calls go through one injectable transport, so every module is tested offline.

## What's in this repo

- `skills/house-search/`: `SKILL.md`, `references/` (one file per step, plus sources, safety, waterlogging, data model, amenities), `scripts/`, `assets/`
- `plugin.json`: portable Agent Plugins manifest
- `.claude-plugin/`, `.codex-plugin/`: Claude Code and Codex manifests; `marketplace.json` is the shared catalogue
- `.claude/`, `.agents/`, `.opencode/`: symlinks to the skill for agent discovery
- `scripts/check_repo.py`: repo sanity checks
- `docs/`: notes for other agents

## Limits worth knowing

- Safety is a relative indicator from public evidence, not a guarantee. Fine-grained police data is often unpublished, in which case confidence drops and the report says so.
- Ambulance times are estimates from peak-hour road traffic with an assumed siren factor; call handling and dispatch delay are not included.
- `assets/waterlogging-seed.json` is a small sourced starter list. The live news search is the real check.
- Rental platforms change their pages and access rules often; app-only listings cannot be searched.

## License

MIT
