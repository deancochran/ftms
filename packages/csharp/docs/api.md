# C# interface and units

Namespace: `DeanCochran.Ftms`. One pure managed library; no runtime dependencies.

| Module | Interface |
| --- | --- |
| Feature | `FeatureCodec.Decode`, `TryDecode`, `Encode`, `TryEncode`; two raw `uint` words and unknown masks |
| Ranges | `RangeCodec.Decode`, `TryDecode`, `Encode`, `TryEncode`, `Inspect`; exact min/max/increment, unit and scale |
| Controls | `ControlCodec.DecodeRequest`, `TryDecodeRequest`, `EncodeRequest`, `TryEncodeRequest`; equivalent response methods |
| Measurements | `MeasurementCodec.Decode`, `TryDecode`, `Encode`, `TryEncode`; six kinds, immutable raw fields, diagnostics and normalized projections |
| Status | `StatusCodec.DecodeTraining`, `EncodeTraining`, `TryEncodeTraining`, and corresponding Machine methods |
| Capabilities | `CapabilityEvaluator.Evaluate(snapshot)`; immutable evidence and static reports, not control permission |

## Errors and ownership

Strict decoders reject unusable input with `FtmsException.Error` (`Length`, `Kind`,
`Range`). `TryDecode` variants return `DecodeResult<T>` for these expected failures.
Measurement/status decoders retain partial or unknown evidence where their
contracts permit it. A successful `TryDecode` means a result exists, not that its
diagnostics are empty. Programmer errors such as null arguments remain exceptions.

Encoders reject invalid widths, unsupported sentinels, inconsistent fields and
noncanonical diagnosed values. `TryEncode` returns false with `written == 0` for
insufficient destination capacity; invalid models still throw `FtmsException`.
Neither path modifies the destination on failure. These methods currently use
an internal temporary array; no allocation-free claim is made.

Inputs retained by models and byte arrays returned from evidence are copied.
Read-only collection wrappers reject mutation. Codecs have no mutable global state.

## Wire values versus projections

Raw integer values always retain FTMS widths and resolutions. The 30-field
`MeasurementField` enum follows the shared raw-field contract. `Measurement.Fields`
distinguishes absence from unavailable (`null`). `Normalized` exposes named unit
properties without changing raw evidence:

- Speed: raw hundredths of km/h → metres per second (`raw / 360`).
- Inclination/ramp angle: tenths of percent/degrees.
- Treadmill elevation: tenths of metres; other elevation fields use metres.
- Cross-trainer stride count: tenths of a stride.
- Stroke rate and cadence: half-units per minute.
- Metabolic equivalent: tenths.
- Standard pace: seconds per 500 metres; selected `UInt8Legacy` treadmill pace
  retains its raw integer but has no asserted physical unit and normalizes to
  `null` (corrected in 0.1.0-alpha.2). Energy: kilocalories; time: seconds; power: watts.

Control operands are ordered raw integers, **not** these floating-point projections.
For example, `new ControlRequest(ControlOpcode.TargetPower, 250)` is 250 W, while
target speed uses hundredths of km/h. Signed and unsigned widths are enforced by
the opcode. Encoding any request is not authorization to transmit it.

`MeasurementFormat` selects resistance byte/whole versus signed-16/tenths and
treadmill unsigned-16 versus legacy byte pace independently. `RangeCodec` has its
own resistance selection. Control request resistance defaults to signed-16 tenths;
its optional byte profile is independently selected. Machine Status resistance
remains signed-16 tenths regardless of the Control Point selection.

## Capability evidence

Use the named discovery/scope/read enums with `CapabilitySnapshot` and
`CapabilityCharacteristic`; the numeric overloads preserve shared-contract codes.
UUID strings are canonical 32-character lowercase hex (for example,
`00002acc00001000800000805f9b34fb`), not BLE byte-order encodings.

`CapabilityC7` carries nullable bonding and Feature-lifetime-change facts. Omitted
facts remain unknown, not false. The report retains raw Feature words, unknown
bits, observation bytes, input indices and caller generation. `PresenceOf` selects
a characteristic by kind. Range and operation reports expose named evidence states;
the numeric diagnostic/known-kind fields follow the shared capability contract.

`DeclaredSupport`, `StaticPrerequisites` and `ReasonFlags` describe static evidence.
Even `CapabilityPrerequisites.Satisfied` does not establish security, subscriptions,
current ownership, user intent, safe ranges for a particular activity, or execution
permission. Applications own all of those policies.
