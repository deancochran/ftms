# Dart coverage

The Dart implementation targets `FullWire`, `CapabilityEvidence`, `RangeInspection`
and measurement `NormalizedViews`. Claims refer to executed evidence in
`build/<platform>/verification.json`, not just the package version.
See the [release matrix](../../../docs/released-packages.md#published-native-universal-measurements)
for verified publication and the [verification record](verification.md) for
historical local checks and their limitations.

| Family | Decode | Encode |
| --- | --- | --- |
| Feature (two uint32 words) | Yes | Yes |
| Speed, inclination, resistance, heart-rate and power ranges | Yes | Yes |
| Treadmill, cross trainer, step climber, stair climber, rower, indoor bike | Yes | Yes |
| Training Status and defined Machine Status opcodes | Yes | Yes |
| All 21 Control Point request opcodes | Yes | Yes |
| Control Point responses | Raw diagnostic evidence | Canonical values only |

The raw measurement slot order is `MeasurementField`. Integer widths, signedness,
units and sentinel behavior follow the shared contracts. Normalized views expose
m/s, metres, percent, degrees, seconds/500 m where defined, kcal, kcal/hour,
kcal/minute, bpm, MET, seconds, newtons, watts, steps/minute, counts and rpm.
Signed compatibility resistance uses tenths; canonical uint8 resistance is whole
levels. Cross-trainer strides are tenths. Undefined legacy treadmill pace remains
raw, not guessed physical units.

Typed enum parameters make unsupported measurement kinds unrepresentable at the
ordinary Dart call site. The adapter accounts for the shared invalid-kind fixture
separately; it does not invent a seventh public enum value. Malformed payloads
that cannot hold the required flag/header structure throw documented codec
errors. Partial measurement groups remain diagnostics; they are not repaired.

Capability evaluation is static, including independent discovery/service scope,
full Bluetooth UUID matching, duplicate ambiguity, C.7 three-valued evidence,
read failures, malformed Feature/ranges, target declarations and prerequisites.
Known kinds, operations and diagnostics retain canonical ordered reporting.

No record planner, fragment assembler, BLE integration, simulator/session policy,
physical controller, private capture, or Bluetooth qualification is included.
