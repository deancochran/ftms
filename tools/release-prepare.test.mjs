import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import test from "node:test";
import {
  allReadiness,
  ports,
  readiness,
  validateMetadata,
  validNuGetVersion,
} from "./release-prepare.mjs";

test("CLI rejects extra arguments after dry-run", () => {
  const result = spawnSync(process.execPath, [
    "tools/release-prepare.mjs",
    "all",
    "--dry-run",
    "unexpected",
  ]);
  assert.notEqual(result.status, 0);
});

test("1.0 metadata uses port-specific tags without changing native versions", () => {
  assert.equal(
    validateMetadata("typescript", '{"version":"1.0.0"}', "## 1.0.0").tag,
    "typescript-v1.0.0",
  );
  assert.equal(validateMetadata("typescript", '{"version":"0.4.0"}', "## 0.4.0").tag, "v0.4.0");
  assert.equal(validateMetadata("go", "## 1.0.0", "## 1.0.0").tag, "packages/go/v1.0.0");
});

test("all-package readiness includes every implemented distribution", async () => {
  const result = await allReadiness();
  assert.equal(result.passed, true);
  assert.equal(result.scope, "metadata-only");
  assert.deepEqual(result.packages.map((p) => p.port).sort(), [
    "c",
    "csharp",
    "dart",
    "go",
    "kotlin",
    "python",
    "rust",
    "swift",
    "typescript",
  ]);
  assert.equal(result.packages.find((p) => p.port === "dart").tag, "dart-v0.1.0");
  assert.equal(result.packages.find((p) => p.port === "go").tag, "packages/go/v0.1.0");
});

test("all-package readiness retains failures and continues independent checks", async () => {
  const result = await allReadiness(async (port) => {
    if (port === "c") throw new Error("missing changelog");
    return readiness(port);
  });
  assert.equal(result.passed, false);
  assert.equal(result.packages.length, 9);
  assert.equal(result.packages.find((p) => p.port === "c").error, "missing changelog");
  assert.equal(result.packages.filter((p) => p.status === "passed").length, 8);
});

for (const port of Object.keys(ports))
  test(`${port} readiness reads current metadata`, async () => {
    const result = await readiness(port);
    assert.equal(result.port, port);
    assert.equal(result.remoteMutation, false);
  });
test("readiness refuses candidate mutation", async () =>
  assert.rejects(readiness("python", "9.9.9")));
test("requires exact version and changelog identity", () => {
  assert.throws(() => validateMetadata("c", "not-a-version", "## not-a-version"));
  assert.throws(() => validateMetadata("c", "1.0.0", "## 1.0.01"));
  assert.throws(() => validateMetadata("c", "01.0.0", "## 01.0.0"));
  assert.throws(() => validateMetadata("python", 'version = "1.0.0-invalid"', "## 1.0.0-invalid"));
  assert.equal(
    validateMetadata("typescript", '{"version":"1.2.3-beta.1"}', "## [1.2.3-beta.1] - 2026-09-30")
      .tag,
    "typescript-v1.2.3-beta.1",
  );
});

test("C# accepts only canonical NuGet release identities", () => {
  for (const version of ["0.1.0-alpha.1", "0.1.0", "1.2.3-rc.2"]) {
    assert.equal(validNuGetVersion(version), true, version);
    assert.equal(validateMetadata("csharp", version, `## ${version}`).tag, `csharp-v${version}`);
  }
  for (const version of [
    "1.2",
    "1.2.3.0",
    "01.2.3",
    "1.02.3",
    "1.2.03",
    "1.2.3+build.7",
    "1.2.3-alpha.01",
    "1.2.3-Alpha.1",
    "2147483648.0.0",
    "1.2.3-",
    "1.2.3\n",
  ]) {
    assert.equal(validNuGetVersion(version), false, version);
  }
  assert.throws(() => validateMetadata("csharp", "1.2.3+build.7", "## 1.2.3+build.7"));
});

test("Go release identity comes from its changelog and nested-module tag", () => {
  assert.equal(
    validateMetadata("go", "## 1.2.3 — 2026-09-30", "## 1.2.3 — 2026-09-30").tag,
    "packages/go/v1.2.3",
  );
  assert.throws(() => validateMetadata("go", "go 1.24", "## 1.24.0"));
  assert.throws(() => validateMetadata("go", "## 1.2.3", "## 1.2.30"));
});
