# FTMS package support profiles

Status: current package-coverage taxonomy. These profiles describe protocol
directions, not Bluetooth transport, device compatibility, execution permission,
or a requirement that language packages expose identical interfaces.

## Why profiles are role-based

Encoding and decoding direction depends on the FTMS role and message family, not
on the implementation language:

| Protocol family | Client application | Equipment/server |
| --- | --- | --- |
| Features, Supported Ranges, measurements and statuses | Decode | Encode |
| Control Point requests | Encode | Decode |
| Control Point responses | Decode | Encode |

A telemetry-only client can therefore be decode-only. A client that controls a
machine is not decode-only: it encodes requests and decodes responses. Equipment
uses the complementary directions.

## Named wire profiles

### `TelemetryClient`

- Decode Fitness Machine Feature and all five Supported Ranges.
- Decode all six FTMS machine-data families.
- Decode Training Status and Fitness Machine Status.
- Preserve defined unavailable values and malformed, truncated, trailing and
  unknown evidence according to the implemented shared contracts.

This profile performs no Control Point procedure. It is suitable for passive
monitoring and recording applications.

### `ControllerClient`

`ControllerClient` includes `TelemetryClient` and additionally:

- encodes all 21 FTMS 1.0 Control Point request opcodes; and
- decodes Control Point responses, including retained unknown/malformed evidence
  where the package exposes a raw decoder.

Encoding bytes is not permission to transmit them. Discovery, security,
indication subscription, control ownership, serialization, timeouts, supported
ranges, user confirmation and physical safety remain caller responsibilities.

### `EquipmentServer`

- Encode Fitness Machine Feature and all five Supported Ranges.
- Encode all six FTMS machine-data families.
- Encode Training Status and Fitness Machine Status.
- Decode all 21 Control Point request opcodes.
- Encode canonical Control Point responses.

This profile does not register a GATT service, schedule notifications, own an
actuator, or implement equipment safety policy.

### `FullWire`

`FullWire` is the union of `ControllerClient` and `EquipmentServer`. It is useful to
gateways, virtual equipment, simulators, replay tools and conformance tooling. It
does not imply that a package contains every convenience interface implemented in
another language.

## Orthogonal modules

These modules are reported separately from wire direction:

| Module | Meaning |
| --- | --- |
| `CapabilityEvidence` | Pure interpretation of caller-provided GATT discovery/read evidence; never current execution authority |
| `RangeInspection` | Reports the selected range layout and bounded structural candidates without choosing a format from bytes |
| `RecordPlanning` | Splits one complete measurement into valid FTMS More Data packets for a caller-supplied value budget |
| `RecordAssembly` | Combines caller-delivered fragments under explicit generation/expiry policy; does not own subscriptions or timers |
| `NormalizedViews` | Language-specific physical-unit or convenience projections in addition to raw wire values |

Orthogonal modules need not be copied into every package. In particular, C's
bounded planning and assembly interfaces are not missing wire directions in the
other ports.

## Current package claims

Claims below identify current released package versions and the implemented Rust
source candidate, not every historical branch or future version. The authoritative
artifact identities and publication boundaries are in
[released packages](released-packages.md).

| Package | Wire profile | Orthogonal modules | Current distribution state |
| --- | --- | --- | --- |
| TypeScript `@deancochran/ftms` 0.4.0 | `FullWire` | `CapabilityEvidence`, `RangeInspection`, `NormalizedViews` | Published on npm |
| C `ftms` 0.2.0 | `FullWire` | `CapabilityEvidence`, `RangeInspection`, `RecordPlanning`, `RecordAssembly` | Published GitHub source archive |
| Swift `FTMS` 0.1.0 | `FullWire` | `CapabilityEvidence`, `RangeInspection`, `NormalizedViews` | Published Git/SwiftPM release; revision pin required |
| Kotlin/JVM `io.github.deancochran:ftms` 0.1.0 | `FullWire` | `CapabilityEvidence`, `RangeInspection` | Published on Maven Central |
| Python `deancochran-ftms` 0.1.0a1 | `FullWire` raw codecs | `RangeInspection` and selected `NormalizedViews`; no `CapabilityEvidence` | Published PyPI alpha |
| Rust `ftms` 0.1.0 source candidate | `FullWire` raw codecs | `RangeInspection`; no `CapabilityEvidence`, `RecordPlanning` or `RecordAssembly` | Implemented and verified in source; not tagged or published on crates.io |

C# development now has an explicitly approved `FullWire` parity objective with
`CapabilityEvidence`, `RangeInspection` and normalized views. This supersedes the
earlier client-first recommendation for this port, not the requirement for
complete directional evidence. Its package-owned coverage record distinguishes
that objective from verified behavior; there is no NuGet publication claim.
`RecordPlanning` and `RecordAssembly` remain outside its initial scope.

Other future ports should select the smallest profile justified by a consumer;
they need not implement `EquipmentServer` merely for parity. C is the primary
lane for future embedded equipment/server runtime validation because it already
has bounded planning and assembly interfaces.

## Claim and verification rules

- A profile claim requires every direction listed by that profile; partial
  implementations must list individual supported directions instead.
- Shared wire meanings, widths, units, sentinels, diagnostics and explicit format
  selections remain consistent wherever an operation is implemented.
- Public interfaces should be idiomatic for their language. Object shapes,
  allocation policy, error types and convenience modules need not match.
- Runners enumerate all canonical cases they discover and report pass, fail,
  unsupported and skipped outcomes. Unsupported work must not disappear or be
  described as complete conformance.
- Directional corpora distinguish canonical encode/decode assertions from
  intentionally decode-only malformed evidence. Case totals and directional
  assertion totals are separate.
- Passing host fixtures is protocol regression evidence, not BLE qualification,
  runtime lifecycle evidence or compatibility with every machine.

The existing immutable codec-v1 identity is unchanged by this taxonomy. Future
machine-readable profile accounting must be additive and consumed by real package
runners rather than added as unused placeholder infrastructure.
