import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "parse5";
import { base, pages, site, sitePath } from "../site.config.mjs";

const output = fileURLToPath(new URL("../dist/", import.meta.url));

function htmlFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const file = path.join(directory, entry.name);
    return entry.isDirectory() ? htmlFiles(file) : file.endsWith(".html") ? [file] : [];
  });
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
  ]) {
    assert.ok(existsSync(path.join(output, required)), `Missing generated asset ${required}`);
  }
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
