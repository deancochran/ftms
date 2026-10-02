# Public API index

## References by language

Start with the public reference or package guide for your language. There is not
yet a uniform generated reference for all nine ports; guides below are real entry
points, not promises of equivalent documentation tooling.

| Language | Reference / usage guide |
| --- | --- |
| C | [Public header index](#c-public-headers) and [C guide](../packages/c/README.md) |
| C# | [Public API](../packages/csharp/docs/api.md) |
| Dart | [Dart package guide](../packages/dart/README.md) |
| Go | [Go package guide](../packages/go/README.md) and [capabilities](../packages/go/docs/capabilities.md) |
| Kotlin/JVM | [Kotlin and Java guide](../packages/kotlin/README.md) |
| Python | [Python package guide](../packages/python/README.md) |
| Rust | [Rust package guide](../packages/rust/README.md) |
| Swift | [Swift package guide](../packages/swift/README.md) |
| TypeScript | [Task index](#typescript-reference) and [package guide](../packages/typescript/README.md) |

Need installation first? [Choose a language](../packages/README.md).
The detailed task tables below cover TypeScript and C. Import TypeScript APIs
from `@deancochran/ftms`, never `src/` or unexported subpaths. Include installed C
headers as `<ftms/measurement.h>`, for example, and link `ftms::ftms`.

## TypeScript reference

The documentation site publishes searchable TypeDoc HTML from public exports and
source comments. The installed package's `dist/index.d.ts` and referenced
declarations remain the offline API authority. Generated HTML is not included in
the npm artifact. Contributors can reproduce it using the
[site development instructions](../site/README.md).

| Task | Public API |
| --- | --- |
| Measurement, normalized | `parseFtmsTreadmillData`, `parseFtmsCrossTrainerData`, `parseFtmsStepClimberData`, `parseFtmsStairClimberData`, `parseFtmsRowerData`, `parseFtmsIndoorBikeMeasurement`; `decodeIndoorBikeData` (named Indoor Bike measurement/raw/diagnostics view) |
| Characteristic dispatch | `parseRegisteredFtmsPayload`, `FTMS_CHARACTERISTICS`, `FTMS_DATA_CHARACTERISTICS` |
| Features | `decodeFtmsFeatures`; `decodeFtmsFeaturesRaw` / `encodeFtmsFeaturesRaw` |
| Ranges | `decodeFtmsRange`, `decodeSupportedPowerRange` and the other named range decoders; `decodeFtmsRangeRaw` / `encodeFtmsRangeRaw`; `inspectFtmsRangeRaw` |
| Measurements, raw | `decodeFtmsMeasurementRaw` / `encodeFtmsMeasurementRaw` |
| Requests, normalized | `tryEncodeFtmsControlRequest` (result union), `encodeFtmsControlRequest` (throwing) |
| Requests, raw | `decodeFtmsControlRequestRaw` / `encodeFtmsControlRequestRaw` |
| Responses | `decodeFtmsControlResponse` (validated result); `decodeFtmsControlResponseRaw` / `encodeFtmsControlResponseRaw` |
| Statuses | `parseFtmsTrainingStatus`, `parseFtmsMachineStatus`; `decodeFtmsTrainingStatusRaw` / `encodeFtmsTrainingStatusRaw`; `decodeFtmsMachineStatusRaw` / `encodeFtmsMachineStatusRaw` |
| Capability evidence | `evaluateFtmsCapabilities`, `FtmsCapabilitySnapshot`, `FtmsCapabilityReport` |

Normalized names carry units (`speedMps`, `cadenceRpm`, `powerWatts`). Missing or
unavailable metrics are `null`; diagnostics are separate from metrics. Raw codecs
preserve wire-scale values and have API-specific validation/throw behavior. Use
the generated signatures and comments, not a guessed common decoder contract.

## C public headers

| Installed header | Operations and ownership |
| --- | --- |
| [ftms.h](../packages/c/include/ftms/ftms.h) | `ftms_decode_features`, `ftms_encode_features`, `ftms_decode_range`, `ftms_encode_range`, `ftms_inspect_range` and explicit-format variants; result codes and masks |
| [measurement.h](../packages/c/include/ftms/measurement.h) | `ftms_decode_measurement`, `ftms_encode_measurement`, `ftms_measurement_plan`, explicit-format variants and caller-owned `ftms_record_*` assembly APIs |
| [control.h](../packages/c/include/ftms/control.h) | `ftms_encode_control_request`, `ftms_decode_control_request`, format variants, `ftms_encode_control_response`, `ftms_decode_control_response` |
| [status.h](../packages/c/include/ftms/status.h) | Machine and Training Status encode/decode APIs, partial evidence and text-span rules |
| [capabilities.h](../packages/c/include/ftms/capabilities.h) | `ftms_capability_requirements*` and matching `ftms_evaluate_capabilities*`; caller-owned buffers, discovery evidence and C.7 options |

C values use documented fixed-point integers, not normalized JavaScript floats.
Read each header's capacity, lifetime, overlap and unchanged-output error contracts.
Only consume output after the function's success contract is satisfied; success
may still carry payload diagnostics. The library's C++ linkage guards permit C++
consumers, but the implementation is compiled as C99.

These indexes describe codecs and static evidence, not an executable control
session. See the [cookbook](integration.md) for application responsibilities.
