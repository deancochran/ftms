# Adoption-readiness verification — 2026-09-29

Local work on `docs/adoption-readiness`, based on
`8a0006671df3babf4276ed3a97607ef7bc4fd46e`. This is an uncommitted local milestone,
not publication, remote CI, main-branch integration or equipment evidence.

## Delivered scope

| Checklist phase | Result |
| --- | --- |
| Baseline and release facts | Existing TypeScript and C suites passed before edits; npm/GitHub metadata verified read-only |
| Status and trust | Canonical release matrix; security wording and current C guidance corrected; historical records labeled at their own entry points |
| Positioning and first use | Neutral descriptive README, current-release npm quickstart, released C/C++ installation walkthrough; older npm example preserved |
| Integration | Cookbook, tested DataView/base64 boundaries, API selection index, troubleshooting and a canonical reading order |
| Reference | Pinned development-only TypeDoc and reproducible local HTML; C public-header/function index |
| Participation | Contributor guide, four issue templates, roadmap and explicit non-goals |
| Automation | Offline documentation checker with negative tests; current npm examples, README snippet and API-index functions checked against packed public exports |

No TypeScript/C protocol source, public C header, export map, runtime dependency
or canonical conformance vector was changed. TypeDoc is a development dependency;
base64-js is example-only. Existing package names and versions are preserved.

## Verification performed

Environment: Linux, Node 22.23.2, pnpm 10.33.0, GCC/G++ 16.2.1,
Clang 22.1.8 and CMake 3.22.1. CMake was added to PATH for the manual walkthrough;
the repository native verifier also supports its existing `CMAKE` override/fallback.

- `pnpm install --frozen-lockfile --ignore-scripts`: lockfile is reproducible.
- `pnpm verify`: TypeScript type checks, **588 tests in 16 files**, fresh build,
  packed-artifact verification, documentation checks and TypeDoc HTML generation.
- `pnpm verify:package`: unchanged exact 42-file artifact allowlist and export
  map; source maps, declarations, runtime neutrality, browser bundle resolution,
  historical/current examples, README output and API-index function names.
- `pnpm docs:check`: four checker tests including negative cases, plus repository
  local Markdown targets/heading anchors and quickstart release/hash consistency.
  It checks inline destinations and reference definitions, not undefined reference
  usages, arbitrary HTML or remote URL availability.
- `make -C packages/c test`: full native host suite, sanitizers, corpus runners,
  deterministic fuzz suites and installed/source-artifact consumers. Codec v1
  reports **97 passed, 0 failed/unsupported/skipped**. The client example executes
  as both C99 and C++11 against the installed C library.
- Isolated npm `@deancochran/ftms@0.4.0` consumer: quickstart and recipes passed
  against registry bytes, separately from the locally packed candidate.
- Downloaded C `c-v0.2.0` archive: SHA-256 and exact source-manifest verification,
  installed/vendored/FetchContent C/C++ consumers and repository examples passed.
  Artifact SHA-256:
  `3aa60d809f3dcd02634417018d39f325c46a552734f0fe311ba748261914e61f`.
- The exact C quickstart shell blocks were extracted from its README and executed
  in a fresh isolated directory, including downloads and both C/C++ tests: **1.81 s**
  in this environment. npm install/start/test in an isolated consumer with cache
  available took **0.34 s**. These are automated runs, not human usability timings.
- `git diff --check`: no whitespace errors.

## Corrections caught during verification and review

- Corrected the new JavaScript assertions to use `hrBpm` and include the range's
  `kind` discriminator; installed-package runs exposed both mistaken assumptions.
- Fixed an existing broken historical coverage anchor.
- Corrected C quickstart configuration to pass `CMAKE_BUILD_TYPE=Release` as well
  as `--config Release`. The exact copy/paste walkthrough initially failed without
  the former on a single-configuration generator; it passed after correction.
- Independent review identified stale C release/design records, misleading Make
  availability for the minimal archive, and an overly broad checker description.
  Current guidance and historical banners were corrected; Make is checkout-only.
- An initial log redirection outside the checkout was denied; verification was
  rerun with ignored checkout-local logs. No gate was bypassed.

## Limits and delivery

The two-minute discovery and five-minute human onboarding targets were not tested
with an independent human participant. Automated walkthrough timings do not prove
those usability targets. The TypeDoc site built and its assets were served locally,
but automated visual/browser interaction was unavailable in this OpenChamber
client; no visual QA claim is made. The temporary preview server was stopped.

No live Bluetooth, Metro/mobile runtime, physical controls, firmware execution,
PTS or qualification testing was performed. No remote CI was dispatched, no
accounts changed, and no commit, push, merge, publication or deployment occurred.
The documentation URLs targeting main become available only after approved
integration. Other language-port branches are outside this source-tree assessment.
