# Compatibility diagnostics and structural coverage — 2026-09-29

Local, uncommitted work on `fix/protocol-boundary-hardening`, based on
`74f1552959d96755f38eac42f6999a5b04088b2f`. This follows the hardening and passive
pilot recorded separately. Nothing in this milestone was published or tested
through new Bluetooth operations. Package versions remain unchanged.

## Delivered

The maintained [layout inventory](compatibility-inventory.md) records fixed,
flag-driven and variant layouts, source references and implementation limits.

- Additive TypeScript `inspectFtmsRangeRaw` and C `ftms_inspect_range` /
  `ftms_inspect_range_with_format`: selected profile, actual/expected lengths,
  selected result and structural candidates. No format guessing or fallback.
- Existing capability-v1 reports, decoder defaults and existing corpus JSON
  remain unchanged. Inspection is companion evidence: callers retain range kind,
  explicit options and original bytes alongside the report. There is no new
  automatic capability evaluator or command policy.
- Separate literal synthetic inspection corpus with **9 exact whole-report
  comparisons per port**, including selected failure with alternative success.
- Separate measurement structural matrix with **181,760 generated cases per
  port**, each checking decode and encode against constructed expectations.
  Also **46 sentinel-position** and **47 RFU-bit** cases, and incomplete prefixes
  of all ten supported complete layout configurations.
- C adds ten complete snapshots and **650 planner-budget cases** with reassembly
  comparison, query-count checks and explicit insufficient-budget failures.
  Total streaming C records: **181,863**, repeated under ASan/UBSan.
- Installed C consumers now explicitly link and execute both new inspection
  entry points, including a selected failure with a valid alternative.

These are separately declared test expectations, not expected results generated
from production table imports. The matrix remains a shared test oracle, not proof
independent of the protocol review; existing literal vectors remain necessary.

## Contract and corpus identity

Inspection comparison contract: `shared/conformance/inspection/v1/README.md`.
Literal fixture SHA-256:
`153b613e6e8a59185ec89267af90fbb88cf3d7806a558a35761f30bee8ca6786`.

Structural contract: `ftms-measurement-matrix-v1`, documented under
`shared/conformance/measurement-matrix/v1/`. Layout declaration SHA-256:
`97d0785c935edb2888ce6dbd74746d1818440e67bfdb3709c4092d92e2665852`.

These are separate from the original codec-v1 and capability-v1 identities and
from npm/C package versions. No private device capture was added to a corpus.

## Completed verification

```sh
env -u TMPDIR pnpm verify
make -C packages/c BUILD=build/compat-final test
make -C packages/c BUILD=build/compat-final check-embedded
git diff --check
```

- TypeScript: **588 tests / 16 files**, lint, types, examples, build and packed
  package checks passed. The matrix is one test containing many generated cases;
  it is not hundreds of thousands of separate Vitest registrations.
- An isolated consumer of a freshly packed npm archive also imported the new
  function through `@deancochran/ftms` and exercised default mismatch and explicit
  alternative success. The preferred `/tmp/opencode` location was not writable;
  the check was rerun successfully in an isolated directory under ignored C build
  storage. No dependency downloads or package publication occurred.
- C: all units, shared corpus adapters, both matrix passes, sanitizer/fuzz,
  simulation, compiler/installed consumer and source-bundle gates passed.
- Cortex-M0 compilation passed. This is not linked MCU execution or a board test.
- Ignored logs: `packages/c/build/compat-final-{ts,c,embedded}.log`.

During development the first matrix test exposed an incorrect test expectation:
the raw comparison model represents sentinel values as zero plus an unavailable
mask, not the sentinel integer. The expectation was corrected to the existing
documented contract; production measurement logic was not altered to pass it.
Independent inspection review identified selected-value object aliasing in TS
and unclear C invalid-value documentation. The selected value is now copied and
the C status-discriminated value invariant is documented. All final checks above
passed after those corrections.

Final independent review found no actionable correctness or boundary defects.
Its outstanding verification note is resolved: the installed-consumer change
preceded the final successful TypeScript, native and embedded runs. Subsequent
changes were documentation-only, and final `git diff --check` passed. Review
confirmed matrix accounting, complete inspection-report comparisons, preserved
profile selection and wiring into native CI's existing test command. No remote
CI run is claimed for these uncommitted changes.

## Boundaries and remaining work

This milestone does not resolve conflicting physical-unit annotations, certify
devices, select formats automatically, add advertising codecs or add a TypeScript
production assembler. The structural enumeration is not every numeric input,
every packet-loss sequence or every device firmware. Existing numeric/fuzz and
simulation tests are complementary. Further device/reference evidence is still
needed, especially for resistance scale. Nothing here permits executing controls.
