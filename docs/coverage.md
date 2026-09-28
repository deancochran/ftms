# Codec coverage and evidence matrix

Status: this is an audit of the current TypeScript exports, unit tests, and v1
corpus. It is not a claim of complete FTMS conformance, device interoperability,
or Bluetooth qualification. C has unreleased bidirectional codecs and static
capability interpretation; Swift and Kotlin have no implementation yet.

## Current codec surface

| Family | TypeScript decode | TypeScript encode | Tests and v1 vectors | Equipment-side direction |
| --- | --- | --- | --- | --- |
| Measurements | All six families via normalized parsers and raw codecs | All six via raw codec | Original vectors plus 26 raw cases / 47 assertions | Implemented, unreleased addition |
| Statuses | Training and Machine Status, normalized and raw | Both raw codecs | Original vectors plus 38 raw cases / 63 assertions | Implemented, unreleased addition |
| Features | Normalized and raw words | Raw words | Original 35 vectors plus raw value corpus | Implemented, unreleased addition |
| C Features | Raw machine/target words | Raw machine/target words | Original 35 vectors plus bidirectional value corpus | Implemented |
| Supported ranges | All five, normalized and raw | All five, raw | Original 7 vectors plus raw value corpus | Implemented, unreleased addition |
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
that all test cases are shared vectors. The current full TypeScript run has 350
tests, including package-specific tests and the v1 comparator boundary tests.

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

The separate capability runner executes 49 shared cases with complete exact
reports: discovery 12, duplicates 3, features 5, forward-compatibility 2,
measurements 7, operations 4, properties 8, ranges 8. All cases pass in the current
host run, with zero unsupported/skipped cases **in that corpus only**. Fourteen
adapter/schema/template tests check wrong outputs, malformed fixtures and failure
accounting. Native tests separately isolate all 17 target bits, every range
relationship, base procedures, all read reasons and argument/capacity atomicity.
Those test-suite counts are not additional shared vectors or device evidence.

## Evidence and future gates

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
