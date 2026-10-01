// Presentation metadata only. Native manifests remain the version authorities.
// Package identities and tag prefixes are compatibility contracts, not branding.
export const portCatalog = {
  typescript: {
    language: "TypeScript",
    packageId: "@deancochran/ftms",
    versionSource: "packages/typescript/package.json",
    tagPrefix: "typescript-v",
    legacyTagPrefix: "v",
    guide: "examples/typescript-quickstart/README.md",
  },
  c: {
    language: "C",
    packageId: "ftms",
    versionSource: "packages/c/VERSION",
    tagPrefix: "c-v",
    guide: "examples/c-client/README.md",
  },
  swift: {
    language: "Swift",
    packageId: "FTMS",
    versionSource: "packages/swift/VERSION",
    tagPrefix: "swift-v",
  },
  kotlin: {
    language: "Kotlin/JVM",
    packageId: "io.github.deancochran:ftms",
    versionSource: "packages/kotlin/VERSION",
    tagPrefix: "kotlin-v",
  },
  python: {
    language: "Python",
    packageId: "deancochran-ftms",
    versionSource: "packages/python/pyproject.toml",
    tagPrefix: "python-v",
  },
  rust: {
    language: "Rust",
    packageId: "ftms",
    versionSource: "packages/rust/Cargo.toml",
    tagPrefix: "rust-v",
  },
  dart: {
    language: "Dart",
    packageId: "deancochran_ftms",
    versionSource: "packages/dart/pubspec.yaml",
    tagPrefix: "dart-v",
  },
  go: {
    language: "Go",
    packageId: "github.com/deancochran/ftms/packages/go",
    versionSource: "packages/go/CHANGELOG.md",
    tagPrefix: "packages/go/v",
  },
  csharp: {
    language: "C#",
    packageId: "DeanCochran.Ftms",
    versionSource: "packages/csharp/VERSION",
    tagPrefix: "csharp-v",
  },
};

export function portInfo(port) {
  const entry = portCatalog[port];
  if (!Object.hasOwn(portCatalog, port)) throw new Error(`unknown port: ${port}`);
  return {
    ...entry,
    readme: `packages/${port}/README.md`,
    changelog: `packages/${port}/CHANGELOG.md`,
    route: `start/${port}`,
    title: `FTMS for ${entry.language}`,
  };
}

export function releaseTitle(port, version) {
  // Native version syntax (including Python prereleases) is preserved.
  if (!/^[0-9][0-9A-Za-z.+-]*$/.test(version))
    throw new Error("expected native version without v prefix");
  return `FTMS ${portInfo(port).language} ${version}`;
}

export function releaseTag(port, version) {
  releaseTitle(port, version);
  const info = portInfo(port);
  // Keep the entire pre-1.0 line in its original namespace. The 1.0 milestone
  // (including prereleases) starts the language-prefixed npm tag namespace.
  const prefix =
    port === "typescript" && version.startsWith("0.") ? info.legacyTagPrefix : info.tagPrefix;
  return `${prefix}${version}`;
}

export function guidePage(port) {
  const entry = portInfo(port);
  return {
    source: entry.guide ?? entry.readme,
    slug: entry.route,
    title: entry.language,
    group: "Getting started",
  };
}
