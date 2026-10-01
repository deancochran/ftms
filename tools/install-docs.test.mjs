import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { check, installCommand, published, render, validateEvidence } from "./install-docs.mjs";

test("committed installation guidance matches public records", check);
test("prereleases require explicit opt-in; stable releases remove it", () => {
  assert.match(installCommand("python", published.python), /--pre /);
  assert.match(installCommand("csharp", published.csharp), /--prerelease/);
  assert.equal(
    installCommand("python", { version: "1.0.0" }),
    "python -m pip install deancochran-ftms",
  );
  assert.equal(
    installCommand("csharp", { version: "1.0.0" }),
    "dotnet add package DeanCochran.Ftms",
  );
});
test("all nine ports have instructions; invalid records fail closed", () => {
  assert.equal((render().match(/^### /gm) ?? []).length, 9);
  assert.throws(() => render({}));
  assert.throws(() => render({ ...published, swift: { ...published.swift, revision: "main" } }));
  assert.throws(() => render({ ...published, c: { ...published.c, sha256: "unknown" } }));
  assert.throws(() => installCommand("unknown", {}));
});

test("stable rendered guidance drops prerelease flags and explanation", () => {
  const text = render({
    ...published,
    python: { ...published.python, version: "1.0.0" },
    csharp: { ...published.csharp, version: "1.0.0" },
  });
  assert.doesNotMatch(text, /--pre|command explicitly includes prereleases/);
});

test("evidence rejects another port's anchor, stale versions and incorrect identities", () => {
  const ledger = readFileSync(new URL("../docs/released-packages.md", import.meta.url), "utf8");
  for (const [port, changes] of [
    ["go", { evidence: published.rust.evidence }],
    ["rust", { version: "0.1.0" }],
    ["swift", { revision: "a".repeat(40) }],
    ["c", { sha256: "b".repeat(64) }],
  ]) {
    assert.throws(() =>
      validateEvidence({ ...published, [port]: { ...published[port], ...changes } }, ledger),
    );
  }
});
