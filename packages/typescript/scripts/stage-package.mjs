import { copyFile, mkdir, rm, writeFile } from "node:fs/promises";

const packageRoot = new URL("../", import.meta.url);
const repositoryRoot = new URL("../../", packageRoot);

// Both module formats are compiled from the same source. This local scope also
// makes the matching .d.ts files CommonJS for NodeNext TypeScript consumers.
await writeFile(new URL("dist/cjs/package.json", packageRoot), '{"type":"commonjs"}\n');

// Distribution snapshots only; package-owned README and changelog stay untouched.
await rm(new URL("conformance/", packageRoot), { force: true, recursive: true });
await mkdir(new URL("conformance/v1/", packageRoot), { recursive: true });
for (const [source, destination] of [
  ["LICENSE", "LICENSE"],
  ["SECURITY.md", "SECURITY.md"],
  ["shared/conformance/v1/schema.json", "conformance/v1/schema.json"],
  ["shared/conformance/v1/vectors.json", "conformance/v1/vectors.json"],
]) {
  await copyFile(new URL(source, repositoryRoot), new URL(destination, packageRoot));
}
