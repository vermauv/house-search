# /house-search

**Say what home you want. Get the ones worth visiting.**

[`/house-search`](https://github.com/vermauv/house-search) is an **agent skill** plus a small **CLI**. You describe a rental in plain English; an agent searches rental portals, checks the neighbourhood, ranks what it finds, and writes a report. The CLI runs the same tested helpers (`normalize`, `geocode`, `rank`, `report`, …) without opening an IDE.

**Repository:** [github.com/vermauv/house-search](https://github.com/vermauv/house-search)

## What you get beyond portal filters

- **Safety** — public incident reporting and society-level security, with a confidence level (not a guarantee).
- **Hospital access** — nearest emergency-capable hospitals; **ambulance** time estimates in peak traffic when Maps data is available.
- **Metro** and **malls** — straight-line distance from each home.
- **Office commute** — typical weekday traffic to your office at the times you leave, as 1× / 2× / 3× / 4×+ vs free-flow.
- **Waterlogging** — ⚠️ when dated news ties the area to repeated flooding (never “proven safe” when nothing is found).

Example prompt:

```text
/house-search semi furnished 2.5bhk apartment in Mahadevapura with 2 wheeler parking,
gym, swimming pool, pets allowed, vastu compliant, east facing, under 55k
```

The skill understands furnishing, BHK, property type, budget, and [38 amenity keys](skills/house-search/references/amenities.md) (parking, lift, power backup, pets, gym, …). Listings can carry a **`notes`** array for portal-only detail (livability scores, deposit/all-in rent, “other units same building”, map-pin caveats); **`report.md` / `report.html` print those bullets**. If you paste a **listing URL** after a run, the agent should open it, append to `listings.json`, and re-run `rank` + `report` (see skill step 3b).

Run output goes in **`house-search-output/`** (gitignored): `requirements.json`, `listings.json`, `enriched.json`, `ranked.json`, `report.md`, `report.html`.

## Disclaimer

**This project is a research and detail aggregator, not a rental marketplace or broker.** It does not list properties, negotiate leases, verify owners, or handle payments. All listing data comes from third-party sites; URLs in the report are for you to open and confirm. Rankings and scores are indicative only, built from public sources available at run time.

**The authors and contributors are not responsible for any dispute, loss, or legal issue** arising from rentals you pursue based on this tool—including inaccurate or stale listings, portal scams, neighbourhood conditions, or commute times. Always verify rent, deposit, amenities, and paperwork on the portal or with the owner before paying or signing.

## Install the skill (agents)

**Recommended** — [`skills` CLI](https://github.com/vercel-labs/skills) (Cursor, Copilot, Gemini, Claude Code, opencode, and others):

```bash
npx skills add https://github.com/vermauv/house-search --skill house-search
```

<details>
<summary>No installer? Copy the skill directly.</summary>

```bash
git clone https://github.com/vermauv/house-search.git
# use skills/house-search/ from the clone, or copy it:
rsync -a --exclude '__pycache__' skills/house-search/ ~/.cursor/skills/house-search/
# or ~/.claude/skills/house-search/, etc.
```

Restart your agent after copying.
</details>

### Agent discovery paths

| Agent | Skill location |
|---|---|
| **Claude Code** | Copy or symlink to `skills/house-search/` → `.claude/skills/house-search/` |
| **Codex / Antigravity** | `.agents/skills/house-search/` (symlink when cloned from this repo) |
| **opencode** | `.opencode/skills/house-search/` (symlink when cloned from this repo) |
| **Cursor** | `skills/house-search/` in repo, or `~/.cursor/skills/house-search/` globally (`.cursor/` is local-only and gitignored) |
| **Other** | Point instructions at `skills/house-search/SKILL.md` — [`docs/other-agents.md`](docs/other-agents.md) |

On Windows, enable symlinks (`git config core.symlinks true`, Developer Mode) or copy `skills/house-search/` instead of relying on repo symlinks.

## CLI (`npx`, no agent required for helpers)

Python **3.11+** must be on your `PATH` as `python3` (or set `PYTHON`). The npm package ships the skill scripts and a launcher:

```bash
npx @vermauv/house-search --help
npx @vermauv/house-search normalize --text "2bhk furnished flat in Indiranagar under 40k"
npx @vermauv/house-search geocode "Mahadevapura, Bengaluru"
```

After `npm install -g @vermauv/house-search`, use `house-search` or `hs` instead of `npx`.

**Publish (maintainers, once per release):** log in with `npm login`, bump `version` in `package.json` and `plugin.json`, then `npm publish --access public` from the repo root. Scoped package `@vermauv/house-search` requires `--access public` on first publish.

## Requirements

- An agent that can follow `SKILL.md` (for the full workflow), **or** Python 3.11+ for CLI-only use.
- Web search / fetch in the agent; a browser tool helps for portals and Maps traffic fallback.
- **Optional:** `GOOGLE_MAPS_API_KEY` (Geocoding + Routes) for traffic multipliers and ambulance times. Without it, the skill still runs with OpenStreetMap and manual Maps fallback where possible.

## How it works

| Step | Agent | `hs.py` / `npx @vermauv/house-search` |
|---|---|---|
| 1. Understand | Parses your sentence; ≤3 questions | `normalize` |
| 2. Locate | Confirms locality, radius | `geocode` |
| 3. Discover | Searches portals; can add a URL you send later | (browser + judgement) |
| 4. Check | Safety, waterlogging, hospitals, commute | `nearby`, `traffic`, `waterlog`, `safety-news`, … |
| 5. Rank & report | Answer + files | `rank`, `report` |

## What it will not do

- Invent listings or numbers; silence is flagged, not assumed safe.
- Score neighbourhoods by demographics—only incidents and property security.
- Log in, bypass CAPTCHAs, or scrape at volume; blocked sources are reported with a link for you.
- Contact owners or store broker phone numbers.

## Develop & test

```bash
# Python unit tests (offline)
cd skills/house-search/scripts && pip install pytest && pytest -q

# Repo checks (frontmatter, amenities.md, symlinks, npm package layout)
python3 scripts/check_repo.py

# npm CLI smoke tests (Node 18+)
node --test test/npm-cli.test.js

# Or everything CI runs:
npm test
```

CI: `.github/workflows/test.yml` (Python 3.12, Node 20, `check_repo`, pytest, npm tests).

## Repo layout

- `skills/house-search/` — `SKILL.md`, `references/`, `scripts/hs.py`, `assets/`
- `bin/house-search.js` — npm entrypoint → `hs.py`
- `package.json` — `@vermauv/house-search` on npm
- `plugin.json`, `.claude-plugin/`, `.codex-plugin/` — optional agent plugin manifests (for tooling; install via `skills` CLI or copy above)
- `.claude/`, `.agents/`, `.opencode/` — symlinks into `skills/house-search/`
- `scripts/check_repo.py` — sanity checks
- `docs/other-agents.md` — wiring notes for other products

## Limits worth knowing

- Safety is relative; station-level police data is often unavailable → lower confidence, stated in the report.
- Ambulance times assume peak driving + siren factor; dispatch delay excluded.
- Waterlogging uses live news plus a small seed file; “none found” ≠ no risk.
- Portals change often; app-only inventory is called out, not pretended searched.

## License

MIT — see [LICENSE](LICENSE).
