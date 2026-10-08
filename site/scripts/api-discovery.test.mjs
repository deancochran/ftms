import assert from "node:assert/strict";
import test from "node:test";
import { injectApiDiscovery } from "./api-discovery.mjs";

test("TypeDoc HTML gains one visible and machine-readable Markdown representation", () => {
  const output = injectApiDiscovery(
    "<!doctype html><html><head><title>API</title></head><body><main>API</main></body></html>",
    "/ftms/api/typescript/classes/Foo.md",
  );
  assert.match(output, /rel="describedby" href="\/ftms\/llms.txt"/);
  assert.match(
    output,
    /rel="alternate" type="text\/markdown" href="\/ftms\/api\/typescript\/classes\/Foo.md"/,
  );
  assert.match(output, />AI documentation</);
  assert.match(output, />View Markdown</);
  assert.equal(injectApiDiscovery(output, "/ftms/api/typescript/classes/Foo.md"), output);
});
