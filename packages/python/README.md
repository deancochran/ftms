# deancochran-ftms

`deancochran-ftms` is a pure, synchronous Python protocol package.  This
**0.1.0a2 is an alpha with an evolving API**: it implements FTMS Features, all five supported ranges (raw and normalized), structural range inspection, raw Control Point requests/responses, all six raw measurement families, bidirectional Machine/Training Status, and static capability evaluation. The earlier 0.1.0a1 artifact has no capability API. It has no BLE, lifecycle, or logging APIs and is not a complete port of every API in the TypeScript/C packages.

Its wire [support profile](../../docs/support-profiles.md) is `FullWire` raw codecs,
with `RangeInspection`, selected `NormalizedViews`, and `CapabilityEvidence`.
`FullWire` does not mean cross-language convenience parity.

## Static capability evidence

`evaluate_capabilities(snapshot, options=None)` is a pure interpretation of one immutable,
caller-owned `CapabilitySnapshot`. It accepts ordered immutable
`CharacteristicEvidence` observations and returns an immutable `CapabilityReport`.
The report preserves discovery/scope uncertainty, duplicates, raw feature words,
unknown bits, range evidence, all 21 operation prerequisites, and diagnostics.
`report.to_wire()` produces fresh JSON-compatible containers in the exact shared
capability-corpus representation. It deliberately has no `canExecute` field: BLE
I/O, encryption, indication setup, control ownership, retries, and safety approval
remain outside this package. The evaluator supports explicit C.7 `C7Evidence`;
unknown is not false.

As with standalone range decoding, pass
`RangeFormatOptions(resistance_format="signed16Tenths")` to explicitly select the
six-byte resistance range alternative. The default is three unsigned whole-level
bytes; this selection affects only the resistance range and is never inferred
from observed bytes or Feature bits.

This API requires 0.1.0a2 or newer. Until that version is available on PyPI,
install from the source checkout (`python -m pip install ./packages/python`
from the repository root). Publication evidence is tracked separately in the
[release matrix](../../docs/released-packages.md).

```python
from deancochran_ftms import (
    CapabilitySnapshot,
    CharacteristicEvidence,
    DiscoveryState,
    ReadState,
    ServiceScope,
    evaluate_capabilities,
)

# The application supplies discovery/read evidence; this does not use Bluetooth.
feature = CharacteristicEvidence(
    uuid="00002acc00001000800000805f9b34fb",
    properties=0x02,  # Read
    read_state=ReadState.SUCCESS,
    read_bytes=bytes(8),  # Valid all-zero feature words, not a missing read.
)
report = evaluate_capabilities(
    CapabilitySnapshot(
        discovery=DiscoveryState.COMPLETE,
        scope=ServiceScope.PRESENT,
        generation=1,
        characteristics=(feature,),
    )
)
assert report.observation_count == 1
assert len(report.operations) == 21
assert "canExecute" not in report.to_wire()
```

UUIDs use 32 lowercase hexadecimal characters without hyphens. Read payloads
must be immutable `bytes`, observations must be a tuple, and state fields use the
exported enums. Positional report rows follow the
[shared capability report layout](../../shared/conformance/capabilities/README.md).
Missing Control Point/Machine Status evidence and unknown C.7 facts in this
example are retained as diagnostics, not silently treated as satisfied.

## Install and compatibility

The distribution name is `deancochran-ftms`; import `deancochran_ftms`. It has
no runtime dependencies and declares Python >=3.11. Python 3.11 and 3.14 are
tested by the package verification commands in this milestone.

After publication, install this explicitly selected prerelease from PyPI:

```sh
python -m pip install 'deancochran-ftms==0.1.0a2'
```

```python
from deancochran_ftms import decode_features, encode_features_raw, FeaturesRaw

wire = encode_features_raw(FeaturesRaw(machine=0, target=1 << 3))
result = decode_features(wire)
assert result.ok and result.value is not None
assert result.value.power_target_setting_supported
```

`decode_features_raw()` and `encode_features_raw()` are strict wire codecs and
raise `RawCodecError` for wrong byte inputs, non-8-byte payloads, or invalid raw
words. `decode_features()` instead returns an immutable `FeatureDecodeResult`:
wrong lengths produce a `FeatureDiagnostic` with `code="length"`. Feature
payloads are exactly eight bytes; trailing bytes are rejected, matching the
canonical TypeScript Feature behavior. `bytes`, `bytearray`, and contiguous
one-dimensional byte `memoryview` inputs are accepted and copied as immutable
evidence. Raw words retain all unknown/reserved bits. Integer raw words must be
plain `int` values from 0 through 2^32-1; `bool` is rejected.

