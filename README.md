# @deancochran/ftms

Runtime-neutral TypeScript codecs and state helpers for the Bluetooth Fitness
Machine Service (FTMS).

The package accepts `Uint8Array` or `ArrayBuffer` values and returns typed,
normalized data. It does not create BLE connections, own GATT subscriptions,
schedule command timeouts, log, or depend on React Native.

> **Release status:** `0.x`. The protocol codecs are comprehensively unit
> tested, but the package does not claim Bluetooth qualification, PTS
> verification, or compatibility with every fitness machine.

## Install

```sh
npm install @deancochran/ftms
# or
pnpm add @deancochran/ftms
```

The package is ESM-only. It publishes JavaScript and TypeScript declarations
from `dist/`. It is intended for Node.js 20+, modern bundlers, and modern
React Native/Metro projects.

## Parse measurements

```ts
import { parseFtmsIndoorBikeMeasurement } from "@deancochran/ftms";

const reading = parseFtmsIndoorBikeMeasurement(notificationBytes);

if (reading.diagnostics.truncated) {
  // The notification ended before every advertised field could be read.
}

console.log(reading.metrics.cadenceRpm);
console.log(reading.metrics.powerWatts);
console.log(reading.metrics.speedMps);
```

Parsers are available for:

- Treadmill Data
- Cross Trainer Data
- Step Climber Data
- Stair Climber Data
- Rower Data
- Indoor Bike Data
- Training Status
- Fitness Machine Status

Use `parseRegisteredFtmsPayload(characteristicUuid, bytes)` when dispatching by
characteristic UUID.

## Decode features and supported ranges

Feature and range decoders return explicit result unions rather than throwing
for malformed payload lengths or invalid ranges.

```ts
import { decodeFtmsFeatures, decodeSupportedPowerRange } from "@deancochran/ftms";

const features = decodeFtmsFeatures(featureBytes);
if (!features.ok) {
  throw new Error(features.error.message);
}

const powerRange = decodeSupportedPowerRange(powerRangeBytes);
if (powerRange.ok) {
  console.log(powerRange.value); // { min, max, increment, unit: "watts" }
}
```

## Encode control requests

All FTMS 1.0 Fitness Machine Control Point request opcodes are represented by
the `FtmsControlRequest` union.

```ts
import { decodeFtmsControlResponse, tryEncodeFtmsControlRequest } from "@deancochran/ftms";

const encoded = tryEncodeFtmsControlRequest({
  op: "setTargetPower",
  powerWatts: 250,
});

if (!encoded.ok) {
  throw new RangeError(encoded.error.message);
}

await writeControlPoint(encoded.value);

const response = decodeFtmsControlResponse(indicationBytes);
if (!response.ok || !response.value.success) {
  // Treat the operation as rejected or failed.
}
```

`encodeFtmsControlRequest` is the throwing convenience variant.
`tryEncodeFtmsControlRequest` is recommended at untrusted boundaries.

### Control safety and ownership

This package only encodes and decodes protocol values. Callers must:

- inspect the Feature characteristic before exposing a control;
- read and enforce the machine's supported range and increment;
- request control and wait for the matching indication;
- serialize Control Point procedures;
- handle timeouts, disconnects, and Control Permission Lost (`0xff`);
- require appropriate user confirmation for movement or resistance changes.

FTMS responses do not contain transaction identifiers. Correlating responses,
handling delayed indications, and deciding whether a connection remains safe
are transport/application responsibilities.

## Units and unavailable values

Public metric names carry normalized units where practical:

- speed: metres per second (`*Mps`)
- distance and elevation: metres (`*Meters`)
- cadence, stroke rate, and step rate: per minute (`*Rpm`/`*Spm`)
- power: watts (`*Watts`)
- heart rate: beats per minute (`*Bpm`)
- energy: kilocalories (`*Kcal`)
- duration: seconds (`*Seconds`)
- inclination and grade: percent (`*Percent`)

Wire-level unavailable sentinels become `null`. Truncation, reserved values,
unknown status opcodes, trailing bytes, reserved flags, and More Data are
reported through `ParsedFtmsPayload.diagnostics`.

The package deliberately does not reassemble notifications marked More Data;
the caller owns fragment buffering and lifecycle policy.

## Machine detection

`detectFtmsMachineType` prefers an advertised machine-data characteristic and
can use a user-confirmed type. Feature-only inference is a heuristic and should
not be treated as authoritative for safety or UI capability decisions.

## Conformance corpus

Versioned, language-neutral regression vectors and their JSON Schema are
published at:

- `@deancochran/ftms/conformance/v1`
- `@deancochran/ftms/conformance/schema`

Use the JSON loading mechanism appropriate to your runtime or tooling. The
corpus is regression evidence, not a Bluetooth qualification certificate.

## Specification basis

Characteristic layouts follow the Bluetooth SIG GATT Specification Supplement
YAML at public repository revision
`3b58acd4d2446e68f5539acac46c3b4941a34747`. The adopted FTMS v1.0 service
text supplies service semantics where GSS does not. ESR11 and its FTMS errata
override older text, including the signed 16-bit, 0.1-resolution resistance
Control Point correction.

Mandatory Errata Correction 23224 must be included in any future compliance
assessment. No Bluetooth compliance or interoperability claim is made here.

## API stability

The package follows semantic versioning. During `0.x`, protocol corrections and
API cleanup may be released as minor versions. Compatibility projections,
including `parseFtmsIndoorBikeData`, `ControlMode`, and app-facing control
presentation types, may move to a compatibility subpath before `1.0.0`.
Prefer complete `ParsedFtmsPayload` parsers for new code.

## Development

```sh
pnpm install
pnpm check-types
pnpm test
pnpm build
pnpm verify:package
```

Security reports should follow the repository's
[security policy](https://github.com/deancochran/ftms/security/policy).

## License

[MIT](./LICENSE) © Dean Cochran.
