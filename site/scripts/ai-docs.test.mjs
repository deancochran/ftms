import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { pages } from "../site.config.mjs";
import { absolutizeApiLinks, buildAiDocuments, syncAiDocuments } from "./ai-docs.mjs";

test("AI index exports every explicit route without Starlight frontmatter", () => {
  const canonical = pages.map((page) => ({
    page,
    markdown: `# ${page.title}\n\nPublic content.\n`,
  }));
  const documents = buildAiDocuments({
    canonical,
    api: [{ file: "README.md", markdown: "# API\n" }],
    revision: "0123456789abcdef",
  });
  assert.equal(documents.get("llms.txt").match(/\n- \[/g).length, pages.length + 2);
  for (const page of pages) {
    const file = `${page.slug ? `${page.slug}/` : ""}index.md`;
    assert.match(documents.get(file), new RegExp(`Canonical source: .*${page.source}`));
    assert.match(documents.get(file), new RegExp(`# ${page.title}`));
  }
  assert.match(documents.get("llms-full.txt"), /Scope: the curated public pages/);
  assert.doesNotMatch(documents.get("llms-full.txt"), /Source: \.context\//);
});

test("generated API links are absolute and base-aware", () => {
  const markdown =
    "See [result](../interfaces/Result.md#shape) and [source](https://example.com/a.md).";
  assert.equal(
    absolutizeApiLinks(markdown, "functions/decode.md"),
    "See [result](https://deancochran.github.io/ftms/api/typescript/interfaces/Result.md#shape) and [source](https://example.com/a.md).",
  );
});

test("regeneration removes only stale generated files", async () => {
  const destination = await mkdtemp(path.join(os.tmpdir(), "ftms-ai-docs-"));
  try {
    await syncAiDocuments({
      destination,
      previousFiles: ["obsolete/index.md"],
      documents: new Map([["current/index.md", "# Current\n"]]),
    });
    assert.equal(existsSync(path.join(destination, "obsolete/index.md")), false);
    assert.equal(await readFile(path.join(destination, "current/index.md"), "utf8"), "# Current\n");
  } finally {
    await rm(destination, { recursive: true, force: true });
  }
});
