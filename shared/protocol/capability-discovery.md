# FTMS capability discovery contract

Status: language-neutral contract. The unreleased C slice and TypeScript
`evaluateFtmsCapabilities` implement the static evidence interpretation
described here. TypeScript accepts `Uint8Array`/`ArrayBuffer` read bytes and
returns the corpus's normalized representation; neither API performs discovery
or authorizes control.

An optional caller-owned resistance-range format selection is applied consistently
to requirements and evaluation. It changes only resistance wire decoding; it does
not infer a device format or authorize an operation.

## Goal and scope

Allow clients to establish what an FTMS device declares and what the available
GATT evidence supports, without a model allowlist or an indoor-bike assumption.
"Any FTMS-compatible trainer" means a generic protocol-based interrogation
design, not a guarantee that every device is conformant, reachable, controllable,
or already tested. Incomplete or contradictory evidence must be representable.

Cover the complete FTMS 1.0 machine-data characteristic set:

| Measurement family | Characteristic UUID |
| --- | --- |
| Treadmill Data | `0x2ACD` |
| Cross Trainer Data | `0x2ACE` |
| Step Climber Data | `0x2ACF` |
| Stair Climber Data | `0x2AD0` |
| Rower Data | `0x2AD1` |
| Indoor Bike Data | `0x2AD2` |

A device can expose multiple measurement characteristics. Do not collapse them
to one inferred machine identity or treat advertising type bits as an exclusive
classification. This contract does not add Cycling Power, Cycling Speed and
Cadence, ANT+, or proprietary services to FTMS coverage.

## Caller-owned discovery

The caller discovers the Fitness Machine Service (`0x1826`), enumerates its
characteristics and properties, and reads Feature and relevant range values.
The interpreter only consumes an evidence snapshot; it performs no I/O.

Snapshots are scoped to one service instance and discovery generation. Do not
merge evidence from different devices, service instances, or stale connections.
The caller owns discovery completeness, read retries, cache invalidation on
Service Changed, and refreshing evidence after relevant lifecycle changes.

## Evidence model

The C API is unreleased. This contract preserves these distinctions:

| Evidence | Required distinctions |
| --- | --- |
| Service/characteristic discovery | Not attempted, partial, complete, or failed; retain observed UUIDs and properties |
| Characteristic presence | Unique, ambiguous (duplicates), confirmed absent after complete discovery, or unknown |
| Read result | Not attempted, succeeded with raw bytes, or failed |
| Decode result | Valid, or malformed with diagnostics; retain raw evidence |
| Feature declaration | Supported, not supported, or unknown because Feature is unavailable/invalid |
| Range | Not read, absent, read failed, malformed, or valid with min/max/increment/unit |

Read failures may include normalized reasons such as security-required or
unavailable; platform exception types must not leak into the shared core.
An unsuccessful read is not a zero-valued Feature and not evidence of unsupported
capabilities. A zero-valued valid Feature is different from a missing Feature.

Preserve both raw 32-bit Feature words, unknown/reserved bits, and unknown
characteristic UUIDs for diagnostics and future extensions. Use declared
known bits only for current semantics. The existing TypeScript decoder does
not expose all this evidence; this is an aggregate interpreter requirement, not a
description of its current return type.

## Interpretation rules

### Measurements and targets are separate

Feature (`0x2ACC`) is mandatory and readable. It contains separate measurement
feature and target-setting feature words. A measured value being supported does
not prove that the corresponding value can be controlled. Optional feature bits
are not a complete inventory of mandatory fields in every measurement layout.

Return the observed set of measurement characteristics and their properties,
alongside decoded feature declarations. Packet-level flags still determine
which optional fields are present in a particular notification; a capability
snapshot must not fabricate a missing measurement.

### Ranges constrain targets; they do not grant support

These target declarations require corresponding readable range evidence:

| Target-setting feature | Supported range characteristic |
| --- | --- |
| Speed | Supported Speed Range (`0x2AD4`) |
| Inclination | Supported Inclination Range (`0x2AD5`) |
| Resistance level | Supported Resistance Level Range (`0x2AD6`) |
| Power | Supported Power Range (`0x2AD8`) |
| Heart rate | Supported Heart Rate Range (`0x2AD7`) |

A range may be present when the corresponding target bit is not set. Its
presence alone must not promote that target to supported. Report a set target
bit with absent or malformed required range evidence as an inconsistency or
incomplete evidence, not as a safe executable control.

Preserve minimum, maximum, increment, and units. Bounds do not imply every value
is supported, and power extrema do not guarantee the machine can achieve that
power at its current speed. Other target-setting bits do not automatically need
one of these five ranges; evaluate each according to its own specification rule.

### Control availability is not current permission

