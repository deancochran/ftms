# Bidirectional C verification — 2026-09-28

> Historical pre-release evidence for the exact base and dirty source recorded
> below. It is not current publication status; see the
> [release matrix](../../../docs/released-packages.md).

Local, unreleased work on `scaffold/native-capabilities`, base/HEAD
`41023a60cff6efdeef5e36730c3d7356a91d26b6`, **dirty checkout**. No commit, push,
publication, deployment, remote CI dispatch or device-control action occurred.
This record supersedes intermediate codec limitations in `verification.md`.

## Actual final checks

From `packages/c`:

```sh
make BUILD=build/final-native test
make BUILD=build/final-native check-embedded
```

From the repository root:

```sh
env -u TMPDIR pnpm verify
git diff --check
```

All passed. Local logs: `packages/c/build/final-native.log`,
`final-embedded.log`, `final-typescript.log` (ignored build artifacts).

| Evidence | Actual result |
| --- | --- |
| Immutable codec-v1 | 97/97 passed, 0 failed/unsupported/skipped |
| Capability corpus | 49/49 complete reports passed |
| Control corpus | 35 fixtures, 62/62 directional assertions |
| Feature/range value corpus | 8 fixtures, 16/16 directional assertions |
| Measurement corpus | 26 fixtures, 47/47 directional assertions |
| Status corpus | 38 fixtures, 63/63 directional assertions |
| Adapter regressions | 37 Python tests passed across six suites |
| Native units | Strict C99 and Clang ASan/UBSan suites passed |
| Bounded fuzz | 10,000 codec/capability/control + 10,000 measurement/status iterations passed |
| Installation | Real Make DESTDIR install into fresh prefixes; GCC/Clang archives, two C and four C++11 consumers compiled and ran |
| TypeScript | 350 tests, original 97 vectors, lint/types/build and packed-consumer checks passed |

The original codec corpus and TypeScript implementation remain unchanged by this
milestone. Additive equipment-side fixture families do not alter npm exports.
Native CI was added as a real workflow, but was **not run remotely**. CMake,
native publication and Swift/Kotlin implementation remain out of scope.

## Failures found and resolved before final verification

- Original Control Point code narrowed enum values before validation; values 256
  and 257 could alias valid opcode/action bytes. Validate original enums first.
- Response encoding reread a structure after overlapping output writes. Stage
  the length and operands before writing; added genuine alias/canary tests.
- Clean builds used a control driver before compiling it. Fixed build order and
  verified in a previously unused build directory, not just incremental outputs.
- Measurement unavailable markers initially used the wrong signed sentinel and
  omitted energy sentinels. Corrected field-specific `0x7fff`/`0xffff`/`0xff` rules.
- The signed maximum and unsigned maxima were then over-restricted for fields
  without sentinels. New golden encoding assertions exposed valid bike +32767
  rejection (46/47 assertions before fix). Width bounds and sentinel rejection
  are now separate; all 47 assertions pass, including non-sentinel extrema.
- A schema's arbitrary 20-case ceiling blocked adding six all-field fixtures.
  Removed the ceiling and validated all 26 fixtures before running codecs.
- Weak intermediate adapter comparisons checked only status codes or unrelated
  dictionary inequality. Replaced with real complete-field comparisons, mutation
  tests against runner behavior, and explicit direction/outcome accounting.
- An intermediate coverage statement incorrectly said 75 passed/26 unsupported;
  it was 75/22 of 97. Final accounting is 97/0, not the sum of separate corpora.

Independent review found no remaining must-fix defect in its final scoped review.
It noted an additional regression opportunity: direct available-unsigned-energy
sentinel encoder rejection assertions. Existing sentinel tests and golden cases
are finite evidence, not an exhaustive input proof.

## Embedded evidence and limits

Clang Cortex-M0 `-Oz -ffreestanding` compilation succeeded for all five sources.
Object text sizes: base codecs 650 bytes, control 1000, capabilities 2242,
measurements 1648, statuses 1664; data/BSS zero. These are toolchain-specific
object totals, not linked firmware size. Compiler runtime references include
memory helpers and `__aeabi_llsl`; a target runtime must supply them. Stack-usage
files report per-function frames, not whole-call-chain or interrupt bounds.

No embedded executable link/runtime, board execution, real-device BLE exchange,
Bluetooth PTS/qualification, actuator safety or mobile lifecycle evidence exists.
Passing finite corpora does not imply complete FTMS interoperability or permission
to execute controls. Platform/security/control ownership remain caller concerns.

## Additional corpus identity

SHA-256 identities below are independent of package version. Each corpus README
is its comparison/direction-accounting contract. Original codec/capability
identities remain in the earlier verification record and actual runner reports.

| Family | Asset | SHA-256 |
| --- | --- | --- |
| controls | schema | `d80eb0aa1fdb7c3ecc9481b86f5bd12af9389742f6454fe30b2f2e781d6c45fc` |
| controls | vectors | `7d5273729cdeb157795a6a17c94ef76346f430e1b01c24f7be753db942115999` |
| controls | README | `01b82dae7d0071b918f1406b92ffc948b73ed25acd691eefab71cd78cc3a056a` |
| values | schema | `5761e04084820b61349598c38c0532f6f3e98e0079ab2e8e319866319c152772` |
| values | vectors | `72c4f718c8e892ca567fdc081181dfc8e3fe836a011ca52cdd598d9a63212d06` |
| values | README | `f41a894786b204996a32342dfa505d1b1e0ff061a042a02338afc092c5cc1366` |
| measurements | schema | `f8dd737c4d4aed11650bf8be3ada0f371d81d5a44e144e2eb25a5483332477c1` |
| measurements | vectors | `ac9f20a9bff33edd94e44fac3f9b794942e4d3c0d346fd90a8ed013766e28ec0` |
| measurements | README | `e33087a1d48977a6124fdcd74b9e78b0abbc8330bbde37c8a52b6c170441c794` |
| statuses | schema | `db54281b8edf4c10cbeefa45184a3ce158a602713f36d111e430b43b1accb5ec` |
| statuses | vectors | `ccd15d9ce4214bcc486fc696b5cfe16752f196e48455da330a437308b2920689` |
| statuses | README | `58a1d0e2f76fae8efdad18e8303f5d50da96d26465ddd90c901f7d3a3722b1c2` |
