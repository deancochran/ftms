# FTMS for Go

Pure Go codecs for Bluetooth Fitness Machine Service bytes. Module:
`github.com/deancochran/ftms/packages/go`, package name: `ftms`, minimum Go: 1.24.
No runtime dependencies beyond the standard library. No BLE, cgo, timers,
logging, background goroutines, or control authority.

Integrate through the [consumer adapter seam](https://github.com/deancochran/ftms/blob/main/docs/architecture.md#consumer-adapter-seam):
transport conversion, BLE/session lifecycle, retries, subscriptions,
UI/application policy and control safety remain outside this protocol package.

**Version 0.1.0: raw codecs and static capability interpretation.**
The pre-1.0 interface may change in minor releases. See
[coverage](docs/coverage.md), [verification](docs/verification.md), and
[release gates](docs/releasing.md). Publication evidence is recorded in the
[canonical release matrix](https://github.com/deancochran/ftms/blob/main/docs/released-packages.md).

Select the latest release for your application, then retain `go.mod` and `go.sum`:

```sh
go get github.com/deancochran/ftms/packages/go@latest
```

To reproduce the recorded release specifically, use
`go get github.com/deancochran/ftms/packages/go@v0.1.0`. Existing constraints may
affect resolution; inspect the selected version before adopting changes.

## Implemented

- Bidirectional Feature values, all five Supported Ranges, and all six measurement families.
- All 21 Control Point requests and Control Point responses, in both directions.
- Machine Status and Training Status, in both directions.
- Range inspection and normalized range values.
- Explicit malformed-input, unavailable-field, and unknown-bit evidence.
- Static capability interpretation of caller-owned discovery snapshots, including
  full Bluetooth-base UUID matching, C.7 evidence, ranges, diagnostics, and all
  21 Control Point operation prerequisites. It never performs I/O or says that a
  caller is authorized to execute an operation.

Normalized measurement views, record planning, and record assembly remain
pending. More Data is preserved, not assembled.

## Example

```go
import ftms "github.com/deancochran/ftms/packages/go"

reading, err := ftms.DecodeMeasurement(
    ftms.IndoorBike,
    []byte{0, 0, 0x10, 0x0e},
    ftms.MeasurementOptions{},
)
// Handle err and reading.Diagnostics before using values.
// reading.Values[ftms.Speed] is 3600 raw hundredths of km/h.
_ = err
_ = reading
```

See `example_test.go` for an executable example. The byte slice is synthetic,
not a physical-device capture.

## Static capability evidence

`InterpretCapabilities(snapshot, options)` evaluates caller-supplied observations
without discovering characteristics or reading a device. It preserves missing,
failed, malformed, duplicate, and contradictory evidence separately. Its complete
reports pass all **63 canonical capability cases**, including C.7 property rules.

See the [capability guide](docs/capabilities.md) and the executable
`ExampleInterpretCapabilities` for snapshot construction and interpretation.
`PrerequisiteSatisfied` is a static protocol result, **not permission to execute**.

## Raw values and errors

`Measurement.Values` is indexed by typed `MeasurementField` constants. Map
membership means a complete available field was decoded; a true entry in
`Unavailable` means a complete defined sentinel was observed. Neither means
physical zero. Absence from both maps means absent or incomplete bytes, resolved
using flags and diagnostics. `BytesRead` ends after the last complete field.

Raw values use wire units: speed is hundredths of km/h; cadence and stroke rate
are half-units per minute; signedness and scaling otherwise depend on the
characteristic and explicit format. No automatic clamping or quantization occurs.
Control request operands are ordered raw integers in the specification's wire
order, not normalized physical values. Request opcodes are `0x00` through `0x14`.

Measurement decoders return errors for invalid arguments or missing flag words,
but preserve partial measurements with diagnostics for truncated payload fields.
Status decoders return diagnostic values for malformed input. Feature, range,
and request decoders return `ErrLength`, `ErrKind`, or `ErrRange` as applicable.
Control response decoding can explicitly retain unexpected trailing-parameter
diagnostics. Do not treat a nil error alone as proof that a record is canonical.

Training text is a Go string that retains original bytes even if invalid UTF-8;
check its diagnostics before displaying it. Such evidence cannot be encoded as
a canonical Training Status. Decoders do not mutate or retain caller byte slices.
Returned maps and slices belong to the caller; concurrent mutation requires
caller synchronization.

## Format selections are independent

| Domain | Zero-value options | Explicit alternative |
| --- | --- | --- |
| Resistance range | Three-byte `ResistanceUint8Whole` | `ResistanceSint16Tenths` |
| Control resistance | Corrected `ControlResistanceSigned16Tenths` | `ControlResistanceUint8Tenths` |
| Raw resistance measurement | Legacy `MeasurementResistanceUint8` | `MeasurementResistanceSigned16Tenths` |
| Treadmill pace | 16-bit | `TreadmillPaceUint8: true` |

The raw measurement default follows the existing raw corpus. Select the signed
measurement format explicitly when that is the caller's intended wire profile.
No format is inferred from bytes, range values, device names, or capability flags.
Decoded range/measurement values retain format provenance; their encoders require
the same selection. Alternative range candidates do not establish intended
format, units, or permission to control equipment.

## Contributor verification

From this directory, ordinary package checks require only Go:

```sh
go vet ./...
go test -race ./...
go build ./...
```

Full checkout verification additionally requires Python with the pinned
contributor-only validator (`scripts/requirements.txt`):

```sh
bash scripts/verify.sh
```

It validates canonical schemas and capability template expansions, executes
shared fixtures directly (including all 63 capability reports), runs the
structural matrix, and installs a module zip into an isolated consumer without
`replace`, a workspace, or sibling fixtures. Consumers do not need Python.

The conformance build tag is checkout-only and fails when canonical assets are
missing. Ordinary installed-module tests do not depend on `shared/`.

Discovery, subscriptions, control ownership, procedure timing, bonding, and
physical safety remain the application's responsibility. A valid encoded request
does not authorize its transmission.
