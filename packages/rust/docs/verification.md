# Rust port support and evidence

## Supported raw codec matrix

| Surface | Decode | Encode | Evidence |
| --- | --- | --- | --- |
| Fitness Machine Feature | Yes | Yes | values-v1 literal cases |
| Five Supported Ranges | Yes | Yes | values-v1 literal cases and boundary tests |
| Range inspection | Yes | N/A | all 9 inspection-v1 complete reports |
| Control Point requests (0x00--0x14) | Yes | Yes | controls-v1 literal cases and width tests |
| Control Point responses | Yes | Yes where canonical | controls-v1, including spin-down and diagnostics |
| Six measurement families | Yes, including partial diagnostics | Yes where canonical | measurements-v1, compatibility-v1, independent structural matrix |
| Machine Status (all 22 defined opcodes) | Yes, including unknown/partial evidence | Yes where canonical | statuses-v1 and every opcode/action/prefix/capacity boundary |
| Training Status | Yes, including raw invalid UTF-8 | Yes where canonical | statuses-v1, all flags/codes, UTF-8 and borrowed-text tests |

The crate is pure `no_std`, allocation-free protocol code. It does not provide
BLE/GATT lifecycle, discovery, permissions, control authorization, device
testing, PTS, or Bluetooth qualification.

## Measurement/status milestone: local verification identity

Checkout: `feat/rust-port`, base/HEAD
`8a0006671df3babf4276ed3a97607ef7bc4fd46e`, **dirty**, with the Rust package still
uncommitted. This records local `ftms` **0.1.0** candidate evidence, not a release.
Rust/Cargo **1.85.1** were used from the ignored package-local toolchain. During
this codec milestone no
global toolchain defaults, other language packages, canonical shared assets, CI
configuration or release automation were changed.

### Literal corpus accounting

All schema-backed runners validate the canonical schema and unique/nonempty
case IDs. Complete raw objects are compared exactly; encoding takes independent
literal expected values, not decoder output. Decode-only diagnostic cases have
no canonical-encoding pass claim. Each report identifies source HEAD/dirty state,
schema/vector/contract hashes and every case/direction outcome.

| Corpus | Cases | Directional assertions/reports | Category cases |
| --- | ---: | ---: | --- |
| values/v1 | 8 | 16 | Features 3; ranges 5 |
| inspection/v1 | 9 | 9 complete reports | Inspection 9; no schema asset |
| controls/v1 | 41 | 72 | Requests 27; responses 6; invalid 8 |
| measurements/v1 | 26 | 47 | Treadmill 6; Cross 3; Step 3; Stair 3; Rower 3; Bike 6; invalid kind 2 |
| statuses/v1 | 38 | 63 | Machine 28; Training 10 |
| compatibility/v1 | 9 | 18 | Measurements 6; ranges 3 |

All listed executions have **zero failures, unsupported cases, skips and runner
errors**. The immutable normalized codec-v1 (97 cases) and capability-v1 corpora
are **not claimed** by this raw-codec milestone. Schema format v1, FTMS
specification revisions, package versions and these fixture content hashes are
independent identities.

### Structural, boundary and malformed-input evidence

The runner consumes `ftms-measurement-matrix-v1` directly from canonical
`layouts.json`; it does not import production descriptors. Across ten applicable
layout/format configurations it verifies:

- **181,760** structural layouts, **363,520** independent encode/decode assertions;
- **46** individual unavailable-sentinel cases, **92** directional assertions;
- **47** RFU-bit cases, **94** decode/encoder-rejection assertions;
- **315** incomplete prefixes with exact complete-field masks and offsets.

Per-family structural case counts are Treadmill 16,384; Cross Trainer 131,072;
Step Climber 512; Stair Climber 1,024; Rower 16,384; Indoor Bike 16,384. More Data
and Cross Trainer direction states are included. This is complete field-presence
enumeration, not every numeric value or real-device behavior. The C-only planner
budget contract is not claimed; Rust does not yet plan or assemble fragments.

