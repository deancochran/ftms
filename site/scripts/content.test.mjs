import assert from "node:assert/strict";
import test from "node:test";
import { pages, sidebar, sitePath } from "../site.config.mjs";
import { convertAiMarkdown, convertMarkdown, rewriteLink } from "./content.mjs";

test("routes and sources are unique and constrained", () => {
  assert.equal(new Set(pages.map((page) => page.source)).size, pages.length);
  assert.equal(new Set(pages.map((page) => page.slug)).size, pages.length);
  for (const page of pages) assert.match(page.slug, /^(?:[a-z]+\/[a-z-]+)?$/);
});

test("reader navigation separates getting started, releases and contributor evidence", () => {
  const groups = sidebar.filter((entry) => entry.items).map((entry) => entry.label);
  assert.deepEqual(groups, ["Getting started", "Guides", "Reference", "Releases", "Contributing"]);
  assert.deepEqual(
    pages
      .filter((page) =>
        /^start\/(c|csharp|dart|go|kotlin|python|rust|swift|typescript)$/.test(page.slug),
      )
      .map((page) => page.title),
    ["C", "C#", "Dart", "Go", "Kotlin/JVM", "Python", "Rust", "Swift", "TypeScript"],
  );
  assert.equal(pages.find((page) => page.source === "docs/releasing.md").group, "Contributing");
  assert.equal(pages.find((page) => page.source === "docs/released-packages.md").group, "Releases");
  assert.equal(
    pages.find((page) => page.source === "packages/README.md").slug,
    "start/choose-language",
  );
});

test("mapped links preserve base, query and fragments; unmapped source stays on GitHub", () => {
  assert.equal(
    rewriteLink("integration.md#diagnostics-and-more-data", "docs/README.md"),
    `${sitePath("integration/cookbook")}#diagnostics-and-more-data`,
  );
  assert.equal(rewriteLink("../examples/c-client/", "docs/README.md"), sitePath("start/c"));
  assert.equal(
    rewriteLink(
      "https://github.com/deancochran/ftms/blob/main/docs/integration.md?x=1",
      "README.md",
    ),
    `${sitePath("integration/cookbook")}?x=1`,
  );
  assert.match(
    rewriteLink("main.mjs", "examples/typescript-quickstart/README.md"),
    /github.com\/deancochran\/ftms\/blob\/main\/examples\/typescript-quickstart\/main.mjs$/,
  );
  assert.equal(rewriteLink("https://example.com/page", "README.md"), "https://example.com/page");
  assert.equal(rewriteLink("mailto:hello@example.com", "README.md"), "mailto:hello@example.com");
});

test("missing/private paths and escaping the repository fail closed", () => {
  for (const href of ["missing.md", "../.context/private.md", "../../etc/passwd"]) {
    assert.throws(() => rewriteLink(href, "docs/README.md"));
  }
});

test("Markdown conversion retains tables/code, resolves references and restores removed title anchor", () => {
  const page = pages.find((entry) => entry.source === "docs/integration.md");
  const markdown =
    '# Integration cookbook\n\n[title](#integration-cookbook) [help][ref]\n\n[ref]: troubleshooting.md\n\n| A | B |\n| - | - |\n| 1 | 2 |\n\n```js\nconst text = "[not a link](missing.md)";\n```\n';
  const result = convertMarkdown(markdown, page, new Map([[page.source, "integration-cookbook"]]));
  assert.ok(result.includes(`${sitePath(page.slug)}#_top`));
  assert.ok(result.includes(sitePath("integration/troubleshooting")));
  assert.ok(result.includes("[not a link](missing.md)"));
  assert.match(result, /\| A\s+\| B/);
  assert.ok(!result.includes("# Integration cookbook"));
  assert.ok(result.includes("/edit/main/docs/integration.md"));
});

test("AI Markdown retains canonical headings without frontmatter or UI-only anchors", () => {
  const page = pages.find((entry) => entry.source === "docs/integration.md");
  const result = convertAiMarkdown(
    "# Integration cookbook\n\n[title](#integration-cookbook)\n\n```js\nconst packet = bytes;\n```\n",
    page,
    new Map([[page.source, "integration-cookbook"]]),
  );
  assert.match(result, /^# Integration cookbook/m);
  assert.ok(
    result.includes(
      "https://deancochran.github.io/ftms/integration/cookbook/index.md#integration-cookbook",
    ),
  );
  assert.match(result, /```js/);
  assert.doesNotMatch(result, /^---/m);
  assert.doesNotMatch(result, /#_top/);
});
