#!/usr/bin/env node
// Release readiness is intentionally read-only. Version/changelog edits have
// ecosystem-specific lockfile and metadata consequences and are reviewed in PRs.
import { readFile } from "node:fs/promises";

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

export const ports = {
  typescript: {
    version: "packages/typescript/package.json",
    changelog: "packages/typescript/CHANGELOG.md",
    match: (s) => JSON.parse(s).version,
  },
  python: {
    version: "packages/python/pyproject.toml",
    changelog: "packages/python/CHANGELOG.md",
    match: (s) => s.match(/^version\s*=\s*"([^"]+)"/m)?.[1],
    valid: (v) =>
      /^[0-9]+(?:\.[0-9]+)*(?:(a|b|rc)[0-9]+)?(?:\.post[0-9]+)?(?:\.dev[0-9]+)?$/.test(v),
  },
  kotlin: {
    version: "packages/kotlin/VERSION",
    changelog: "packages/kotlin/CHANGELOG.md",
    match: (s) => s.trim(),
  },
  c: {
    version: "packages/c/VERSION",
    changelog: "packages/c/CHANGELOG.md",
    match: (s) => s.trim(),
  },
  rust: {
    version: "packages/rust/Cargo.toml",
    changelog: "packages/rust/CHANGELOG.md",
    match: (s) => s.match(/^version\s*=\s*"([^"]+)"/m)?.[1],
  },
  swift: {
    version: "packages/swift/VERSION",
    changelog: "packages/swift/CHANGELOG.md",
    match: (s) => s.trim(),
  },
  csharp: {
    version: "packages/csharp/VERSION",
    changelog: "packages/csharp/CHANGELOG.md",
    match: (s) => s.trim(),
    valid: validNuGetVersion,
  },
};

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
            line === heading || (port === "typescript" && line.startsWith(`${heading} - `)),
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
    tag: port === "typescript" ? `v${version}` : `${port}-v${version}`,
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
if (import.meta.url === `file://${process.argv[1]}`) {
  const [port, supplied, suppliedMode] = process.argv.slice(2);
  const candidate = supplied === "--dry-run" ? undefined : supplied;
  const mode = supplied === "--dry-run" ? supplied : suppliedMode;
  if (!port || ![undefined, "--dry-run"].includes(mode))
    throw new Error("usage: pnpm release:prepare PORT [VERSION] [--dry-run] (read-only)");
  console.log(JSON.stringify(await readiness(port, candidate)));
}
