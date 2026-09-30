import assert from "node:assert/strict";
import test from "node:test";
import { publicationDecision, releaseChannel } from "./npm-release.mjs";

test("selects npm channels", () => {
  assert.equal(releaseChannel("1.2.3"), "latest");
  assert.equal(releaseChannel("1.2.3-rc.1"), "next");
  assert.equal(releaseChannel("1.2.3+build-with-hyphens"), "latest");
  assert.throws(() => releaseChannel("invalid"));
});
test("publishes only absent version and rejects bad integrity", () => {
  assert.deepEqual(publicationDecision("", "sha512-a"), { publish: true, reason: "absent" });
  assert.deepEqual(publicationDecision("sha512-a", "sha512-a"), {
    publish: false,
    reason: "identical",
  });
  assert.throws(() => publicationDecision("sha512-b", "sha512-a"));
  assert.throws(() => publicationDecision(undefined, "sha512-a"));
});
