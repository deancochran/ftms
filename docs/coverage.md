# Codec coverage and evidence matrix

Status: this is an audit of the current TypeScript exports, unit tests, and v1
corpus. It is not a claim of complete FTMS conformance, device interoperability,
or Bluetooth qualification. C has unreleased bidirectional codecs and static
capability interpretation in the original audit. Kotlin now implements the shared
raw surface and static capability evaluation; see its separately scoped
[verification matrix](../packages/kotlin/docs/verification.md). Swift remains
unimplemented. Public release identities are in [released packages](released-packages.md).

## Current codec surface

| Family | TypeScript decode | TypeScript encode | Tests and v1 vectors | Equipment-side direction |
| --- | --- | --- | --- | --- |
| Measurements | All six families via normalized parsers and raw codecs | All six via raw codec | Original vectors plus 26 raw cases / 47 assertions | Implemented, unreleased addition |
| Statuses | Training and Machine Status, normalized and raw | Both raw codecs | Original vectors plus 38 raw cases / 63 assertions | Implemented, unreleased addition |
| Features | Normalized and raw words | Raw words | Original 35 vectors plus raw value corpus | Implemented, unreleased addition |
| C Features | Raw machine/target words | Raw machine/target words | Original 35 vectors plus bidirectional value corpus | Implemented |
| Supported ranges | All five, normalized/raw and caller-profile inspection | All five, raw and caller-profile inspection | Original 7 vectors plus raw value and separate synthetic inspection corpus | Implemented, unreleased addition |
| C Supported ranges | All five ranges, fixed-point | All five ranges, fixed-point | Original 7 vectors plus bidirectional value corpus | Implemented |
| C Measurements | All six families, raw fixed-point and diagnostics | All six families | 26 raw cases / 47 directional assertions plus original corpus | Implemented |
| C Statuses | Training and all 22 Machine Status opcodes | Training and all 22 Machine Status opcodes | 38 raw cases / 63 directional assertions plus original corpus | Implemented |
| Control Point requests | Both ports, all 21 raw operations | Both ports; TypeScript also has human-unit encoder | Original vectors plus raw control corpus | Both directions implemented |
| Control Point responses | Both ports, raw evidence; TypeScript retains validated API | Both ports | Original vectors plus raw control corpus | Both directions implemented |

The six measurement families are specifically Treadmill Data, Cross Trainer Data,
Step Climber Data, Stair Climber Data, Rower Data, and Indoor Bike Data. The five
ranges are Speed, Inclination, Resistance Level, Heart Rate, and Power. The v1
corpus also has 10 diagnostic vectors, which exercise malformed/truncated parsing
behavior rather than a seventh protocol family. Its category total is 97 vectors;
it must not be confused with the overall TypeScript test count or used to infer
that all test cases are shared vectors. The 350-test TypeScript run was historical
evidence from the earlier codec audit; current verification is recorded below.

The published TypeScript release is client-oriented. Unreleased source additions
now cover both directions through separate raw APIs without replacing existing
normalized/compatibility interfaces. The package keeps its existing public module
paths and 42-file artifact layout. C deliberately keeps raw integers, fixed-size
storage and compact diagnostics; it does not imitate TypeScript's allocating
metric objects, strings or UUID parser registry. These are language/API differences,
not missing wire directions. See [parity evidence](parity.md).

## Capability interpretation

The C slice includes an unreleased static capability-evidence interpreter and a
separate executable capability corpus. TypeScript now exposes the same static
interpretation as `evaluateFtmsCapabilities`; neither is an execution
permission decision, or device evidence. The contract covers all six measurement
families, five target/range relationships, and 21 operation reports using
caller-supplied discovery evidence. It preserves raw/unknown bits and UUIDs,
partial/failed discovery, read/security failures, malformed values, duplicate
ambiguity and property contradictions. It does not infer a machine type, acquire
permission, or authorize controls. See
[capability discovery](../shared/protocol/capability-discovery.md).

The separate capability runner executes 63 shared cases with complete exact
reports: discovery 12, duplicates 3, features 5, forward-compatibility 2,
measurements 7, operations 4, properties 22, ranges 8. All cases pass in the current
host run, with zero unsupported/skipped cases **in that corpus only**. Fourteen
adapter/schema/template tests check wrong outputs, malformed fixtures and failure
accounting. Native tests separately isolate all 17 target bits, every range
relationship, base procedures, all read reasons and argument/capacity atomicity.
Those test-suite counts are not additional shared vectors or device evidence.

