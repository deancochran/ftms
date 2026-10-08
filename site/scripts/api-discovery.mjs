import { readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { siteFile, sitePath } from "../site.config.mjs";

const marker = "ftms-ai-discovery";

export function injectApiDiscovery(html, markdownHref) {
  if (html.includes(marker)) return html;
  const head = `<link data-${marker} rel="describedby" href="${siteFile("llms.txt")}"><link data-${marker} rel="alternate" type="text/markdown" href="${markdownHref}">`;
  const visible = `<p data-${marker}><a href="${siteFile("llms.txt")}">AI documentation</a> · <a href="${markdownHref}">View Markdown</a></p>`;
  if (!html.includes("</head>") || !/<body\b[^>]*>/i.test(html))
    throw new Error("TypeDoc page is missing a document head or body");
  return html.replace("</head>", `${head}</head>`).replace(/<body\b[^>]*>/i, `$&${visible}`);
}

async function htmlFiles(directory, prefix = "") {
  const entries = await readdir(directory, { withFileTypes: true });
  return (
    await Promise.all(
      entries.map(async (entry) => {
        const relative = path.posix.join(prefix, entry.name);
        if (entry.isDirectory()) return htmlFiles(path.join(directory, entry.name), relative);
        return entry.isFile() && entry.name.endsWith(".html") ? [relative] : [];
      }),
    )
  ).flat();
}

export async function addApiDiscovery(directory) {
  for (const file of await htmlFiles(directory)) {
    const markdownFile = file
      .replace(/^types\//, "type-aliases/")
      .replace(/^hierarchy\.html$/, "index.md")
      .replace(/index\.html$/, "index.md")
      .replace(/\.html$/, ".md");
    const markdown = `${sitePath("api/typescript")}${markdownFile}`;
    const destination = path.join(directory, file);
    await writeFile(destination, injectApiDiscovery(await readFile(destination, "utf8"), markdown));
  }
}
