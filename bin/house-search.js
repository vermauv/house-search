#!/usr/bin/env node
/**
 * npx @vermauv/house-search — runs skills/house-search/scripts/hs.py (Python 3.11+).
 * Agent workflow lives in SKILL.md; this CLI is for normalize, geocode, rank, report, etc.
 */
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const hs = path.join(root, "skills", "house-search", "scripts", "hs.py");

if (!existsSync(hs)) {
  console.error("house-search: missing bundled skill at", hs);
  process.exit(1);
}

const py = process.env.PYTHON ?? "python3";
const result = spawnSync(py, [hs, ...process.argv.slice(2)], {
  stdio: "inherit",
  env: process.env,
});

if (result.error) {
  console.error("house-search:", result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);
