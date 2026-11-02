import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const bin = path.join(root, "bin", "house-search.js");
const hs = path.join(root, "skills", "house-search", "scripts", "hs.py");

test("bundled skill and launcher exist", () => {
  assert.ok(existsSync(bin));
  assert.ok(existsSync(hs));
});

test("house-search.js runs hs.py normalize", () => {
  const run = spawnSync(process.execPath, [bin, "normalize", "--text", "2bhk in Indiranagar under 40k"], {
    cwd: root,
    encoding: "utf8",
  });
  assert.equal(run.status, 0, run.stderr || run.stdout);
  const data = JSON.parse(run.stdout);
  assert.ok(data.unit_types?.includes("2bhk"));
});

test("package.json declares bin and skill files", () => {
  const pkg = JSON.parse(readFileSync(path.join(root, "package.json"), "utf8"));
  assert.equal(pkg.name, "@vermauv/house-search");
  assert.ok(pkg.bin["house-search"]);
  assert.ok(pkg.files.some((f) => f.includes("skills/house-search")));
});
