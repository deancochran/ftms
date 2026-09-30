# FTMS for Dart

Pure Dart codecs for the Bluetooth **Fitness Machine Service**, usable from
Flutter and standalone Dart. No Flutter, BLE, FFI, platform-channel or runtime
package dependencies. Requires Dart 3.11 or newer, below Dart 4.

**Status: 0.1.0 published on pub.dev.** See the repository's
[release matrix](https://github.com/deancochran/ftms/blob/main/docs/released-packages.md)
for published identities.

## Install

Use the published package from Dart or Flutter:

```sh
dart pub add deancochran_ftms
# Or: flutter pub add deancochran_ftms
```

For an exact release pin:

```yaml
dependencies:
  deancochran_ftms: 0.1.0
```

For development against a source checkout, use a local path dependency:

```yaml
dependencies:
  deancochran_ftms:
    path: /path/to/ftms/packages/dart
```

```dart
import 'dart:typed_data';
import 'package:deancochran_ftms/deancochran_ftms.dart';

final raw = decodeMeasurement(
  MeasurementKind.indoorBike,
  Uint8List.fromList([0x44, 0, 0x10, 0x0e, 0xb4, 0, 0xfa, 0]),
);
final metrics = normalizeMeasurement(raw);
// metrics.speedMps == 10, cadenceRpm == 90, powerWatts == 250.
// raw still retains flags, integer wire values and diagnostics.
```

The bytes are synthetic, not an equipment capture. Run the complete example with
`dart run example/main.dart`. The example checks results even when Dart assertions
are disabled. Branch source can differ from the published package; the release
matrix records the verified public archive and consumer identity.

## Scope and interface

- Bidirectional Feature, all five Supported Ranges, all six measurement families,
  Training Status, Machine Status, all 21 Control Point request opcodes, and
  canonical Control Point responses (`FullWire`).
- `evaluateCapabilities` interprets typed caller-provided discovery/read evidence
  including duplicates, contradictions, missing evidence and C.7 conditions.
- `inspectSupportedRange` reports the selected layout and bounded candidates,
  without guessing the format from bytes.
- `normalizeMeasurement` exposes physical units while preserving the raw record.

Use the main import above; `lib/src/` is implementation detail. Models are
immutable. Decoders do not mutate input bytes, retained arrays are owned copies,
and encoders return fresh `Uint8List` values. Raw integer values are not rounded
or clamped. Public result `toJson()` methods expose documented shared comparison
representations; JSON is not required to use the typed interface.

### Raw values, formats and diagnostics

`MeasurementRaw.values` has 30 slots indexed by `MeasurementField`; presence and
unavailable masks distinguish absent values, sentinels and actual zero. Do not
interpret absent/unavailable slot zeros as physical measurements.

Measurement payload truncation, trailing bytes, More Data and RFU flags remain
explicit evidence. Missing flag words throw `MeasurementCodecException` with a
stable code; malformed Control Point requests/responses use
`ControlCodecException`. Feature/range length and range errors use
`ArgumentError`/`RangeError`. Encoders reject non-canonical evidence and invalid
raw widths. See [coverage](doc/coverage.md) for the intentional error-model limits.

Format choices are explicit and independent:

- Range resistance: `ResistanceRangeFormat`.
- Control-request resistance: `ResistanceControlFormat` (signed 16-bit tenths by default).
- Measurement resistance and treadmill pace: `MeasurementFormatOptions`.
- Capability range interpretation: `CapabilityResistanceRangeFormat`.

Use the same measurement options for decode, normalization and encode. Legacy
treadmill pace has no asserted physical unit and therefore normalizes to null.
Machine Status resistance always retains its signed 16-bit tenths layout.

## What remains in your application

Bluetooth discovery, permissions, connections, CCCD subscriptions, encryption,
control ownership, procedure serialization, timing, reconnection, user consent
and physical safety. A supported feature or encodable command **does not grant
permission to transmit or move equipment**. There is no `canExecute` result.

C-style packet planning and fragment assembly are not included. This package is
not a complete trainer controller and does not claim Bluetooth qualification or
universal equipment compatibility.

## Develop and verify

From this directory inside the repository:

```sh
python3 -m pip install -r tool/requirements.txt
python3 tool/verify.py --package
# With Chrome installed (CHROME_EXECUTABLE can select another Chromium binary):
python3 tool/verify.py --platform chrome --compiler dart2js
python3 tool/verify.py --platform chrome --compiler dart2wasm
```

`DART` can select an exact SDK executable. Python/jsonschema are development-only
schema/provenance tools; consumers need only Dart. The verification gate reads
the canonical repository `shared/` corpora. No fixture copies are maintained here.
Browser fixture data is generated, hash-identified, ignored, and never published.

Repository tests are deliberately excluded from the distribution because they
require the shared corpus. Installation checks instead extract the exact source
archive into an isolated consumer and execute the public examples.

See [verification](doc/verification.md), [Flutter integration](doc/flutter_integration.md),
and [release procedure](RELEASING.md). Host tests, compilation, real devices and
Bluetooth qualification are different evidence streams.
