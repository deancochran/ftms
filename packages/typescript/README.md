# @deancochran/ftms

Runtime-neutral TypeScript codecs for the Bluetooth Fitness Machine Service
(FTMS).

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

Use `parseRegisteredFtmsPayload(characteristicUuid, bytes, formatOptions)` when dispatching by
characteristic UUID. Measurement parsers accept explicit caller-owned format
options; legacy treadmill pace is retained only by raw decoding because its unit
is unknown, so normalized pace remains null.

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

## Conformance corpus

Versioned, language-neutral regression vectors and their JSON Schema are
published at:

- `@deancochran/ftms/conformance/v1`
- `@deancochran/ftms/conformance/v1/schema`
- `@deancochran/ftms/conformance/schema`

Use the JSON loading mechanism appropriate to your runtime or tooling. The
corpus is regression evidence, not a Bluetooth qualification certificate.
Its language-neutral comparison and reporting rules are in the repository's
[conformance runner contract](../../shared/conformance/README.md).

## Specification basis

Characteristic layouts follow the Bluetooth SIG GATT Specification Supplement
YAML at public repository revision
`3b58acd4d2446e68f5539acac46c3b4941a34747`. The adopted FTMS v1.0 service
text supplies service semantics where GSS does not. ESR11 and its FTMS errata
override older text, including the signed 16-bit, 0.1-resolution resistance
Control Point correction.

Mandatory Errata Correction 23224 replaces the general conformance language in
FTMS 1.0 Section 1.1: each capability, and each supported implementation option,
must be supported as specified. It does not change FTMS wire layouts. The corpus
records the correction as governing provenance, while qualification and
caller-owned GATT behavior remain outside this codec package. No Bluetooth
compliance or interoperability claim is made here.

## API stability

The package follows semantic versioning. During `0.x`, protocol corrections and
API cleanup may be released as minor versions. Compatibility projections such
as `parseFtmsIndoorBikeData` remain available. Application policy, transport
lifecycle, machine inference, and presentation contracts intentionally remain
outside this package. Prefer complete `ParsedFtmsPayload` parsers for new code.

## Bidirectional protocol APIs (unreleased source additions)

The working source now matches the C port's protocol directions. Existing
normalized parsers, human-unit control encoders and validated response decoder
remain compatible. Additive raw APIs are exported from the package root:

- `decodeFtmsFeaturesRaw` / `encodeFtmsFeaturesRaw`
- `decodeFtmsRangeRaw` / `encodeFtmsRangeRaw`
- `decodeFtmsControlRequestRaw` / `encodeFtmsControlRequestRaw`
- `decodeFtmsControlResponseRaw` / `encodeFtmsControlResponseRaw`
- `decodeFtmsMeasurementRaw` / `encodeFtmsMeasurementRaw`
- `decodeFtmsMachineStatusRaw` / `encodeFtmsMachineStatusRaw`
- `decodeFtmsTrainingStatusRaw` / `encodeFtmsTrainingStatusRaw`
- `evaluateFtmsCapabilities`

Explicit resistance/pace compatibility options apply to raw codecs and normalized
measurement parsers, including registry dispatch. Resistance-range options also
apply to normalized range decoding and capability evaluation. Each call requires
its own explicit selection; no setting changes another API's defaults. Legacy
treadmill pace values remain available through raw decoding, but normalized
seconds-per-500m fields stay null because the legacy units are unresolved.
Omit options or pass `{}` for defaults; malformed option values are rejected.
See the repository's `docs/device-compatibility.md` for field applicability.

These additions are local source work, **not a claim that the published 0.2.0
package already contains them**. No version bump or publication was performed.

Raw codecs use integer wire units and explicit diagnostics, matching the shared
bidirectional contracts. They accept `Uint8Array`/`ArrayBuffer` inputs, including
offset views and cross-realm inputs. Invalid arguments or unrepresentable values
throw `RawCodecError` with a `null`, `length`, `kind` or `range` category. Decoded
partial/unknown evidence can instead carry diagnostics: successful decoding does
not mean a complete or conformant packet. Encoder inputs are canonical values,
not permission to send controls. Unknown-response evidence is available through
the new raw decoder without changing the old decoder's stricter behavior.

