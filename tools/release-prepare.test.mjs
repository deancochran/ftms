import assert from "node:assert/strict";
import test from "node:test";
import { ports, readiness, validateMetadata, validNuGetVersion } from "./release-prepare.mjs";

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
    "v1.2.3-beta.1",
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