Control Point (`0x2AD9`) is optional. When present, its required properties are
Write and Indicate, and Fitness Machine Status (`0x2ADA`) is required. Validate
required characteristic properties, including Read for Feature/ranges and
Notify for measurement data and Machine Status. Report missing requirements
without silently changing the advertised feature bits.

Training Status (`0x2AD3`) is optional; when present, validate both Read and
Notify. Do not confuse Training Status with Fitness Machine Status or make
Training Status a prerequisite for every device.

Represent three independent questions:

1. **Declared support:** what do valid Feature bits and observed characteristics
   say, including base Control Point procedures that have no individual target bit?
2. **Evidence completeness and consistency:** are required characteristics,
   properties, and ranges known and valid for the operation?
3. **Can this caller execute now?** This is outside the static capability result.

The caller must establish required security, configure indications, obtain
control, serialize procedures, match responses, handle timeouts/disconnects and
permission loss, and apply user confirmation and physical safety constraints.
Characteristic properties alone do not prove the connection is encrypted or
the caller holds control. Do not expose a misleading aggregate `canExecute`
boolean based only on discovery evidence.

Telemetry-only devices are valid discovery outcomes. An absent Control Point
must not prevent decoding their measurements. Conversely, a target bit alone
does not prove a functioning Control Point is available. Unknown device behavior
must not be silently repaired with a brand/model heuristic in the core.

## Result sections

- **Observed services/characteristics:** including discovery completeness and
  all supported measurement families as a set.
- **Declared features:** separate measurement and target support, with raw words
  and unknown bits retained.
- **Ranges:** independently recorded evidence with units and validation results.
- **Operation evidence:** known declarations and missing/inconsistent protocol
  prerequisites; not authorization to issue commands.
- **Diagnostics:** stable reasons tied to their evidence, such as missing
  required range, invalid properties, malformed Feature, or incomplete discovery.

This result reports protocol facts, not UI modes, inferred machine identities,
or application lifecycle state. Existing deprecated ERG/SIM aliases must not
become the canonical cross-language contract.

## Static evaluation rules

These are conservative evidence rules, not additional wire requirements or a
Bluetooth qualification test. [Capability corpus v1](../conformance/capabilities/README.md)
pins their normalized representation separately from codec corpus v1.

### Scope, presence, and reads

- The caller selects one FTMS service instance; the snapshot's service scope is
  unknown, present, absent, or ambiguous. It supplies a discovery state and an
  opaque generation number. The interpreter cannot validate device identity or
  freshness; it holds no cache and copies the generation without interpreting it.
- Observations retain every full UUID, property mask, read state/reason, read
  length, and input index. UUIDs use canonical display/network order, not BLE's
  little-endian serialized UUID order. Raw value bytes remain caller-owned, and
  output indices refer back to this snapshot. UUIDs matching the **entire**
  Bluetooth base UUID are recognized; arbitrary 128-bit UUIDs are never truncated.
- Only known characteristic kinds are constrained to one instance. Duplicates
  are ambiguous even when byte-identical; none is selected for Feature/range
  decoding. Unknown UUIDs remain opaque observations, including repeated UUIDs.
- Observed presence remains visible regardless of service scope. Unobserved known
  characteristics become absent only with complete discovery and present scope;
  otherwise they are unknown. The unknown-kind presence slot has no aggregate
  meaning and remains unknown.
- Only present scope permits Feature/range decoding or derived declarations.
  Complete discovery with absent scope and **zero** observations establishes
  not-supported operations, with not-applicable prerequisites. Absent scope with
  observations or incomplete discovery is a scope contradiction: declarations
  remain unknown and prerequisites inconsistent. Unknown/ambiguous scope leaves
  declarations unknown and prerequisites incomplete, even if observations exist.
- A successful read with zero or invalid-length bytes is malformed evidence.
  A failed read is never treated as malformed bytes or a zero Feature. The read
  reason distinguishes generic failure, security-required, unavailable, timeout,
  and disconnected; a failed read may also have no supplied reason.
- Successful, valid Feature bytes retain both raw words and unknown masks even
  if Read properties are wrong. Valid ranges likewise retain decoded values.
  Property contradictions are reported separately, rather than changing bytes or
  erasing declarations. All-zero Feature is valid, with known false target bits.

### Operation declarations and prerequisites

Reports cover wire opcodes `0x00` through `0x14`, ordered by opcode:

| Opcode | Declaration source | Additional range prerequisite |
| --- | --- | --- |
| `00`, `01`, `07`, `08` (Request Control, Reset, Start/Resume, Stop/Pause) | Unique Control Point presence; no dedicated target bit | None |
| `02` speed | Target bit 0 | Speed |
| `03` inclination | Target bit 1 | Inclination |
| `04` resistance | Target bit 2 | Resistance |
| `05` power | Target bit 3 | **Power**, not Heart Rate |
| `06` heart rate | Target bit 4 | **Heart Rate**, not Power |
| `09`–`14` (hex) | Target bits 5–16 respectively | None of the five ranges |

