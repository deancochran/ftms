import { rm } from "node:fs/promises";

// Only generated package-local outputs; canonical repository assets are untouched.
for (const asset of ["dist", "conformance", "LICENSE", "SECURITY.md"]) {
  await rm(new URL(`../${asset}`, import.meta.url), { force: true, recursive: true });
}
