import { existsSync, statSync } from "node:fs";
import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { slug } from "github-slugger";
import remarkGfm from "remark-gfm";
import remarkParse from "remark-parse";
import remarkStringify from "remark-stringify";
import { unified } from "unified";
import { pages, repository, sitePath, sourceBranch } from "../site.config.mjs";

export const root = fileURLToPath(new URL("../../", import.meta.url));
const contentDirectory = path.join(root, "site/src/content/docs");
const processor = unified().use(remarkParse).use(remarkGfm).use(remarkStringify);
const sourcePages = new Map(pages.map((page) => [page.source, page]));

function visit(node, callback) {
  callback(node);
  for (const child of node.children ?? []) visit(child, callback);
}

function textOf(node) {
  return node.value ?? (node.children ?? []).map(textOf).join("");
}

function publicFile(source) {
  const normalized = path.posix.normalize(source);
  if (
    normalized.startsWith("../") ||
    path.posix.isAbsolute(normalized) ||
    normalized.split("/").some((part) => part.startsWith(".")) ||
    !existsSync(path.join(root, normalized))
  )
    throw new Error(`Not an existing public repository path: ${source}`);
  return normalized;
}

export function rewriteLink(href, source, titleAnchors = new Map(), image = false) {
  if (/^(?:mailto:|tel:)/i.test(href)) return href;
  let relative = href;
  const githubPrefix = `${repository}/blob/${sourceBranch}/`;
  if (href.startsWith(githubPrefix)) {
    relative = `/${href.slice(githubPrefix.length)}`;
  } else if (/^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(href)) {
    return href;
  }
  const url = new URL(relative, `https://repository.invalid/${source}`);
  let target = publicFile(decodeURIComponent(url.pathname.slice(1)));
  if (statSync(path.join(root, target)).isDirectory()) {
    const readme = path.posix.join(target, "README.md");
    if (sourcePages.has(readme)) target = readme;
  }
  const page = sourcePages.get(target);
  if (page && !image) {
    const hash =
      decodeURIComponent(url.hash.slice(1)) === titleAnchors.get(target) ? "#_top" : url.hash;
    return `${sitePath(page.slug)}${url.search}${hash}`;
  }
  const encoded = target.split("/").map(encodeURIComponent).join("/");
  if (image)
    return `https://raw.githubusercontent.com/deancochran/ftms/${sourceBranch}/${encoded}${url.search}`;
  const kind = statSync(path.join(root, target)).isDirectory() ? "tree" : "blob";
  return `${repository}/${kind}/${sourceBranch}/${encoded}${url.search}${url.hash}`;
}

export function convertMarkdown(markdown, page, titleAnchors) {
  const tree = processor.parse(markdown);
  const first = tree.children[0];
  if (first?.type !== "heading" || first.depth !== 1) {
    throw new Error(`${page.source} must start with a level-one title`);
  }
  tree.children.shift(); // Starlight renders the title; preserve the original anchor via rewriting.
  visit(tree, (node) => {
    if (["link", "image", "definition"].includes(node.type)) {
      node.url = rewriteLink(node.url, page.source, titleAnchors, node.type === "image");
    }
  });
  const metadata = {
    title: page.title,
    editUrl: `${repository}/edit/${sourceBranch}/${page.source}`,
  };
  if (page.slug === "") {
    metadata.description =
      "FTMS protocol codecs for TypeScript, C, Swift, Kotlin, Python and Rust. Keep your Bluetooth stack.";
    metadata.template = "splash";
    metadata.hero = {
      tagline: "Decode telemetry. Understand capabilities. Keep your Bluetooth stack.",
      actions: [
        { text: "Get started", link: sitePath("start/typescript"), icon: "right-arrow" },
        { text: "Explore C / C++", link: sitePath("start/c"), variant: "secondary" },
      ],
    };
  }
  const frontmatter = Object.entries(metadata)
    .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
    .join("\n");
  const apiLink =
    page.source === "docs/api.md"
      ? `\n[Open the generated TypeScript API reference](${sitePath("api/typescript")})\n`
      : "";
  return `---\n${frontmatter}\n---\n${apiLink}\n${processor.stringify(tree)}`;
}

export async function prepareContent() {
  const contents = await Promise.all(
    pages.map(async (page) => {
      publicFile(page.source);
      return [page, await readFile(path.join(root, page.source), "utf8")];
    }),
  );
  const titleAnchors = new Map(
    contents.map(([page, text]) => {
      const first = processor.parse(text).children[0];
      return [page.source, slug(textOf(first))];
    }),
  );
  for (const [page, text] of contents) {
    const destination = path.join(contentDirectory, `${page.slug || "index"}.md`);
    const output = convertMarkdown(text, page, titleAnchors);
    await mkdir(path.dirname(destination), { recursive: true });
    // Avoid unnecessary HMR events when another canonical document changes.
    if (!existsSync(destination) || (await readFile(destination, "utf8")) !== output) {
      await writeFile(destination, output);
    }
  }
}

export function canonicalDocs() {
  return {
    name: "ftms-canonical-docs",
    hooks: {
      "astro:config:setup": async () => {
        await rm(contentDirectory, { recursive: true, force: true });
        await prepareContent();
        const api = path.join(root, "packages/typescript/docs/api");
        if (!existsSync(path.join(api, "index.html")))
          throw new Error("Run pnpm docs:build before building the site");
        const destination = path.join(root, "site/public/api/typescript");
        await rm(destination, { recursive: true, force: true });
        await cp(api, destination, { recursive: true });
      },
      "astro:server:setup": ({ server }) => {
        const sources = new Set(pages.map((page) => path.join(root, page.source)));
        server.watcher.add([...sources]);
        let pending = Promise.resolve();
        server.watcher.on("change", (file) => {
          if (sources.has(file)) {
            pending = pending
              .then(prepareContent)
              .catch((error) => server.config.logger.error(String(error)));
          }
        });
      },
    },
  };
}
