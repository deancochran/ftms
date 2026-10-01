import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { portCatalog } from "./port-catalog.mjs";

export const consumerAdapterUrl =
  "https://github.com/deancochran/ftms/blob/main/docs/architecture.md#consumer-adapter-seam";

export const consumerAdapterProjectLinks = Object.freeze({
  "README.md": "docs/architecture.md#consumer-adapter-seam",
  "CONTRIBUTING.md": "docs/architecture.md#consumer-adapter-seam",
  "docs/README.md": "architecture.md#consumer-adapter-seam",
  "docs/ftms-explained.md": "architecture.md#consumer-adapter-seam",
  "docs/integration.md": "architecture.md#consumer-adapter-seam",
  "docs/roadmap.md": "architecture.md#consumer-adapter-seam",
  "docs/support-profiles.md": "architecture.md#consumer-adapter-seam",
  "docs/transport-recipes.md": "architecture.md#consumer-adapter-seam",
  "packages/README.md": "../docs/architecture.md#consumer-adapter-seam",
  "site/landing.md": "../docs/architecture.md#consumer-adapter-seam",
});

export function withoutCode(text) {
  return text.replace(/^ {0,3}(`{3,}|~{3,})[^\n]*\n[\s\S]*?^ {0,3}\1\s*$/gm, "");
}

export function anchors(text) {
  const counts = new Map();
  const result = new Set();
  const prose = withoutCode(text);
  for (const match of prose.matchAll(/^ {0,3}#{1,6}\s+(.+?)(?:\s+#+)?\s*$/gm)) {
    const slug = match[1]
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
      .replace(/<[^>]*>/g, "")
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\p{M}_\-\s]/gu, "")
      .replace(/ /g, "-");
    const count = counts.get(slug) ?? 0;
    counts.set(slug, count + 1);
    result.add(count ? `${slug}-${count}` : slug);
  }
  for (const match of prose.matchAll(/<(?:a|h[1-6])\s+[^>]*(?:id|name)=["']([^"']+)["']/g)) {
    result.add(match[1]);
  }
  return result;
}

export function links(text) {
  const prose = withoutCode(text).replace(/`[^`\n]*`/g, "");
  const result = [];
  for (const match of prose.matchAll(/!?\[[^\]\n]*\]\(<?([^\s)>]+)>?(?:\s+["'][^\n]*?["'])?\)/g)) {
    result.push(match[1]);
  }
  for (const match of prose.matchAll(/^ {0,3}\[[^\]]+\]:\s*<?([^\s>]+)>?/gm)) {
    result.push(match[1]);
  }
  return result;
}

export function checkLinks(root, file, text) {
  const errors = [];
  for (const href of links(text)) {
    if (/^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(href)) continue;
    const [pathname, fragment] = href.split("#");
    let target;
    let anchor;
    try {
      target = pathname
        ? path.resolve(path.dirname(file), decodeURIComponent(pathname.split("?")[0]))
        : file;
      anchor = fragment ? decodeURIComponent(fragment) : "";
    } catch {
      errors.push(`${file}: malformed link ${href}`);
      continue;
    }
    const relative = path.relative(root, target);
    if (relative.startsWith("..") || path.isAbsolute(relative) || !existsSync(target)) {
      errors.push(`${file}: missing/outside target ${href}`);
    } else if (anchor && target.endsWith(".md") && statSync(target).isFile()) {
      if (!anchors(readFileSync(target, "utf8")).has(anchor)) {
        errors.push(`${file}: missing anchor ${href}`);
      }
    }
  }
  return errors;
}

export function checkStatus(root) {
  const read = (file) => readFileSync(path.join(root, file), "utf8");
  const matrix = read("docs/released-packages.md");
  const manifest = JSON.parse(read("examples/typescript-quickstart/package.json"));
  const version = manifest.dependencies["@deancochran/ftms"];
  assert.match(version, /^\d+\.\d+\.\d+$/);
  assert.ok(
    matrix.includes(`npm \`@deancochran/ftms@${version}\``),
    "Quickstart must match a recorded release",
  );
  assert.match(read("README.md"), /^npm install @deancochran\/ftms$/m);
  const cVersion = matrix.match(/\| C \| GitHub `c-v(\d+\.\d+\.\d+)`/u)?.[1];
  assert.ok(cVersion, "Release matrix must identify the public C archive tag");
  const cExample = read("examples/c-client/README.md");
  const cDownloads = [
    ...cExample.matchAll(/releases\/download\/c-v([^/]+)\/ftms-c-([\d.]+)\.tar\.gz/g),
  ];
  assert.equal(cDownloads.length, 2, "C example must link archive and checksum");
  for (const match of cDownloads) {
    assert.equal(match[1], cVersion, "C example tag must match current public matrix");
    assert.equal(match[2], cVersion, "C archive name must match its tag");
  }
  const cHash = matrix.match(/C \*\*[^*]+\*\* archive SHA-256:\s*`([a-f0-9]{64})`/)?.[1];
  assert.ok(
    cHash && cExample.includes(cHash),
    "C quickstart must retain the reviewed archive hash",
  );
  for (const file of ["SECURITY.md", "packages/typescript/README.md"]) {
    for (const link of links(read(file))) {
      assert.ok(
        !link.startsWith("../"),
        `${file}: repository-only links need public URLs in shipped docs`,
      );
    }
  }
}

export function checkConsumerAdapterSeam(root) {
  const read = (file) => readFileSync(path.join(root, file), "utf8");
  const architecture = read("docs/architecture.md");
  const seamHeading = /^## Consumer adapter seam\s*$/m.exec(architecture);
  assert.ok(seamHeading, "Architecture must define the consumer adapter seam");
  const afterHeading = architecture.slice(seamHeading.index + seamHeading[0].length);
  const nextHeading = /^#{1,2}\s+/m.exec(afterHeading);
  const seam = afterHeading.slice(0, nextHeading?.index ?? afterHeading.length);
  const architectureProse = architecture.replace(/\s+/g, " ");
  const seamProse = withoutCode(seam)
    .replace(/`[^`\n]*`/g, "")
    .replace(/\s+/g, " ")
    .toLowerCase();
  assert.ok(
    anchors(architecture).has("consumer-adapter-seam"),
    "Architecture must define the consumer adapter seam",
  );
  for (const phrase of [
    "protocol package owns",
    "consumer adapter/application owns",
    "record planning/assembly",
    "deterministic expiry evaluation",
    "clock/tick source",
    "selected expiry/freshness policy",
    "not execution permission",
    "physical safety",
    "does not define one cross-language runtime adapter interface",
  ]) {
    assert.ok(seamProse.includes(phrase), `Consumer adapter seam must retain: ${phrase}`);
  }
  assert.ok(
    !seamProse.includes("fragment expiry, freshness"),
    "Consumer side must not claim deterministic fragment-expiry evaluation",
  );
  for (const stale of [
    "Capability interpretation (TypeScript, C, Swift and Kotlin implemented)",
    "Implemented independently by TypeScript, C, Swift, Kotlin and Python",
  ]) {
    assert.ok(
      !architectureProse.includes(stale),
      `Architecture retains stale capability list: ${stale}`,
    );
  }
  for (const port of Object.keys(portCatalog)) {
    const readme = read(`packages/${port}/README.md`);
    assert.ok(
      links(readme).includes(consumerAdapterUrl),
      `packages/${port}/README.md must link the canonical consumer adapter seam`,
    );
  }
  for (const [file, target] of Object.entries(consumerAdapterProjectLinks)) {
    assert.ok(
      links(read(file)).includes(target),
      `${file} must link the canonical consumer adapter seam`,
    );
  }
  assert.ok(
    read("packages/typescript/README.md").includes(
      "`writeControlPoint` above is supplied by the consumer adapter",
    ),
    "TypeScript control example must identify writeControlPoint as consumer-owned",
  );
}

export function main(root) {
  // Includes new work without requiring staging; respects generated/ignored paths.
  const files = execFileSync(
    "git",
    ["ls-files", "--cached", "--others", "--exclude-standard", "-z"],
    {
      cwd: root,
      encoding: "utf8",
    },
  )
    .split("\0")
    .filter((file) => file.endsWith(".md") && file !== "AGENTS.md");
  const errors = [];
  for (const relative of new Set(files)) {
    const file = path.join(root, relative);
    if (existsSync(file)) errors.push(...checkLinks(root, file, readFileSync(file, "utf8")));
  }
  assert.equal(errors.length, 0, errors.join("\n"));
  checkStatus(root);
  checkConsumerAdapterSeam(root);
  console.log(
    `Documentation checks passed: ${new Set(files).size} Markdown files; local links/anchors, release quickstart identity and consumer adapter seam.`,
  );
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(fileURLToPath(new URL("../", import.meta.url)));
}