Measurements use kinds 0–5 (Treadmill, Cross Trainer, Step Climber, Stair Climber,
Rower, Indoor Bike), 30 raw fields and explicit present/unavailable masks. See
the shared measurement contract for field order and per-kind units. Training
text is a `Uint8Array`, retaining invalid UTF-8 evidence on decode and requiring
valid UTF-8 on encode. Raw APIs intentionally do not silently convert display
units or aggregate More Data fragments.

Capability evaluation takes a pure protocol snapshot: uint32 generation, numeric
discovery/scope/read states, canonical 32-lowercase-hex UUIDs, uint16 properties,
and byte read evidence. Its report follows the shared capability contract,
including all 21 operations, duplicates, missing/failed reads and contradictions.
It does not perform discovery or return execution authorization. Full state-code
definitions and examples are in `shared/conformance/capabilities/v1/schema.json`
and `shared/protocol/capability-discovery.md` in the repository.

## Embedded and native mobile roadmap

The TypeScript package above is the only published package. The repository
places it in `packages/typescript` alongside [native port locations](https://github.com/deancochran/ftms/tree/main/packages)
for embedded C/C++, Swift, and Kotlin/Java. C now has an unreleased bidirectional source
implementation; Swift and Kotlin remain design scaffolds. No native release or
real-device compatibility claim is made.

The [cross-language architecture](https://github.com/deancochran/ftms/blob/main/docs/architecture.md)
preserves the npm package identity and the canonical `shared/conformance/v1` corpus. The
[capability-discovery design](https://github.com/deancochran/ftms/blob/main/shared/protocol/capability-discovery.md)
covers all six FTMS machine-data families, not only indoor bikes. Both interpreters
evaluates caller-supplied feature, characteristic, and range evidence without
owning BLE discovery or inferring a machine's identity.

The repository [coverage matrix](../../docs/coverage.md) distinguishes the current
protocol parity from platform-specific APIs and unverified device behavior; its
[versioning boundaries](../../docs/versioning.md) keep package releases independent
from FTMS and corpus revisions.

## Development

From the repository root:

```sh
pnpm install --frozen-lockfile
pnpm verify
```

The root is a private pnpm orchestration workspace; its build, test, type-check,
and verification commands forward to `packages/typescript`. Biome and Lefthook
remain root tooling. C uses its own native compiler/test commands; Swift and
Kotlin remain README-only scaffolds. None is a pnpm workspace package.

Lefthook is installed by `pnpm install` and runs `pnpm test` before every push.
Run one file with `pnpm --filter @deancochran/ftms exec vitest run test/control.test.ts`.

From `packages/typescript`, use `pnpm test`, `pnpm check-types`, `pnpm build`,
and `pnpm verify:package` directly, or `pnpm verify` for all gates. Package scripts
own npm build/staging and verification; lint and format use root Biome configuration.
This README and `CHANGELOG.md` are canonical package-owned documents, not generated
copies of repository documentation.

## Release

Update the source-controlled version and changelog together, merge the verified
change, then push the matching tag (for example, `v0.2.0`). Publishing rejects a
tag that does not exactly match `packages/typescript/package.json` or lacks a
`packages/typescript/CHANGELOG.md` entry.

### Qualification checklist

Before making Bluetooth interoperability, PTS, or qualification claims:

- test supported measurements, statuses, and controls on representative machines; record model,
  firmware, transport traces, and results;
- run the adopted FTMS v1.0 PTS suite with Mandatory Errata Correction 23224 and all applicable
  errata, retaining the PTS version and reports;
- validate caller-owned GATT behavior, including discovery, characteristic properties,
  indications, procedure serialization, timeouts, disconnects, and permission loss;
- convert failures into regression vectors and complete any required Bluetooth SIG qualification
  or listing process.

`pnpm verify` and the conformance corpus are release gates, not substitutes for these steps.

Security reports should follow the repository's
[security policy](https://github.com/deancochran/ftms/security/policy).

## License

[MIT](https://github.com/deancochran/ftms/blob/main/LICENSE) © Dean Cochran.