Wheel circumference (`12`) and spin down (`13`) are marked Optional in Table 4.15.
The result retains that distinction while using their Feature bits (14 and 15)
as declarations; it does not infer support merely from Control Point presence.

In present scope:

1. Base declarations are supported for a unique Control Point, not supported
   when it is confirmed absent, and unknown for unknown/ambiguous presence.
   Other declarations require unique, successfully decoded Feature evidence;
   set/clear bits mean supported/not supported, otherwise unknown.
2. A not-supported declaration has not-applicable prerequisites and zero reason
   flags. Other contradictory observations remain in the report and diagnostics.
3. Every applicable operation needs a unique Feature with exactly Read, a unique
   Control Point with exactly Write + Indicate, and a unique Machine Status with
   exactly Notify. A **base** procedure does not require a successful Feature
   read: its declaration is independent of Feature bits. Target procedures do.
4. Only a **known supported** target among bits 0–4 requires its corresponding
   unique, readable, successfully decoded range. Unknown declarations do not
   invent range requirements; no range is required for bits 5–16.
5. Unknown presence, unread/failed required values, and incomplete discovery
   produce unavailable/incomplete reasons. Confirmed missing prerequisites,
   duplicate prerequisites, invalid required properties, and malformed required
   values produce invalid/inconsistent reasons. **Inconsistency takes precedence**
   over incompleteness; reason flags preserve both when applicable.
6. Satisfied means every static prerequisite above is met and discovery is
   complete. Even when the observed subset is adequate, partial or failed
   discovery remains incomplete. This deliberately conservative rule never
   clears otherwise valid declarations.

Table 4.1 excludes properties not listed for known characteristics, so both
missing required properties and extra properties are diagnosed. Optional
measurement and Training Status property contradictions are global diagnostics,
not prerequisites for unrelated controls. Training Status is never substituted
for Machine Status. A target declaration without Control Point, a Control Point
without Machine Status, and a declared ranged target without its range are
diagnosed when absence is confirmed. Feature absence is always diagnosed in a
completely discovered, present service.

This is **not** a complete GATT conformance check. Descriptors/CCCDs, encryption,
control ownership, procedure responses, parameter-level validation and actuator
safety are outside the snapshot/result. There is no authorization flag.

## Acceptance scenarios

These scenarios now have executable shared fixtures plus C API boundary tests.
The [coverage matrix](../../docs/coverage.md) and port verification record distinguish
those host results from untested devices and the still-partial codec surface.

| Scenario | Required result |
| --- | --- |
| Each of the six machine-data families, separately | Discoverable without Indoor Bike Data or an assumed control mode |
| Multiple measurement families in one service | Preserve the complete observed set |
| Telemetry-only service | Measurements usable; no invented control support |
| Valid all-zero Feature | Known false optional bits, not unknown evidence or "no measurements" |
| Partial discovery, missing Feature read, or failed discovery | Unknown/incomplete, not unsupported |
| Failed read versus malformed Feature bytes | Distinct read/decode diagnostics; retain evidence |
| Measurement bit set, corresponding target bit clear | No inferred target-setting support |
| Each of five target/range pairs | Correct units, bounds, increment, and prerequisite relationship |
| Target bit set; required range absent, unread, failed, or malformed | Distinct evidence states; never silently control-ready |
| Range present; target bit clear | Range retained; no promotion to declared support |
| Target bit set; Control Point absent | Contradictory control evidence reported |
| Control Point lacks Write/Indicate, or Machine Status missing | Required properties/characteristics diagnosed |
| Feature/range lacks Read; measurement/status lacks Notify | Invalid property evidence reported |
| Optional Training Status present without Read or Notify | Invalid properties reported; its absence alone is not an error |
| Target-setting feature with no defined range characteristic | Do not invent a range requirement |
| Base Control Point procedure without a dedicated target bit | Evaluate its own protocol prerequisites |
| Unknown feature bits or characteristic UUIDs | Preserve evidence without assigning invented semantics |
| GATT evidence complete but control not acquired | No execution-permission claim |
| Service Changed or a new discovery generation | Caller replaces stale evidence; no hidden persistent cache |

## Specification basis

Use the repository's pinned specification provenance and applicable errata in
`shared/conformance/v1/vectors.json`, rather than treating one implementation as the
normative specification. Relevant FTMS 1.0 sections include the service
characteristic requirements (Table 4.1), Fitness Machine Feature, supported
ranges, and Fitness Machine Control Point procedures.

The [Bluetooth SIG FTMS page](https://www.bluetooth.com/specifications/specs/fitness-machine-service-1-0/)
provides the adopted service, test documents, and mandatory Errata Correction
23224. Shared fixtures are regression evidence, not a qualification certificate
or proof of compatibility with every machine.
