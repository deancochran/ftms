import assert from "node:assert/strict";
import { writeFileSync } from "node:fs";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { integrity, requireIntegrity, verifyPublic } from "./verify-public.mjs";

test("public npm verification requires the exact tested bytes", () => {
  const expected = integrity(Buffer.from("tested archive"));
  assert.match(expected, /^sha512-/);
  assert.doesNotThrow(() => requireIntegrity(expected, integrity(Buffer.from("tested archive"))));
  assert.throws(() => requireIntegrity(expected, integrity(Buffer.from("different archive"))));
  assert.throws(() => requireIntegrity(expected, undefined));
});

for (const scenario of [
  "matching",
  "missing-then-matching",
  "wrong-metadata",
  "wrong-bytes",
  "consumer-failure",
  "registry-failure",
]) {
  test(`public verification: ${scenario}`, async () => {
    const root = await mkdtemp(path.join(tmpdir(), "ftms-public-test-"));
    const archive = path.join(root, "tested.tgz");
    const reportPath = path.join(root, "report.json");
    const bytes = Buffer.from("tested fixture");
    await writeFile(archive, bytes);
    const calls = [];
    let views = 0;
    const execute = (command, args, options) => {
      calls.push(args[0]);
      if (args[0] === "view") {
        views++;
        if (
          scenario === "registry-failure" ||
          (scenario === "missing-then-matching" && views === 1)
        ) {
          const error = new Error("registry error");
          error.stderr = scenario === "registry-failure" ? "E403" : "E404";
          throw error;
        }
        return JSON.stringify(scenario === "wrong-metadata" ? "sha512-wrong" : integrity(bytes));
      }
      if (args[0] === "pack") {
        writeFileSync(
          path.join(options.cwd, "public.tgz"),
          scenario === "wrong-bytes" ? "bad" : bytes,
        );
        return JSON.stringify([{ filename: "public.tgz" }]);
      }
      if (args[0] === "install") {
        assert.ok(args.includes("--ignore-scripts"));
        return "";
      }
      assert.equal(command, process.execPath);
      assert.equal(args[0], "consumer.mjs");
      if (scenario === "consumer-failure") throw new Error("consumer failed");
      return "";
    };
    try {
      const verification = verifyPublic(archive, reportPath, { execute, sleep: async () => {} });
      const passes = ["matching", "missing-then-matching"].includes(scenario);
      if (passes) await verification;
      else await assert.rejects(verification);
      assert.equal(JSON.parse(await readFile(reportPath, "utf8")).complete, passes);
      assert.equal(calls.includes("publish"), false);
      if (passes) assert.ok(calls.includes("consumer.mjs"));
      if (scenario === "missing-then-matching") assert.equal(views, 2);
      if (scenario === "registry-failure") assert.deepEqual(calls, ["view"]);
      if (["wrong-metadata", "wrong-bytes"].includes(scenario))
        assert.equal(calls.includes("install"), false);
    } finally {
      await rm(root, { recursive: true, force: true });
    }
  });
}