Additional package tests check every measurement field's extrema and adjacent
out-of-width values; sentinel eligibility; exact/short storage and no-write-on-
error behavior; profile isolation and no automatic format inference; all Machine
Status opcodes, action bytes, prefixes and invalid parameter shapes; all 65,536
Training Status flag/code combinations; valid/invalid UTF-8 boundaries; and
8,192-byte caller-bounded training text. A deterministic **10,000-packet**
malformed-input regression exercises all six kinds and all four option
combinations plus both status decoders/encoders. It is not coverage-guided fuzzing.
Runner self-tests deliberately inject/catch errors to verify failed outcomes are
retained; their printed panic text under `--nocapture` is expected.

### Exact new corpus and comparison-contract identity

All paths below are relative to `shared/`; the files remain unchanged at the
source HEAD above. The matrix has no schema asset. The wire compatibility
contract pins independent, explicit selections rather than equipment inference.

| Asset | SHA-256 |
| --- | --- |
| `conformance/measurements/v1/schema.json` | `f8dd737c4d4aed11650bf8be3ada0f371d81d5a44e144e2eb25a5483332477c1` |
| `conformance/measurements/v1/vectors.json` | `ac9f20a9bff33edd94e44fac3f9b794942e4d3c0d346fd90a8ed013766e28ec0` |
| `conformance/measurements/README.md` | `e33087a1d48977a6124fdcd74b9e78b0abbc8330bbde37c8a52b6c170441c794` |
| `conformance/statuses/v1/schema.json` | `db54281b8edf4c10cbeefa45184a3ce158a602713f36d111e430b43b1accb5ec` |
| `conformance/statuses/v1/vectors.json` | `ccd15d9ce4214bcc486fc696b5cfe16752f196e48455da330a437308b2920689` |
| `conformance/statuses/README.md` | `58a1d0e2f76fae8efdad18e8303f5d50da96d26465ddd90c901f7d3a3722b1c2` |
| `conformance/compatibility/v1/schema.json` | `6422e6aeafe238143d7b63f1f48093f11a260b007032fbc938898761f539dea0` |
| `conformance/compatibility/v1/vectors.json` | `f009df66aebd7a8ee820f18b7eb085f87296f65eda90aca0448cb81966aaaf4f` |
| `conformance/compatibility/README.md` | `bf3e656f42d3cdefedf4806d2fea2502e5f58150854f96b0121e67a1d979a423` |
| `conformance/measurement-matrix/v1/layouts.json` | `97d0785c935edb2888ce6dbd74746d1818440e67bfdb3709c4092d92e2665852` |
| `conformance/measurement-matrix/v1/README.md` | `137fd76c48c63ed79ac2e7423885228e50523b118b9ef73a6f9782a0eb437705` |
| `protocol/wire-compatibility.md` | `32bb7bf4488b8fd306a621508722c38e46bf410b73501f80b4f2bbcb1249d27f` |

### Verified commands and installation evidence

Run from `packages/rust` with the package-local toolchain environment documented
in the README. Results for this milestone:

| Command | Actual result |
| --- | --- |
| `cargo fmt --check` | Passed |
| `cargo test --locked` | **20 integration tests + 3 Rustdoc tests passed** |
| `cargo test --locked --test raw_conformance --test measurement_status_conformance --test measurement_matrix -- --nocapture --test-threads=1` | All corpus and structural accounting above passed |
| `cargo clippy --locked --all-targets -- -D warnings` | Passed |
| `cargo build --locked --target thumbv6m-none-eabi` | Passed; compile-only Cortex-M0 `no_std` evidence |
| `RUSTDOCFLAGS='-D warnings' cargo doc --locked --no-deps` | Passed |
| `cargo package --locked --allow-dirty` | Passed archive construction and packaged-source build verification |
| `TMPDIR=/tmp sh tests/consumer.sh` | Passed isolated consumer build **and execution** against extracted `.crate` source |

