# Documentation site verification

The private Astro 7 / Starlight site reuses canonical Markdown and generated
TypeDoc, with a `/ftms` GitHub Pages base. Biome formats/lints authored supported
files; no additional UI framework was needed. See [site operations](../site/README.md).

## Verified locally before publication

- `pnpm verify`: TypeScript types, 588 tests, build, packed consumers,
  documentation checks (73 Markdown files), and TypeDoc generation passed.
- `make -C packages/c test`: full native suite, sanitizers, corpus checks,
  installed consumers and C/C++ examples passed.
- `pnpm site:verify`: content/output unit tests, Astro checks, production build,
  Pagefind index and link/anchor/asset verification passed for **139 HTML files**.
- `pnpm site:test:browser`: all **six** Chromium desktop/mobile checks passed,
  including search, themes, navigation and generated TypeScript API access.
- Independent read-only review found no code-level blocking issues. Its pending
  browser-rerun requirement was satisfied by the six passing checks above.

Initial output checks caught missing favicon and double-prefixed sidebar paths;
both were fixed. Browser checks initially used the wrong search input role and
encountered Astro's agent auto-backgrounding; the corrected tests passed against
the real production preview with Playwright owning the server lifecycle.

Remote main advanced during implementation. Its Swift/Kotlin/Python changes were
merged, stale scaffold claims reconciled, and their canonical guides added to the
site without modifying their protocol implementations. Native release evidence
remains package-specific; these site checks do not reverify those releases.

Astro emits non-fatal notices for Starlight's optional empty i18n collection and
default 404 entry. Generated 404 output exists and local links pass validation.
Local browser evidence is Chromium emulation, not physical mobile devices or BLE.
GitHub Actions and the live URL must be verified separately after publication.
