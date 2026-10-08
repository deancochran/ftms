import { existsSync, readdirSync } from "node:fs";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { base, site } from "../site.config.mjs";

function htmlFiles(directory, prefix = "") {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const relative = path.posix.join(prefix, entry.name);
    return entry.isDirectory()
      ? htmlFiles(path.join(directory, entry.name), relative)
      : entry.isFile() && entry.name.endsWith(".html")
        ? [relative]
        : [];
  });
}

export async function addApiPagesToSitemap(output) {
  output = output instanceof URL ? fileURLToPath(output) : output;
  const api = path.join(output, "api/typescript");
  if (!existsSync(api)) return;
  const sitemap = readdirSync(output).find((file) => /^sitemap-\d+\.xml$/.test(file));
  if (!sitemap) throw new Error("Astro sitemap was not generated");
  const urls = htmlFiles(api)
    .sort()
    .map((file) => `${site}${base}/api/typescript/${file.replace(/index\.html$/, "")}`)
    .map((url) => `<url><loc>${url}</loc></url>`)
    .join("");
  const file = path.join(output, sitemap);
  const xml = await readFile(file, "utf8");
  if (xml.includes(`${base}/api/typescript/`)) return;
  await writeFile(file, xml.replace("</urlset>", `${urls}</urlset>`));
}

export function apiSitemap() {
  return {
    name: "ftms-api-sitemap",
    hooks: {
      "astro:build:done": async ({ dir }) => addApiPagesToSitemap(dir),
    },
  };
}