The normalized `Features` model exposes the canonical v1 feature names in
snake_case. Its three convenience properties (`supports_erg`, `supports_sim`,
and `supports_resistance`) correspond to the v1 compatibility names.

## Ranges and inspection

`decode_supported_range_raw(data, kind, options=None)` and
`encode_supported_range_raw(value, options=None)` operate on `SupportedRangeRaw`.
Kinds are `speed`, `inclination`, `resistance`, `heartRate`, and `power`.
Values retain integer numerators, `scale_divisor`, and units; the normalized
`decode_supported_range()` divides these values into physical units. All three
raise `RawCodecError` for invalid arguments, lengths, or range values.

Resistance ranges default to three unsigned whole-level bytes. Select the
six-byte signed-tenths alternative explicitly with
`RangeFormatOptions(resistance_format="signed16Tenths")`; this option is invalid
for other range kinds. Range units do not imply resistance percentages.

`inspect_supported_range_raw()` returns the shared inspection report shape:
selected profile, actual/expected lengths, status, selected value, and ordered
structural candidates. Malformed wire lengths/values appear as candidate statuses;
invalid caller kinds/options still raise. Report values use the canonical numeric
unit identifiers (0 speed, 1 inclination, 2 resistance, 3 heart rate, 4 power).
The returned dictionary is caller-owned; selected and candidate values do not
alias. A valid alternative candidate never selects a profile automatically or
establishes physical units on a particular machine.

## Control Point requests and responses

```python
from deancochran_ftms import (
    ControlRequestRaw,
    decode_control_request_raw,
    encode_control_request_raw,
    decode_control_response_raw,
)

# Set Target Power: opcode 0x05, raw operand in watts. This does not send anything.
wire = encode_control_request_raw(ControlRequestRaw(0x05, (75,)))
assert wire == bytes.fromhex("05 4b 00")
assert decode_control_request_raw(wire).operands == (75,)
response = decode_control_response_raw(bytes.fromhex("80 05 01"))
assert response.request_opcode == 5 and response.result_code == 1
```

All 21 request opcodes support raw encode/decode. Operands must be tuples of plain
integers in wire units, not arbitrary human-unit floats. For example simulation
operands are wind speed in thousandths of m/s, grade in hundredths of percent,
rolling coefficient in ten-thousandths, and wind coefficient in hundredths kg/m.
There is no public normalized control encoder in this milestone; the legacy
codec-v1 test adapter translates its normalized fixtures to raw operands.

`ControlFormatOptions(resistance_format="uint8Tenths")` explicitly selects the
alternative resistance command width; the default is `signed16Tenths`. Control
options are independent of range options and do not change other opcodes.

`ControlResponseRaw` preserves request/result codes plus integer diagnostic flags
`unknown_request`, `unknown_result`, and `unexpected_parameters`. Its `parameter`
is 0 for none or 1 for successful spin-down speeds (`low`/`high` in hundredths
km/h). `encode_control_response_raw()` accepts only canonical response forms;
decodable malformed/unknown evidence is not necessarily encodable. Invalid wire
headers/lengths and invalid encoder arguments raise `RawCodecError`.

No codec acquires control, sends bytes, retries commands, or authorizes execution.

## Development verification

From `packages/python/` in a full repository checkout (with `uv` installed):

```sh
uv run --locked --group dev python scripts/verify.py
```

That aggregate command runs both supported test interpreters, quality checks,
all codec corpus runners, the structural matrix, and isolated installation.
Individual checks are also available:

```sh
uv run --locked --group dev pytest
uv run --locked --group dev ruff format --check .
uv run --locked --group dev ruff check .
uv run --locked --group dev mypy src tests scripts
uv run --locked --group dev python scripts/run_features_conformance.py
uv run --locked --group dev python scripts/run_measurement_status_conformance.py
uv run --locked --group dev python scripts/run_measurement_matrix.py
uv run --locked --group dev python scripts/run_capability_conformance.py
uv run --locked --group dev python scripts/verify_package.py
```

