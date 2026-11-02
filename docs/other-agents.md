# Using /house-search with other AI agents

## Cursor (Composer / Agent)

Cursor discovers skills from:

| Scope | Path |
|---|---|
| **This repo** | `.cursor/skills/house-search/` → symlink to `skills/house-search/` |
| **All projects** | `~/.cursor/skills/house-search/` (copy or symlink the whole folder) |

Install from a checkout:

```bash
mkdir -p .cursor/skills ~/.cursor/skills
ln -sf ../../skills/house-search .cursor/skills/house-search
rsync -a --exclude '__pycache__' --exclude '.venv' skills/house-search/ ~/.cursor/skills/house-search/
```

Restart Cursor or start a new Agent/Composer chat so the skill loads. Then try natural language such as “find me a 2bhk in Mahadevapura under 55k” or `/house-search`.

Agents without native `SKILL.md` discovery (Aider, or any LLM with custom instructions) can still use the skill.

## Option 1: Paste into custom instructions

Paste the contents of [`skills/house-search/SKILL.md`](../skills/house-search/SKILL.md) into your agent's custom instructions. Keep the `references/` folder reachable so the agent can read the step files the skill points to.

## Option 2: Reference as a file path

If your agent loads instructions from a file, point it at `path/to/skills/house-search/SKILL.md`.

## Option 3: Copy the skill folder

```bash
cp -r skills/house-search/ ~/.your-agent/skills/house-search/
```

## Google Antigravity

- **Project level:** symlink or copy `skills/house-search/` to `.agents/skills/house-search/`.
- **Global:** copy it to `~/.gemini/config/skills/house-search/`.

## Prerequisites

- Python 3.11+ (helpers are standard-library only)
- Web search and fetch available to the agent
- Optional: `GOOGLE_MAPS_API_KEY` for traffic multipliers and ambulance times
- The whole `skills/house-search/` folder, since the scripts, assets and references travel together
