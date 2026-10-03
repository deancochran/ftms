# Universal measurement interfaces

This is the design and acceptance guide for the native-port consumer-interface
changes following TypeScript 0.6.0, published on 2026-10-03. The
[release matrix](released-packages.md) remains the authority for installed
package versions. This guide does not change corpus versions or wire contracts.

See the [local verification record](native-universal-verification.md) for the
combined-checkout compiler, corpus and installed-consumer evidence and limits.

## Native entry points in this source change

Use each package's guide for its native input/result types and error handling.
These additions do not require rewriting existing raw-codec consumers.

| Port | Consumer entry point | Named-value access |
| --- | --- | --- |
| [C](../packages/c/README.md) | UUID16 measurement view | Metric enum and fixed-point numerator/denominator with explicit value state |
| [Rust](../packages/rust/README.md) | `decode_measurement_uuid` | Existing typed `Metric` projection through the retained-format result |
| [Go](../packages/go/README.md) | `DecodeNormalizedMeasurement` | Named optional physical fields; raw evidence retained |
| [Kotlin](../packages/kotlin/README.md) | `MeasurementReader.decode` | Typed decoded/unsupported/invalid result and named optional metrics |
| [Python](../packages/python/README.md) | `decode_measurement` | Immutable typed metrics, selected format and diagnostics |
| [Swift](../packages/swift/README.md) | `decodeMeasurement(uuid:bytes:format:)` | Named optional metric access with the existing raw result |
| [Dart](../packages/dart/README.md) | `decodeFtmsMeasurement` | Existing typed normalized view and retained raw format |
| [C#](../packages/csharp/README.md) | `MeasurementUuidCodec.Decode` | Existing typed normalized view and raw diagnostics |

Supply the identity of the characteristic that produced the notification, not
a guessed machine type. A consumer supporting one known characteristic can use
that identity directly. A generic telemetry application can pass each observed
identity and handle unsupported results without maintaining a six-way switch.

## One operation, not six application parsers

An application supplies a measurement characteristic identity, native bytes and
any explicitly selected wire-format options. The package selects one of the six
FTMS machine-data layouts and exposes named physical values, raw evidence and
diagnostics. Reading common metrics must not require an equipment-specific switch,
field-slot arithmetic, sentinel interpretation or application-side scaling.

Each port keeps **one raw decoding engine** and **one physical projection** for
this path. A convenience call composes those operations; it does not decode twice
or add independent parsers for each family. Existing raw/kind-based interfaces
remain useful for equipment implementations and are preserved for compatibility.

Universal means all six specified FTMS measurement characteristics, not arbitrary
Bluetooth protocols or undocumented layouts. Unknown UUIDs, vendor UUIDs with
similar low words, and status/control characteristics must not be mistaken for
measurements. Recognition uses the full Bluetooth base identity where relevant;
ports may offer native assigned-number values or documented textual aliases.
Discovery itself remains application-owned.

| Assigned number | Measurement |
| --- | --- |
| `0x2ACD` | Treadmill |
| `0x2ACE` | Cross Trainer |
| `0x2ACF` | Step Climber |
| `0x2AD0` | Stair Climber |
| `0x2AD1` | Rower |
| `0x2AD2` | Indoor Bike |

Each assigned number expands as `0000xxxx-0000-1000-8000-00805f9b34fb`.
An assigned-number input denotes that standard expansion, not a fragment of an
arbitrary 128-bit UUID. Never extract the low word of a vendor UUID to dispatch.

## Common semantics, native interfaces

| Concern | Required behavior |
| --- | --- |
| Physical values | Named metrics with documented units and appropriate native optional/value-state types |
| Raw values | Original wire evidence remains accessible; aliases/accessors must not fabricate available values |
| Zero | A real reading, never a substitute for absence or unavailable evidence |
| Missing fields | Not selected, incomplete, unavailable and inapplicable remain distinguishable where raw evidence permits |
| Diagnostics | Preserve truncation, reserved bits, trailing bytes, More Data and direction where defined |
| Unsupported identity | Explicitly distinguish unsupported characteristics from malformed known payloads |
| Invalid input | Preserve native error conventions; recognition is not proof that a packet is valid |
| Alternate formats | Selected explicitly and retained with the decoded convenience result; normalization uses that same selection |
| Legacy treadmill pace | Retain its raw integer, but do not assert seconds per 500 metres for unresolved legacy units |
| Fragment handling | A reading is one packet; do not silently assemble fragments or manage freshness |

A complete available prefix field remains readable if a later field is
truncated. An incomplete field produces no physical value, and its leftover
bytes must not be reinterpreted as a subsequent field. With incomplete flags,
return the port's explicit length error or an explicitly truncated result with
no invented fields. Legacy pace's unknown unit can be expressed by a dedicated
value state or a null physical metric together with retained raw bytes and format;
it must not be represented as a wire-defined unavailable sentinel.

Selected layouts never fall back to another format. A packet may happen to be
valid under more than one layout: success is not evidence for format selection.
Measurement format options remain independent of range and command options.
Any existing raw re-encoding path must preserve its selected integers/layout;
Control Point human-input rounding policies do not apply to these measurements.

Kotlin/C#/Swift/Dart can use typed objects or views; Python can use typed named
results; Go can use named optional values or explicit presence results. Rust must
retain its `no_std`, allocation-free path. C must retain its fixed storage,
caller-owned memory and no-floating-point core; rational/scaled integer accessors
can provide meaningful units without imposing an allocating floating-point model.

No port is required to copy TypeScript property spelling, UUID string ownership,
or object layout. No cross-language runtime dependency or FFI is introduced.
Protocol UUID interpretation and scaling belong in the package; transport-value
conversion, UI models, connection state and execution authority remain at the
[consumer adapter seam](architecture.md#consumer-adapter-seam).

## Verification and adoption criteria

Tests belong in the owning package, not as a duplicated protocol test suite in
an adopter's integration PR. Required evidence includes:

1. All six families through the new public interface, with independent expected
   physical values and named raw-field mappings from the canonical corpora.
2. Unknown and non-measurement identities, full-UUID vendor lookalikes, and any
   advertised aliases.
3. Zero, unavailable sentinels, reserved flags, trailing bytes, direction, More
   Data, incomplete flags and partial fields. Existing strict header errors may
   remain explicit errors; they must not become fabricated zero measurements.
4. Both resistance layouts and legacy treadmill pace, including retained format
   through normalization and any supported re-encoding path.
5. Existing public-interface compatibility and package-specific typing/ABI gates.
6. Actual compiler/runtime tests and an isolated installed-package consumer that
   reads a named measurement without copying protocol tables or conversion math.

Record the exact source base, dirty/local status, corpus schema/vector/contract
hashes and complete case accounting. The [conformance contract](../shared/conformance/README.md)
defines numeric comparison and unsupported-case reporting. A partial runner is
not full conformance; TypeScript checks do not verify native compilers. Installed
local artifacts are not evidence of registry publication or live-device testing.

Keep three evidence streams separate: existing canonical corpus runners, new
package-owned universal-interface tests, and installed public-interface consumers.
The historical normalized corpus alone does not test UUID aliases, vendor
lookalikes or every format variant. C installed consumers must exercise C99 and
supported C++ headers without heap or float requirements; Rust must verify its
actual `no_std` configuration without introducing `alloc` dependencies.
