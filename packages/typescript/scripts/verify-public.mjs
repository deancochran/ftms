// Read-only registry verification. Never publishes or accepts different release bytes.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { pathToFileURL } from "node:url";

export function integrity(bytes) {
  return `sha512-${createHash("sha512").update(bytes).digest("base64")}`;
}

export function requireIntegrity(expected, actual) {
  assert.equal(actual, expected, "public npm archive differs from the tested archive");
}

export async function verifyPublic(
  archive,
  reportPath,
  { execute = execFileSync, sleep = delay } = {},
) {
  const manifest = JSON.parse(await readFile(new URL("../package.json", import.meta.url), "utf8"));
  const expected = integrity(await readFile(archive));
  const report = {
    name: manifest.name,
    version: manifest.version,
    integrity: expected,
    complete: false,
  };
  const temporary = await mkdtemp(path.join(tmpdir(), "ftms-npm-public-"));
  const run = (args) =>
    execute(process.platform === "win32" ? "npm.cmd" : "npm", args, {
      cwd: temporary,
      encoding: "utf8",
      timeout: 120_000,
      env: {
        ...process.env,
        npm_config_cache: path.join(temporary, "cache"),
        npm_config_registry: "https://registry.npmjs.org/",
      },
    });
  try {
    // Registry propagation can lag upload; only missing versions are retried.
    const spec = `${manifest.name}@${manifest.version}`;
    let remote;
    for (let attempt = 0; attempt < 6; attempt++) {
      try {
        remote = JSON.parse(run(["view", spec, "dist.integrity", "--json"]));
        break;
      } catch (error) {
        if (attempt === 5 || !/E404/.test(String(error.stderr))) throw error;
        await sleep(10_000);
      }
    }
    requireIntegrity(expected, remote);
    const packed = JSON.parse(run(["pack", spec, "--ignore-scripts", "--json"]));
    assert.equal(packed.length, 1);
    const filename = packed[0].filename;
    assert.equal(path.basename(filename), filename);
    const publicArchive = path.join(temporary, filename);
    requireIntegrity(expected, integrity(await readFile(publicArchive)));
    await writeFile(path.join(temporary, "package.json"), '{"private":true,"type":"module"}\n');
    run([
      "install",
      publicArchive,
      "--ignore-scripts",
      "--no-audit",
      "--no-fund",
      "--package-lock=false",
    ]);
    await writeFile(
      path.join(temporary, "consumer.mjs"),
      `
import assert from "node:assert/strict";
import { decodeFtmsFeatures } from ${JSON.stringify(manifest.name)};
assert.equal(decodeFtmsFeatures(new Uint8Array(8)).ok, true);
for (const suffix of ["conformance/v1", "conformance/schema", "conformance/v1/schema"]) {
  const value = await import(${JSON.stringify(manifest.name)} + "/" + suffix, { with: { type: "json" } });
  assert.ok(value.default);
}
`,
    );
    execute(process.execPath, ["consumer.mjs"], { cwd: temporary, timeout: 30_000 });
    report.complete = true;
    report.installedConsumer = true;
  } finally {
    await mkdir(path.dirname(reportPath), { recursive: true });
    await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`);
    await rm(temporary, { recursive: true, force: true });
  }
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [archive, report] = process.argv.slice(2);
  if (!archive || !report) throw new Error("usage: node verify-public.mjs ARCHIVE REPORT");
  await verifyPublic(archive, report);
}
