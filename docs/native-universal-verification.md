# Native universal measurement verification

Local, unreleased source verification on 2026-10-02. Integration branch:
`feat/native-universal-measurements`, base
`c89380df6f821221f774bb57488bac6d4645659d`, with uncommitted source changes.
No package versions, canonical corpora, or TypeScript source changed. No remote
publication, commit, push, merge, or deployment was performed for this work.

## Final combined-checkout checks

| Port | Command / evidence | Result |
| --- | --- | --- |
| C | `make BUILD=build/universal-integrated test` | C99, GCC/Clang, ASan/UBSan including universal tests, fuzz tests, 97/97 codec cases; installed 2 C and 4 C++ consumers plus source archive routes passed |
| Rust | Rust 1.85.1: `cargo fmt -- --check`, `cargo test --locked`, Clippy with warnings denied, `thumbv6m-none-eabi` build, Rustdoc with warnings denied, `python3 scripts/consumer.py --allow-dirty` | All passed, including extracted-archive universal consumer and actual embedded `no_std` compilation |
| Go | `bash scripts/verify.sh` | Formatting, vet, race tests, tagged conformance, build and isolated local module-zip consumer passed |
| Kotlin | `bash verification/verify.sh` | Host tests, binary API baseline, local Maven artifact and Java/Kotlin consumers passed; Android consumer compiles the new decoder and named metric access |
| Python | `uv run --locked --group dev python scripts/verify.py` | Python 3.11 and 3.14: 172 tests each; Ruff, strict Mypy, structural matrix and isolated artifact/type consumers passed |
| Swift | Swift 6.0.3: `python3 packages/swift/Verification/verify.py` | 17 tests, release build, 282/282 reconciled fixture cases and local SwiftPM consumer passed |
| Dart | Dart 3.11.0: `python3 tool/verify.py --package` | Analysis, tests, complete VM conformance, extracted-package analysis/run/native compilation passed |
| C# | .NET 10.0.100: `bash verification/verify.sh` | 15 tests; 228 codec cases / 330 comparisons, 63 capability cases, structural matrix; installed `netstandard2.1` and `net10.0` consumers passed |

The codec-v1 corpus contains 97 cases: 35 features, 7 ranges, 21 controls,
12 control responses, 8 measurements, 4 statuses and 10 diagnostics.
C and Python explicitly reported 97 passed, zero failed/unsupported/skipped.
Dart also reconciled values 8/8, controls 41/41, raw measurements 26/26,
statuses 38/38, inspection 9/9, compatibility 9/9 and capabilities 63/63.
Swift's 282 reconciled cases had no failed, unsupported, skipped or unresolved
cases. C# reported zero failed/unsupported/skipped comparisons.
Structural matrix checks cover 181,760 structures, 46 sentinels, 47 reserved-bit
cases and 315 incomplete prefixes; these are distinct from corpus case counts.
Package-owned universal-interface tests and installed consumers are additional
evidence, not new canonical corpus cases.

Repository-wide `pnpm verify` passed (including all 604 TypeScript tests), as did
`pnpm verify:package`, `pnpm site:verify` (165 HTML files), and
`pnpm site:test:browser` (6 desktop/mobile tests). Final `git diff --check` passed.

## Canonical identity

Unchanged SHA-256 identities used by the verification:

| Asset | SHA-256 |
| --- | --- |
| `shared/conformance/README.md` comparison contract | `4ee407ecca3cdce77289ff15920bd831dc6687e5dff0ac9c0a8edf39d6034cc9` |
| `shared/conformance/v1/schema.json` | `e6d976172a32e3124602d17e46ed5fbab337f4f1d6535aec85a83069637268e0` |
| `shared/conformance/v1/vectors.json` | `9b5b61353b191179cc629d8c459b2a185b9e03b7ce5f3f51b715520162e8a5c7` |
| `shared/conformance/measurements/v1/schema.json` | `f8dd737c4d4aed11650bf8be3ada0f371d81d5a44e144e2eb25a5483332477c1` |
| `shared/conformance/measurements/v1/vectors.json` | `ac9f20a9bff33edd94e44fac3f9b794942e4d3c0d346fd90a8ed013766e28ec0` |

## Review corrections and limits

Review corrected Go/Kotlin family-specific elevation scaling, Dart default
re-encoding format retention, Rust 1.85.1 const compatibility, UUID alias syntax,
Go format-provenance access, and unreleased-feature labeling. Added direct
canonical all-field dispatcher coverage for Dart/C#, C metric-mapping checks,
and Android compilation of the new public measurement API.

An initial final Dart run failed two test-source lint rules; these were fixed
and the full verifier rerun successfully. Initial Rust/Swift toolchain blockers
were resolved with existing cached SDKs, without installing new toolchains.
Swift emitted non-fatal compatibility-library warnings; Gradle emitted existing
deprecation warnings. No final required gate remains blocked.

This evidence does not establish live Bluetooth interoperability, device or
emulator execution, PTS/qualification, registry publication, or C# NativeAOT
verification. Local test archives retain the existing versions and must not be
published as replacements for immutable released artifacts. A separate release
must select versions and rerun publication-specific gates.
