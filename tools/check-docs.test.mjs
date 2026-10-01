import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { anchors, checkLinks, checkStatus, links } from "./check-docs.mjs";

test("headings, duplicate anchors, inline code and explicit HTML anchors", () => {
  assert.deepEqual(
    [...anchors('# API `value`\n## API `value`\n<a id="custom"></a>')],
    ["api-value", "api-value-1", "custom"],
  );
});

test("links include images and reference definitions, but not code or fences", () => {
  assert.deepEqual(
    links("[go](a.md#x) ![pic](a.png)\n[ref]: b.md\n`[no](bad)`\n```js\n[x](bad)\n```"),
    ["a.md#x", "a.png", "b.md"],
  );
});

test("missing files, traversal and broken anchors fail; external URLs stay offline", () => {
  const root = mkdtempSync(path.join(tmpdir(), "ftms-doc-links-"));
  try {
    const file = path.join(root, "README.md");
    writeFileSync(file, "# Hello world\n");
    assert.deepEqual(checkLinks(root, file, "[ok](#hello-world) [web](https://example.com)"), []);
    assert.equal(checkLinks(root, file, "[bad](#missing)").length, 1);
    assert.equal(checkLinks(root, file, "[bad](missing.md)").length, 1);
    assert.equal(checkLinks(root, file, "[bad](../README.md)").length, 1);
    assert.equal(checkLinks(root, file, "[bad](%ZZ)").length, 1);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("release guards reject mismatched quickstarts and package-external relative links", () => {
  const root = mkdtempSync(path.join(tmpdir(), "ftms-doc-status-"));
  const put = (name, text) => {
    const file = path.join(root, name);
    mkdirSync(path.dirname(file), { recursive: true });
    writeFileSync(file, text);
  };
  const hash = "a".repeat(64);
  const cExample = `releases/download/c-v0.2.0/ftms-c-0.2.0.tar.gz\nreleases/download/c-v0.2.0/ftms-c-0.2.0.tar.gz.sha256\n${hash}`;
  try {
    put(
      "docs/released-packages.md",
      `npm \`@deancochran/ftms@0.4.0\`\n| C | GitHub \`c-v0.2.0\` |\nC **0.2.0** archive SHA-256:\n\`${hash}\``,
    );
    put("README.md", "npm install @deancochran/ftms@0.4.0");
    put("SECURITY.md", "[policy](https://example.com)");
    put("packages/typescript/README.md", "# Package");
    put(
      "examples/typescript-quickstart/package.json",
      JSON.stringify({ dependencies: { "@deancochran/ftms": "0.4.0" } }),
    );
    put("examples/c-client/README.md", cExample);
    assert.doesNotThrow(() => checkStatus(root));
    put("README.md", "npm install @deancochran/ftms@0.2.0");
    assert.throws(() => checkStatus(root));
    put("README.md", "npm install @deancochran/ftms@0.4.0");
    put("examples/c-client/README.md", cExample.replaceAll("0.2.0", "0.1.0"));
    assert.throws(() => checkStatus(root));
    put("examples/c-client/README.md", cExample);
    put("packages/typescript/README.md", "[guide](../../docs/README.md)");
    assert.throws(() => checkStatus(root));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