## Evidence and future gates

Latest local additive milestone: [compatibility diagnostics and structural
coverage](compatibility-verification.md), including inspection corpus identity,
181,760 generated layout cases per port, 650 C planner budgets and completed
package/native verification. Existing historical run records below are retained
for provenance, not presented as the newest run.

### Historical pre-merge local evidence

This section records the earlier audit branch, not the current release or HEAD.
See [released packages](released-packages.md) for verified publication identity and
[boundary hardening](hardening-verification.md) for the newer local verification.
Historical input hashes below identify their recorded run, not future changes.

- Base: `2b5ff79b81639e8beeea8bc9b219cbf78c2c7194`; branch
  `audit/ftms-1-0-1`; dirty local checkout (no commit, package publication, or
  remote CI claim).
- `env -u TMPDIR pnpm verify`: passed lint, typecheck, build and packed-consumer
  checks; **552 tests in 13 files** passed. Codec v1 was **97/97 complete**;
  TypeScript simulation was **38/38 scenarios, 79/79 steps**.
- `make BUILD=build/commit-polish test` in `packages/c`: passed strict GCC/Clang
  C99 units, ASan+UBSan units, both 10,000-input fuzz suites, codec v1 **97/97**,
  controls **41 cases / 72 assertions**, capability v1 **63 complete reports**,
  simulation **38/38 scenarios, 79/79 steps**, and the real source-artifact plus
  installed C/C++ consumer checks. The capability unit suite includes one
  four-diagnostic Feature observation, oversized pre-walk rejection, and output/
  buffer atomicity checks.

| Current input | SHA-256 |
| --- | --- |
| Capability schema | `1a23dd523896d41b6aa115eea906e6f899a9cfcc8008a87d133ba8c51409ef26` |
| Capability vectors | `90a9b85e735455515c36fc089fa786bd928e217e81cf95f5ccef67c0d479d3dd` |
| Capability corpus contract | `e844292d9a916aa63db9d1f6d22de5525c1923e3584afbcc5013d93d374e6a6a` |
| Capability protocol contract | `9eab3cd08d1fdb83d26c48c62d57fe1c58a163166f414f20c697a933f8abd41e` |
| Controls schema | `3cf0e2e807293d1f5eb4460f1b122e49f689d7301e05cbc3f33268d2d423f73f` |
| Controls vectors | `766ef03b2aa0aabcef96b228bf83f9a8c8bf5bc2e3f61bd3e3779e72e8508531` |
| Simulation scenarios | `bf0e45ffd5fda95adef18b3a46a03aea87d7203d6ce15de2edea33c5b79a98f5` |

These identities cover canonical input assets, not generated logs or this
evidence document. The nine incorporated 1.0.1 errata are the nine entries in
the audit reconciliation; ESR11 and EC23224 are additional governing sources,
not additional entries in that nine-errata count.

Current evidence includes TypeScript host unit tests, schema validation, canonical
shared vectors, and the package's linked-consumer/packed-artifact checks. The
unreleased C package additionally has strict GCC/Clang host builds,
C++11 consumers linked to actual C archives, isolated-prefix C/C++ consumer
checks, an ASan+UBSan bounded fuzz run, and a Cortex-M0 freestanding compile-only
result. Its direct v1 runner passes all 97 cases with zero unsupported/skipped.
Separate bidirectional corpora cover equipment-side values and raw diagnostics;
passing these finite corpora is not exhaustive protocol conformance. Make installs
are tested through six isolated C/C++ consumers. Native CI is configured locally,
not remotely executed in this work. See the C
[verification record](../packages/c/docs/verification.md) for command-level
identity and limitations. There is no native device, PTS, Bluetooth qualification,
full embedded link/runtime, machine/firmware, mobile OS, BLE stack, or control
safety result. In particular, host and corpus evidence makes none of those claims.

Before a port is described as implemented, add port-local host tests that run the
shared corpus and report every category/case according to its
[runner contract](../shared/conformance/README.md). For C, separately demonstrate
an appropriate embedded cross-build, memory-safety/resource review, and malformed
input/fuzz evidence. For every port, record isolated consumer-installation checks
and actual-device evidence separately from host tests; PTS and Bluetooth
qualification remain separate gates.