The conformance test reads `../../shared/conformance/v1` and
`../../shared/conformance/values/v1` directly; it never copies fixtures.
It executes all codec-v1 categories and the additive values, controls,
inspection, compatibility, measurements and statuses contracts directly from
shared fixtures. The capability runner validates the separate canonical schema and
executes all 63 exact reports directly from `../../shared/conformance/capabilities/v1`.
`scripts/verify_package.py` builds both artifacts, rebuilds from
an extracted sdist outside this checkout, installs the wheel non-editably into
a fresh environment, and writes its distinct machine-readable artifact hashes,
interpreter, and per-step install/rebuild evidence to ignored
`build/package-verification-report.json`. Conformance identity and case evidence
are separately recorded in `build/verification-report.json` and
`build/measurement-status-verification-report.json`. The structural matrix
records 181,760 layouts in both directions, 46 sentinel cases, 47 RFU cases,
and 315 incomplete prefixes in `build/measurement-matrix-verification-report.json`.
These generated cases are not separate pytest test registrations. The sdist
intentionally contains no shared corpus dependency: installing or building the
package needs no checkout, but running the conformance suite does. The package
check asserts that rebuilding the extracted sdist produces an identical wheel;
it does not assert byte-for-byte reproducibility of the sdist archive itself.

This is host protocol regression evidence only, not live control execution, device
interoperability or Bluetooth qualification. Public availability is separate
from these host verification results.

## Coverage and limits

Version `0.1.0a2` is an **alpha with language-specific API coverage**. Features, ranges, controls,
all six measurement families and both status characteristics have raw codecs.
Normalized measurement/status projections and normalized range decoding are
available. Static capability evaluation is included starting with 0.1.0a2.
Range, control and
measurement format choices are independent and explicit; no API infers them
from packet length, feature declarations or BLE state. Host fixtures establish
codec regression evidence, not live-device compatibility or qualification.

## Measurements and statuses

`MeasurementRaw` is immutable raw evidence: `flags`, 30 wire-unit `values`, and
`present`/`unavailable` bit masks retain field-level availability. Use
`decode_measurement_raw(data, kind, options=None)` and
`encode_measurement_raw(value, options=None)`. Kinds are 0 Treadmill, 1 Cross
Trainer, 2 Step Climber, 3 Stair Climber, 4 Rower, and 5 Indoor Bike. Decoders
retain More Data, Cross Trainer backward direction, RFU, truncation, and trailing
byte diagnostics. Encoders validate the wire flags, presence/unavailable masks
and selected values; auxiliary decode diagnostics do not themselves authorize
or prevent encoding, matching the shared raw contract. Compatibility formats
are explicit only: `MeasurementFormatOptions(resistance_format="signed16Tenths")`
and `treadmill_pace_format="uint8Legacy"`; they are independent selections and
are never inferred from packet length, features, or machine identity.

```python
from deancochran_ftms import MeasurementRaw, decode_measurement_raw, encode_measurement_raw

raw = MeasurementRaw(5, 0, 1, 0, (1234,) + (0,) * 29)  # speed: 12.34 km/h
assert encode_measurement_raw(raw) == bytes.fromhex("00 00 d2 04")
assert decode_measurement_raw(bytes.fromhex("00 00 d2 04"), 5).values[0] == 1234
```

Machine Status uses `MachineStatusRaw` with raw opcode/action and optional
`(control_opcode, operands)` parameter tuple. Training Status uses
`TrainingStatusRaw`; text is UTF-8 `bytes`, so malformed UTF-8 is retained and
diagnosed by `invalid_utf8` rather than silently replaced. The corresponding
`decode_*_status_raw` APIs preserve partial/trailing/reserved evidence; encoders
accept only canonical values and raise `RawCodecError` on invalid widths, flags,
UTF-8, sentinels, or diagnostics. Raw units/scales remain FTMS wire units.

Host tests cover Python 3.11 and 3.14 plus shared literal measurement/status
corpora. This finite evidence is not BLE, real-device, PTS, or Bluetooth
qualification evidence.

`normalize_measurement(raw, options=None)` provides the immutable-raw-to-codec-v1
normalized metric projection (for example raw speed / 360 to m/s, cadence / 2,
and unavailable or incomplete fields as `None`). `normalize_machine_status()` and
`normalize_training_status()` provide the corresponding normalized status views;
raw codecs remain the source of wire evidence.
