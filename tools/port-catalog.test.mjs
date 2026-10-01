import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readdir, readFile } from "node:fs/promises";
import test from "node:test";
import { pages } from "../site/site.config.mjs";
import { portCatalog, portInfo, releaseTag, releaseTitle } from "./port-catalog.mjs";
import { ports, readiness } from "./release-prepare.mjs";

test("catalog accounts for every port and preserves tag namespaces", async () => {
  const directories = (await readdir("packages", { withFileTypes: true }))
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();
  assert.deepEqual(Object.keys(portCatalog).sort(), directories);
  assert.deepEqual(Object.keys(ports).sort(), directories);
  const prefixes = {
    typescript: "v",
    c: "c-v",
    swift: "swift-v",
    kotlin: "kotlin-v",
    python: "python-v",
    rust: "rust-v",
    dart: "dart-v",
    go: "packages/go/v",
    csharp: "csharp-v",
  };
  for (const port of directories) {
    assert.equal(releaseTag(port, "1.2.3"), `${prefixes[port]}1.2.3`);
    const info = portInfo(port);
    assert.equal(ports[port].version, info.versionSource);
    assert.equal((await readFile(info.readme, "utf8")).split("\n")[0], `# ${info.title}`);
    const changelog = await readFile(info.changelog, "utf8");
    assert.equal(changelog.split("\n")[0], "# Changelog");
    const { version } = await readiness(port);
    assert.ok(changelog.split("\n").includes(`## ${version}`));
    const routes = pages.filter((page) => page.slug === info.route);
    assert.equal(routes.length, 1);
    assert.equal(routes[0].title, info.language);
  }
});

test("release titles preserve native versions and reject ambiguous input", () => {
  assert.equal(releaseTitle("csharp", "0.1.0-alpha.1"), "FTMS C# 0.1.0-alpha.1");
  assert.equal(releaseTitle("python", "0.1.0a2"), "FTMS Python 0.1.0a2");
  assert.equal(releaseTitle("go", "0.1.0"), "FTMS Go 0.1.0");
  assert.equal(releaseTitle("kotlin", "0.1.0"), "FTMS Kotlin/JVM 0.1.0");
  assert.throws(() => releaseTitle("go", "v0.1.0"));
  assert.throws(() => releaseTitle("missing", "1.0.0"));
  assert.throws(() => portInfo("toString"));
});

test("current package chooser tables use catalog language labels", async () => {
  for (const path of ["README.md", "site/landing.md", "docs/ftms-explained.md"]) {
    const source = await readFile(path, "utf8");
    const labels = [...source.matchAll(/^\| ([^|]+) \|/gm)].map((match) => match[1].trim());
    for (const { language } of Object.values(portCatalog)) {
      assert.equal(labels.filter((label) => label === language).length, 1, `${path}: ${language}`);
    }
  }
});

test("title CLI reads native version and rejects extra arguments", async () => {
  const result = spawnSync(process.execPath, ["tools/release-title.mjs", "rust"], {
    encoding: "utf8",
  });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.trim(), `FTMS Rust ${(await readiness("rust")).version}`);
  assert.notEqual(
    spawnSync(process.execPath, ["tools/release-title.mjs", "rust", "ignored"]).status,
    0,
  );
});

test("workflow display names follow policy without renaming workflow files", async () => {
  const workflows = {
    "dart.yml": "Verify Dart",
    "go-ci.yml": "Verify Go",
    "native-c.yml": "Verify C",
    "native-csharp.yml": "Verify C#",
    "native-kotlin.yml": "Verify Kotlin/JVM",
    "native-rust.yml": "Verify Rust",
    "native-swift.yml": "Verify Swift",
    "publish.yml": "Release TypeScript",
    "release-python.yml": "Release Python",
    "release-c.yml": "Release C",
    "release-csharp.yml": "Release C#",
    "release-dart.yml": "Release Dart",
    "release-kotlin.yml": "Release Kotlin/JVM",
    "release-rust.yml": "Release Rust",
    "release-swift.yml": "Release Swift",
  };
  for (const [file, name] of Object.entries(workflows)) {
    assert.equal(
      (await readFile(`.github/workflows/${file}`, "utf8")).match(/^name: (.+)$/m)?.[1],
      name,
    );
  }
});
