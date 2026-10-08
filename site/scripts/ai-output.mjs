import { cp, rm } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const generatedOutput = fileURLToPath(new URL("../.generated/ai-docs/", import.meta.url));

export function aiDocsOutput() {
  return {
    name: "ftms-ai-docs-output",
    hooks: {
      "astro:build:done": async ({ dir }) => {
        const output = fileURLToPath(dir);
        for (const file of ["index.md", "llms.txt", "llms-full.txt"]) {
          await rm(new URL(file, dir), { force: true });
        }
        await cp(generatedOutput, output, { recursive: true });
      },
    },
  };
}
