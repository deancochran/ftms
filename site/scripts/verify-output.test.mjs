import assert from "node:assert/strict";
import test from "node:test";
import { inspectHtml, localTarget } from "./verify-output.mjs";

test("HTML parser decodes links and collects anchor IDs", () => {
  const page = inspectHtml(
    '<h2 id="units">Units</h2><a href="../api/?a=1&amp;b=2#units">API</a><script src="/ftms/app.js"></script>',
  );
  assert.ok(page.ids.has("units"));
  assert.deepEqual(page.links, ["../api/?a=1&b=2#units", "/ftms/app.js"]);
});

test("output resolver enforces the project base without fetching external URLs", () => {
  const url = "https://deancochran.github.io/ftms/reference/api/";
  assert.match(localTarget("../../start/c/", url).file, /dist\/start\/c\/index.html$/);
  assert.match(localTarget("/ftms", url).file, /dist\/index.html$/);
  assert.throws(() => localTarget("/start/c/", url), /Missing Pages base/);
  assert.equal(localTarget("https://github.com/deancochran/ftms", url), null);
  assert.equal(localTarget("data:image/svg+xml,test", url), null);
});
