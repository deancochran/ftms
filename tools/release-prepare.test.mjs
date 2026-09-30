import assert from "node:assert/strict";
import test from "node:test";
import { ports, readiness, validateMetadata } from "./release-prepare.mjs";

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
