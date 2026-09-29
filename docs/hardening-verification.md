# Boundary hardening — 2026-09-29

**Historical pre-release record.** Dirty/uncommitted and unchanged-version
statements below describe that run. Later release preparation sets TypeScript
0.4.0 and C 0.2.0; see [released packages](released-packages.md) for publication.

Local work in `fix/protocol-boundary-hardening`, based on clean published-source
commit `74f1552959d96755f38eac42f6999a5b04088b2f`. This report describes dirty,
uncommitted changes, not a new release. No version, tag or registry was changed.
The published baseline is recorded separately in `released-packages.md`.

## Changes and verification

- Format options and optional C.7 evidence must use own data properties;
  inherited selections and getters are rejected. Realm identity is not used to
  reject ordinary foreign objects; null-prototype records remain supported.
- Normalized control inputs are range-checked before grid alignment. Binary64
  representation tolerance is documented in `shared/protocol/numeric-inputs.md`.
  Raw C and TypeScript integer contracts, default layouts and corpus JSON are
  unchanged. This deliberately tightens previously accepted invalid inputs.
- Release/package overview documentation now recognizes npm 0.3.0 and C 0.1.0.

Test-first evidence: the new boundary suite initially had **21 failures and
2 passes**. After implementation it passed all **23 tests**. Coverage includes
all normalized scalar operand fields, signed/unsigned extrema, adjacent
representable out-of-bound values, half increments, finite-number rejection,
inherited profiles/C.7, getter rejection and foreign/null-prototype defaults.

Completed commands:

```sh
pnpm install --offline --frozen-lockfile --ignore-scripts
pnpm --dir packages/typescript exec vitest run test/boundary-hardening.test.ts
pnpm --dir packages/typescript check-types
env -u TMPDIR pnpm verify
make -C packages/c BUILD=build/hardening test
git diff --check
```

TypeScript: **575 tests / 14 files passed**, including the original 97 codec
vectors, capability/compatibility fixtures and 38 simulation scenarios/79 steps.
Lint, types, packed consumers, source maps, browser resolution and unchanged
42-file artifact allowlist passed. C: all corpus, sanitizer, bounded fuzz,
simulation, installed-consumer and source-artifact checks passed. No C production
source changed. Logs are ignored under `packages/c/build/hardening-{ts,c}.log`.
Offline dependency installation reused cache and changed no lockfile.

The attempted implementation delegation could not access filesystem tools; it
made no edits. Implementation and verification were completed in the coordinator
lane. No independent follow-up review is claimed by this record.

## Next gates

1. Review and authorize integration/release of this local hardening change.
2. User selected an embedded C pilot, **computer first**, with a **Wahoo KICKR
   CORE and Zwift Cog**. The user's screenshot confirms firmware **2.5.37**;
   local inspection confirms EndeavourOS/Linux x86_64, BlueZ **5.87**, active
   Bluetooth service and an unblocked `hci0` controller. The initial preparation
   made no radio interactions. Subsequent explicit user authorization enabled a
   passive scan/connect/read/subscribe session: **45 packets captured and decoded,
   45 complete C/TypeScript raw reports matched**, no Control Point writes. See
   `equipment-results/2026-09-29-kickr-core-linux.md` for scope and the observed
   six-byte Resistance Range compatibility limitation. The new
   `examples/c-passive-replay` is a real installed-library consumer with strict
   hexadecimal parsing and raw Indoor Bike Data output, not a transport or an
   automatic format detector. Its synthetic boundary tests passed through CMake
   installation. CMake was initially absent from PATH; the existing installation
   under `/opt/android-sdk/cmake/3.22.1/bin` was used without downloading tools.
   The source-bundle verifier now tests this example against its relocated install
   so normal native CI also exercises offline replay. Hardware evidence is now
   **partial passive interoperability**, not full device or MCU verification.
3. Swift/Kotlin implementation is deferred by the user's pilot choice. Later,
   select one native port based on its consumer: Swift/SwiftPM for Apple, or
   Kotlin/JVM for Android/Java. Require real compilers, canonical corpus tests,
   isolated consumer installation and platform CI. No placeholder package or
   native implementation has been added while that choice is unresolved.
4. If embedded adoption is first, link and execute a representative C consumer on
   an identified MCU/toolchain; previous compile-only evidence is not execution.

These dependent actions do not block the completed local hardening. Neither a
simulator nor the published-source review establishes device interoperability,
control safety or Bluetooth qualification.
