import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { slug } from "github-slugger";
import remarkGfm from "remark-gfm";
import remarkParse from "remark-parse";
import { unified } from "unified";
import { aiGroupNotes, pages, repository, siteFileUrl, siteUrl } from "../site.config.mjs";
import { convertAiMarkdown, root } from "./content.mjs";

const siteRoot = fileURLToPath(new URL("../", import.meta.url));
const generatedRoot = path.join(siteRoot, ".generated");
const outputRoot = path.join(generatedRoot, "ai-docs");
const apiRoot = path.join(generatedRoot, "api/typescript");
const manifestPath = path.join(generatedRoot, "ai-docs-manifest.json");
const parser = unified().use(remarkParse).use(remarkGfm);

function firstHeadingSlug(markdown) {
  const first = parser.parse(markdown).children[0];
  if (first?.type !== "heading" || first.depth !== 1) throw new Error("Expected a level-one title");
  const text = (node) => node.value ?? (node.children ?? []).map(text).join("");
  return slug(text(first));
}

function apiMarkdownPath(file) {
  return `${siteUrl("api/typescript")}${file.replace(/README\.md$/, "index.md")}`;
}

export function absolutizeApiLinks(markdown, file) {
  return markdown.replace(/\]\(([^)\s]+\.md(?:#[^)\s]*)?)\)/g, (whole, href) => {
    if (/^(?:[a-z][a-z0-9+.-]*:|\/)/i.test(href)) return whole;
    const [target, hash = ""] = href.split("#", 2);
    const resolved = path.posix.normalize(path.posix.join(path.posix.dirname(file), target));
    if (resolved.startsWith("../"))
      throw new Error(`API Markdown link escapes its generated tree: ${href}`);
    return `](${apiMarkdownPath(resolved)}${hash ? `#${hash}` : ""})`;
  });
}

async function apiFiles(directory, prefix = "") {
  const { readdir } = await import("node:fs/promises");
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(
    entries
      .sort((a, b) => a.name.localeCompare(b.name))
      .map(async (entry) => {
        const relative = path.posix.join(prefix, entry.name);
        return entry.isDirectory()
          ? apiFiles(path.join(directory, entry.name), relative)
          : entry.isFile() && entry.name.endsWith(".md")
            ? [relative]
            : [];
      }),
  );
  return nested.flat();
}

export function buildAiDocuments({ canonical, api, revision }) {
  const documents = new Map();
  const index = [
    "# FTMS AI documentation",
    "",
    "> Curated, build-generated Markdown for the public FTMS documentation site and TypeScript API.",
    "",
    `Revision: [${revision}](${repository}/tree/${revision})`,
    "",
    "This index covers only the explicit public pages and generated TypeScript API Markdown listed below. It excludes private `.context/` material, unlisted repository files, generated HTML, device captures, and execution authority. FTMS capability evidence does not authorize controls.",
    "",
    ...Object.entries(aiGroupNotes)
      .filter(([group]) => group !== "Contributing")
      .flatMap(([group, note]) => [
        `## ${group}`,
        "",
        ...canonical
          .filter(({ page }) => page.group === (group === "Overview" ? null : group))
          .map(({ page }) => `- [${page.title}](${siteUrl(page.slug)}index.md): ${note}`),
        "",
      ]),
    "## Generated TypeScript API",
    "",
    `- [API index](${siteUrl("api/typescript")}index.md)`,
    "",
    "## Downloads",
    "",
    `- [Full documentation bundle](${siteFileUrl("llms-full.txt")}): All mapped guides and generated TypeScript API Markdown in one download.`,
    "",
    "## Optional",
    "",
    ...canonical
      .filter(({ page }) => page.group === "Contributing")
      .map(
        ({ page }) =>
          `- [${page.title}](${siteUrl(page.slug)}index.md): Contributor and historical context; not required for using the library.`,
      ),
    "",
  ].join("\n");
  documents.set("llms.txt", index);

  for (const { page, markdown } of canonical) {
    const source = `${repository}/blob/${revision}/${page.source}`;
    documents.set(
      `${page.slug ? `${page.slug}/` : ""}index.md`,
      `<!-- Canonical source: ${source}; revision: ${revision} -->\n\n${markdown}`,
    );
  }
  for (const { file, markdown } of api)
    documents.set(`api/typescript/${file.replace(/README\.md$/, "index.md")}`, markdown);

  const full = [
    "# FTMS AI documentation: full corpus",
    "",
    `Revision: [${revision}](${repository}/tree/${revision})`,
    "",
    "Scope: the curated public pages in llms.txt plus generated TypeScript API Markdown. It intentionally excludes private `.context/` material and all unlisted repository content.",
    "",
    ...canonical.flatMap(({ page, markdown }) => [
      `<!-- Source: ${repository}/blob/${revision}/${page.source}; route: ${siteUrl(page.slug)} -->`,
      markdown.trim(),
      "",
    ]),
    ...api.flatMap(({ file, markdown }) => [
      `<!-- Generated TypeScript API: ${file} -->`,
      markdown.trim(),
      "",
    ]),
  ].join("\n");
  documents.set("llms-full.txt", full);
  return documents;
}

async function revision() {
  return execFileSync("git", ["rev-parse", "HEAD"], { cwd: root, encoding: "utf8" }).trim();
}

async function loadCanonical() {
  const sources = await Promise.all(
    pages.map(async (page) => [page, await readFile(path.join(root, page.source), "utf8")]),
  );
  const anchors = new Map(
    sources.map(([page, markdown]) => [page.source, firstHeadingSlug(markdown)]),
  );
  return sources.map(([page, markdown]) => ({
    page,
    markdown: convertAiMarkdown(markdown, page, anchors),
  }));
}

async function loadApi() {
  if (!existsSync(apiRoot))
    throw new Error("Run pnpm --filter @deancochran/ftms docs:markdown first");
  const files = await apiFiles(apiRoot);
  return Promise.all(
    files.map(async (file) => ({
      file,
      markdown: absolutizeApiLinks(await readFile(path.join(apiRoot, file), "utf8"), file),
    })),
  );
}

export async function writeAiDocuments({ destination = outputRoot } = {}) {
  const [canonical, api, commit] = await Promise.all([loadCanonical(), loadApi(), revision()]);
  const documents = buildAiDocuments({ canonical, api, revision: commit });
  let old = [];
  if (existsSync(manifestPath)) old = JSON.parse(await readFile(manifestPath, "utf8")).files;
  await syncAiDocuments({ documents, destination, previousFiles: old });
  await mkdir(path.dirname(manifestPath), { recursive: true });
  await writeFile(
    manifestPath,
    `${JSON.stringify({ files: [...documents.keys()].sort() }, null, 2)}\n`,
  );
  return documents;
}

export async function syncAiDocuments({ documents, destination, previousFiles = [] }) {
  for (const file of new Set([...previousFiles, ...documents.keys()])) {
    await rm(path.join(destination, file), { force: true });
  }
  for (const [file, content] of documents) {
    const destinationFile = path.join(destination, file);
    await mkdir(path.dirname(destinationFile), { recursive: true });
    await writeFile(destinationFile, content);
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const documents = await writeAiDocuments();
  console.log(
    `Generated ${documents.size} AI-readable documents from ${pages.length} explicit pages.`,
  );
}
