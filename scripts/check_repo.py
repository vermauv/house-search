#!/usr/bin/env python3
"""Repo sanity checks for the house-search skill plugin."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "house-search"
SKILL_SCRIPTS = SKILL / "scripts"
VOCAB = SKILL_SCRIPTS / "housesearch" / "vocab.py"
AMENITIES_MD = SKILL / "references" / "amenities.md"

SYMLINKS = (
    ROOT / ".claude" / "skills" / "house-search",
    ROOT / ".agents" / "skills" / "house-search",
    ROOT / ".opencode" / "skills" / "house-search",
)

GROUP_TITLES = {
    "parking": "Parking",
    "society": "Safety and society",
    "utilities": "Utilities",
    "recreation": "Recreation",
    "sports": "Sports",
    "features": "Household policies and features",
}


def _fail(msg: str) -> None:
    print(f"check_repo: {msg}", file=sys.stderr)
    sys.exit(1)


def _load_vocab_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("housesearch_vocab", VOCAB)
    if spec is None or spec.loader is None:
        _fail(f"cannot import {VOCAB}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def render_amenities_md(vocab_mod) -> str:
    amenities = vocab_mod.AMENITIES
    default_must = ", ".join(f"`{k}`" for k in sorted(vocab_mod.DEFAULT_MUST))
    lines = [
        "# Amenities",
        "",
        "Canonical amenity keys. This file is generated from "
        "`skills/house-search/scripts/housesearch/vocab.py`, which is the source of truth; "
        "`scripts/check_repo.py` fails if they drift. Regenerate with "
        "`python3 scripts/check_repo.py --write-amenities`.",
        "",
        "Use these keys in `requirements.json` and in each listing's `amenities` / "
        "`amenities_absent`. Portals use many spellings; the third column lists the phrases "
        "the helper recognises, and you should map other wording by judgement.",
        "",
        f"Default must-haves (deal-breakers unless the person says otherwise): {default_must}.",
        "",
        "Not amenity keys, because they are fields: property age (`age_years`), area "
        "(`area_sqft`), floor, bathrooms, main-door facing (`facing`), furnishing, rent. "
        'Intent such as "lake view" goes in `notes`.',
        "",
    ]
    by_group: dict[str, list[tuple[str, str, list[str]]]] = {}
    for key, (label, group, syns) in amenities.items():
        by_group.setdefault(group, []).append((key, label, syns))
    for group in ("parking", "society", "utilities", "recreation", "sports", "features"):
        items = by_group.get(group, [])
        if not items:
            continue
        lines.append(f"## {GROUP_TITLES.get(group, group.title())}")
        lines.append("")
        lines.append("| Key | Label | Recognised phrases |")
        lines.append("|---|---|---|")
        for key, label, syns in sorted(items, key=lambda x: x[0]):
            phrase = ", ".join(syns)
            lines.append(f"| `{key}` | {label} | {phrase} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def check_amenities(vocab_mod) -> None:
    expected = render_amenities_md(vocab_mod)
    if not AMENITIES_MD.is_file():
        _fail(f"missing {AMENITIES_MD.relative_to(ROOT)}")
    if AMENITIES_MD.read_text(encoding="utf-8") != expected:
        _fail(
            f"{AMENITIES_MD.relative_to(ROOT)} is out of date; "
            "run python3 scripts/check_repo.py --write-amenities"
        )


def check_skill_frontmatter() -> None:
    skill_md = SKILL / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        _fail("SKILL.md must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        _fail("SKILL.md frontmatter not closed")
    fm = text[4:end]
    if 'name: house-search' not in fm and 'name: "house-search"' not in fm:
        _fail("SKILL.md frontmatter must set name: house-search")
    if "description:" not in fm:
        _fail("SKILL.md frontmatter must include description")


def check_reference_links() -> None:
    skill_md = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for match in re.finditer(r"\[[^\]]+\]\((references/[^)]+)\)", skill_md):
        rel = match.group(1)
        path = SKILL / rel
        if not path.is_file():
            _fail(f"SKILL.md link missing file: {rel}")


def check_symlinks() -> None:
    target = SKILL.resolve()
    for link in SYMLINKS:
        if not link.is_symlink():
            _fail(f"expected symlink: {link.relative_to(ROOT)}")
        if link.resolve() != target:
            _fail(f"symlink points wrong: {link.relative_to(ROOT)}")


def check_npm_package() -> None:
    pkg_path = ROOT / "package.json"
    if not pkg_path.is_file():
        _fail("missing package.json for @vermauv/house-search npm package")
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    if pkg.get("name") != "@vermauv/house-search":
        _fail("package.json name must be @vermauv/house-search")
    bin_rel = (pkg.get("bin") or {}).get("house-search")
    if not bin_rel:
        _fail("package.json must declare bin.house-search")
    bin_path = ROOT / bin_rel
    if not bin_path.is_file():
        _fail(f"npm bin missing: {bin_rel}")
    hs = ROOT / "skills" / "house-search" / "scripts" / "hs.py"
    if not hs.is_file():
        _fail(f"missing bundled helper: {hs.relative_to(ROOT)}")


def check_manifests() -> None:
    for rel in ("plugin.json", ".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/marketplace.json"):
        path = ROOT / rel
        if not path.is_file():
            _fail(f"missing manifest: {rel}")
        json.loads(path.read_text(encoding="utf-8"))


def check_no_root_duplicates() -> None:
    stale = [
        ROOT / "hs.py",
        ROOT / "report.py",
        ROOT / "SKILL.md",
        ROOT / "house-search",
        ROOT / "references",
        ROOT / "assets",
    ]
    found = [p.relative_to(ROOT) for p in stale if p.exists()]
    if found:
        _fail(f"remove stale paths at repo root: {', '.join(str(p) for p in found)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-amenities", action="store_true", help="regenerate references/amenities.md")
    args = parser.parse_args()
    vocab_mod = _load_vocab_module()
    if args.write_amenities:
        AMENITIES_MD.write_text(render_amenities_md(vocab_mod), encoding="utf-8")
        print(f"wrote {AMENITIES_MD.relative_to(ROOT)}")
        return 0
    check_no_root_duplicates()
    check_skill_frontmatter()
    check_reference_links()
    check_symlinks()
    check_npm_package()
    check_manifests()
    check_amenities(vocab_mod)
    print("check_repo: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
