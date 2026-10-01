#!/usr/bin/env node
// Release readiness is intentionally read-only. Version/changelog edits have
// ecosystem-specific lockfile and metadata consequences and are reviewed in PRs.
import { readFile } from "node:fs/promises";
import { portCatalog, portInfo, releaseTag } from "./port-catalog.mjs";

// Deliberately narrower than NuGet's accepted input: VERSION must already be
// canonical. NuGet ignores build metadata and normalizes abbreviated versions.
export function validNuGetVersion(version) {
  return (
    version === version.trim() &&
    /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(?:0|[1-9]\d*|\d*[a-z-][0-9a-z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-z-][0-9a-z-]*))*)?$/.test(
      version,
    ) &&
    version
      .split("-")[0]
      .split(".")
      .every((part) => Number(part) <= 2147483647)
  );
}

const formats = {
  typescript: {
    match: (s) => JSON.parse(s).version,
  },
  python: {
    match: (s) => s.match(/^version\s*=\s*"([^"]+)"/m)?.[1],
    valid: (v) =>
      /^[0-9]+(?:\.[0-9]+)*(?:(a|b|rc)[0-9]+)?(?:\.post[0-9]+)?(?:\.dev[0-9]+)?$/.test(v),
  },
  kotlin: {
    match: (s) => s.trim(),
  },
  c: {
    match: (s) => s.trim(),
  },
  rust: {
    match: (s) => s.match(/^version\s*=\s*"([^"]+)"/m)?.[1],
  },
  swift: {
    match: (s) => s.trim(),
  },
  csharp: {
    match: (s) => s.trim(),
    valid: validNuGetVersion,
  },
  dart: {
    match: (s) => s.match(/^version:\s*([^\s#]+)\s*$/m)?.[1],
  },
  go: {
    // Go has no manifest package-version field: the release heading is the
    // candidate identity; only the nested-module tag establishes publication.
    match: (s) => s.match(/^## (\S+)(?: — .+)?$/m)?.[1],
  },
};

export const ports = Object.fromEntries(
  Object.keys(portCatalog).map((port) => {
    const info = portInfo(port);
    return [port, { ...formats[port], version: info.versionSource, changelog: info.changelog }];
  }),
);

export function validateMetadata(port, source, changelog, candidate) {
  const spec = ports[port];
  if (!spec) throw new Error(`unknown port: ${port}`);
  const version = spec.match(source);
  const semver =
    /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$/;
  if (typeof version !== "string" || !(spec.valid ? spec.valid(version) : semver.test(version)))
    throw new Error(`invalid ${port} manifest version`);
  const headings = port === "typescript" ? [`## ${version}`, `## [${version}]`] : [`## ${version}`];
  if (
    !changelog
      .split(/\r?\n/)
      .some((line) =>
        headings.some(
          (heading) =>
            line === heading ||
            (port === "typescript" && line.startsWith(`${heading} - `)) ||
            (port === "go" && line.startsWith(`${heading} — `)),
        ),
      )
  )
    throw new Error(`missing changelog heading for ${version}`);
  if (candidate && candidate !== version)
    throw new Error(
      "readiness command does not edit versions; update package metadata and lockfiles in a reviewed PR first",
    );
  return {
    port,
    version,
    tag: releaseTag(port, version),
    remoteMutation: false,
  };
}
export async function readiness(port, candidate) {
  const spec = ports[port];
  if (!spec) throw new Error(`unknown port: ${port}`);
  return validateMetadata(
    port,
    await readFile(spec.version, "utf8"),
    await readFile(spec.changelog, "utf8"),
    candidate,
  );
}
// Report every package even if one fails; metadata success is not publication evidence.
export async function allReadiness(check = readiness) {
  const packages = await Promise.all(
    Object.keys(ports).map(async (port) => {
      try {
        return { ...(await check(port)), status: "passed" };
      } catch (error) {
        return { port, status: "failed", error: error.message };
      }
    }),
  );
  return {
    schemaVersion: 1,
    scope: "metadata-only",
    remoteMutation: false,
    passed: packages.every((result) => result.status === "passed"),
    packages,
  };
}
if (import.meta.url === `file://${process.argv[1]}`) {
  const [port, supplied, suppliedMode, ...extra] = process.argv.slice(2);
  const candidate = supplied === "--dry-run" ? undefined : supplied;
  const mode = supplied === "--dry-run" ? supplied : suppliedMode;
  if (
    !port ||
    extra.length ||
    (supplied === "--dry-run" && suppliedMode !== undefined) ||
    ![undefined, "--dry-run"].includes(mode) ||
    (port === "all" && candidate)
  )
    throw new Error("usage: pnpm release:prepare PORT|all [VERSION] [--dry-run] (read-only)");
  const result = port === "all" ? await allReadiness() : await readiness(port, candidate);
  console.log(JSON.stringify(result, null, 2));
  if (result.passed === false) process.exitCode = 1;
}
