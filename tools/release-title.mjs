#!/usr/bin/env node
// Read-only title generator for future releases, never a publication gate.
import { releaseTitle } from "./port-catalog.mjs";
import { readiness } from "./release-prepare.mjs";

const [port, ...extra] = process.argv.slice(2);
if (!port || extra.length) throw new Error("usage: node tools/release-title.mjs PORT");
const { version } = await readiness(port);
console.log(releaseTitle(port, version));
