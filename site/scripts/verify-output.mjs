import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { slug } from "github-slugger";
import { parse } from "parse5";
import { base, pages, site, sitePath } from "../site.config.mjs";

const output = fileURLToPath(new URL("../dist/", import.meta.url));

function htmlFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const file = path.join(directory, entry.name);
    return entry.isDirectory() ? htmlFiles(file) : file.endsWith(".html") ? [file] : [];
  });
}

function markdownFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const file = path.join(directory, entry.name);
    return entry.isDirectory()
      ? markdownFiles(file)
      : entry.isFile() && /\.(?:md|txt)$/.test(file)
        ? [file]
        : [];
  });
}

function verifyMarkdownLinks() {
  for (const file of markdownFiles(output)) {
    const text = readFileSync(file, "utf8");
    assert.doesNotMatch(text, /\.context\/(?:ftms|private)/, `Private content in ${file}`);
    for (const [, href] of text.matchAll(/\]\(([^)\s]+)\)/g)) {
      const target = new URL(href, `${site}${sitePath()}`);
      if (target.origin !== site || !target.pathname.includes(".md")) continue;
      assert.ok(target.pathname.startsWith(`${base}/`), `Markdown path misses base: ${href}`);
      const targetFile = path.join(output, target.pathname.slice(base.length));
      assert.ok(existsSync(targetFile), `Missing Markdown link ${href} from ${file}`);
      if (target.hash) {
        const headings =
          readFileSync(targetFile, "utf8")
            .match(/^#{1,6}\s+(.+)$/gm)
            ?.map((heading) => slug(heading.replace(/^#+\s+/, ""))) ?? [];
        assert.ok(headings.includes(target.hash.slice(1)), `Missing Markdown anchor ${href}`);
      }
    }
  }
}

export function inspectHtml(html) {
  const ids = new Set();
  const links = [];
  const walk = (node) => {
    const attrs = Object.fromEntries((node.attrs ?? []).map((attr) => [attr.name, attr.value]));
    if (attrs.id) ids.add(attrs.id);
    if (attrs.name && node.tagName === "a") ids.add(attrs.name);
    for (const key of ["href", "src"]) {
      // Metadata is not a navigable resource (Starlight's 404 canonical is /404/).
      if (node.tagName === "link" && attrs.rel === "canonical") continue;
      if (attrs[key] && node.tagName !== "use") links.push(attrs[key]);
    }
    for (const child of node.childNodes ?? []) walk(child);
  };
  walk(parse(html));
  return { ids, links };
}

export function localTarget(href, pageUrl) {
  const target = new URL(href, pageUrl);
  if (target.origin !== site || !["http:", "https:"].includes(target.protocol)) return null;
  assert.ok(
    target.pathname === base || target.pathname.startsWith(`${base}/`),
    `Missing Pages base: ${href}`,
  );
  let pathname = decodeURIComponent(target.pathname.slice(base.length));
  if (!pathname || pathname.endsWith("/")) pathname += "index.html";
  const file = path.resolve(output, `.${pathname.startsWith("/") ? pathname : `/${pathname}`}`);
  assert.ok(file.startsWith(output), `Path escapes output: ${href}`);
  return { file, fragment: decodeURIComponent(target.hash.slice(1)) };
}

export function verifyOutput() {
  for (const page of pages) {
    assert.ok(existsSync(path.join(output, page.slug, "index.html")), `Missing route ${page.slug}`);
  }
  for (const required of [
    "404.html",
    "pagefind/pagefind.js",
    "pagefind/pagefind-entry.json",
    "api/typescript/index.html",
    "sitemap-index.xml",
    "llms.txt",
    "llms-full.txt",
  ]) {
    assert.ok(existsSync(path.join(output, required)), `Missing generated asset ${required}`);
  }
  const aiIndex = readFileSync(path.join(output, "llms.txt"), "utf8");
  const aiFull = readFileSync(path.join(output, "llms-full.txt"), "utf8");
  assert.match(aiIndex, /# FTMS AI documentation/);
  assert.match(aiFull, /# FTMS AI documentation: full corpus/);
  assert.doesNotMatch(aiFull, /Source: \.context\//);
  for (const page of pages) {
    const markdown = path.join(output, page.slug, "index.md");
    assert.ok(existsSync(markdown), `Missing AI Markdown for ${page.slug || "home"}`);
    assert.ok(
      aiIndex.includes(`${sitePath(page.slug)}index.md`),
      `Missing AI index link ${page.slug}`,
    );
  }
  assert.ok(existsSync(path.join(output, "api/typescript/index.md")), "Missing API Markdown index");
  const sitemap = readFileSync(path.join(output, "sitemap-0.xml"), "utf8");
  assert.match(sitemap, /\/ftms\/api\/typescript\//, "Missing TypeDoc API sitemap entries");
  verifyMarkdownLinks();
  const files = htmlFiles(output);
  const documents = new Map(files.map((file) => [file, inspectHtml(readFileSync(file, "utf8"))]));
  const errors = [];
  for (const [file, document] of documents) {
    const relative = path.relative(output, file).split(path.sep).join("/");
    const pageUrl = `${site}${sitePath()}${relative.replace(/index\.html$/, "")}`;
    for (const link of document.links) {
      try {
        const target = localTarget(link, pageUrl);
        if (!target) continue;
        assert.ok(existsSync(target.file) && statSync(target.file).isFile(), `Missing ${link}`);
        if (target.fragment && target.file.endsWith(".html")) {
          assert.ok(documents.get(target.file)?.ids.has(target.fragment), `Missing anchor ${link}`);
        }
      } catch (error) {
        errors.push(`${relative}: ${error.message}`);
      }
    }
  }
  assert.deepEqual(errors, [], errors.join("\n"));
  console.log(
    `Verified ${files.length} HTML files: local links, anchors, assets, ${base} base, search and TypeDoc output.`,
  );
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url))
  verifyOutput();