The consumer executes existing Feature/range/control operations, all six
measurement decoders/encoders, explicit signed resistance, Machine Status and
borrowed-text Training Status. It cannot rely on repository fixture files.
Source-checkout tests, target outputs and the toolchain are excluded from the
archive. Cargo warnings about excluded integration tests are expected.
`/tmp` was used because the preferred `/tmp/opencode` was not writable on this
host. Detailed run output is local/ignored under `target/verification/`.

An independent static review found no blocking measurement/status codec defects.
At this codec milestone only Rust 1.85.1 local host/package results and Cortex
compilation had been verified. Additional pipeline work is recorded below;
MCU linking/execution, Rust BLE/device testing, PTS and Bluetooth qualification
remain unverified. No equipment commands were sent.
Normalized feature/capability interpretation remains unimplemented. At this
milestone nothing had been committed, merged, pushed or published; the package
name/version were candidate metadata, not evidence of registry availability or
publication.

## Publishing-pipeline addition

The package now has a reusable host CI matrix and a separate `rust-v*` publishing
workflow, with a pinned-release artifact, clean/tag/main gates, checksum-aware
reruns, a public registry consumer and checksum-pinned, no-overwrite GitHub assets. See
[`releasing.md`](releasing.md) for commands, credential handling and exact gates.

Additional **local Linux** verification has passed on both the pinned Rust/Cargo
**1.85.1** and current stable **1.98.1**: formatting, Clippy, the same 20 integration
tests and three Rustdoc tests, Cortex-M0 compilation, strict documentation,
Cargo packaging and the portable extracted-archive consumer. Each stable check
used the ignored local toolchain with an explicit override; the release pin and
MSRV remain 1.85.1, and no global toolchain default was changed.

The **24 passing offline Python tests** exercise tag/commit/version agreement,
changelog/clean-source/main ancestry, archive safety and scope, prepared evidence
and toolchain binding, reproducible bytes, fail-closed registry queries, matching
version reruns, credential separation, and GitHub release evidence. These are
mocked publication tests, **not** proof of a successful remote upload. They also
cover delayed API/index propagation, exhausted retries, actual simulated upload
failure, GitHub metadata/asset conflicts and destination-scoped authentication.

Both workflow files passed **actionlint 1.7.12**. Two separate real local MSRV
candidate preparations produced byte-identical `.crate` files and `release.json`
records; their SHA256SUMS checks and extracted consumers passed. The archive
contains only the library, package metadata, license, changelog and docs, not
verification tooling, fixtures or credentials. Actual invocations confirmed that
dirty-source preparation/publication fail before registry/authentication work.
These candidates remain dirty and are deliberately ineligible for release.

At pipeline setup, the `crates-io` GitHub environment was configured for `rust-v*`
tags with the encrypted publishing secret, while workflow files were still
local/uncommitted. No release tag or package was published during setup.
Feature/capability interpretation remains out of scope.

## Integration verification

The Rust implementation and workflows were committed and pushed for
[PR #14](https://github.com/deancochran/ftms/pull/14). The first remote Rust matrix
passed the codec tests but correctly rejected an unintended tracked `.gitignore`
in the crate. Commit `a7cde5d` explicitly excludes that repository-only file;
the strict archive check remains in place.

Two clean local MSRV preparations at that commit built and executed their
extracted-package consumers and produced identical archives and release records.
The archive SHA-256 was
`68a6c1fcf23d6742fdc02b2fa30f9a8c1ab30ff1328356b519f00375d753327b`.
This identifies that commit's archive, not a later merge/tag or registry version.
All 24 offline release-policy tests and the 588-test TypeScript push gate passed.
The pull request's checks provide the authoritative remote execution status.
First registry authentication/publication, docs.rs and a real public-registry
consumer remain unverified; no Rust release tag has been created.
