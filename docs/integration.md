# Integration cookbook

**Example languages: TypeScript and C.** These executable recipes do not imply
matching APIs in other ports. For every language's installation and usage entry
point, see [Choose a language](../packages/README.md). Shared protocol concepts
are explained in [What is FTMS?](ftms-explained.md); optional modules are listed
in [support profiles](support-profiles.md). Every port follows the same
[consumer adapter seam](architecture.md#consumer-adapter-seam): these TypeScript
and C recipes are examples of that seam, not a shared transport interface.

Start with the [installed TypeScript quickstart](../examples/typescript-quickstart/README.md)
or [C/C++ quickstart](../examples/c-client/README.md). The complete, executable
TypeScript recipes live in [recipes.mjs](../examples/typescript-quickstart/recipes.mjs)
and run with `npm test`. Their assertions are the expected results—not device claims.

## Select an API

| Task | TypeScript | C |
| --- | --- | --- |
| Display measurements | `decodeFtmsMeasurement` with the discovered machine-data UUID | `ftms_decode_measurement`; convert documented fixed-point fields in the application |
| Dispatch by characteristic | `parseRegisteredFtmsPayload` | Select the explicit kind from caller-owned discovery |
| Decode feature declarations | `decodeFtmsFeatures` | `ftms_decode_features` |
| Read a supported range | `decodeFtmsRange` / `decodeSupportedPowerRange` | `ftms_decode_range` |
| Inspect range structure | `inspectFtmsRangeRaw` | `ftms_inspect_range` |
| Construct a control request | `tryEncodeFtmsControlRequest` | `ftms_encode_control_request` |
| Interpret a response | `decodeFtmsControlResponse` | `ftms_decode_control_response` |
| Evaluate discovery evidence | `evaluateFtmsCapabilities` | `ftms_evaluate_capabilities_with_c7` and its matching requirements API |

See the [API index](api.md) for raw codecs, status APIs and public C headers.

## Parse and dispatch measurements

The quickstart uses the illustrative packet `44 00 10 0e b4 00 fa 00`: speed
10 m/s, cadence 90 rpm and power 250 W. Heart rate is absent and becomes `null`,
not zero. Removing the final byte produces a truncated reading and missing power.
The dispatch recipe uses the full Indoor Bike characteristic UUID
`00002ad2-0000-1000-8000-00805f9b34fb`. Handle an unrecognized UUID explicitly;
do not assume every notification contains indoor-bike data.

For new application code prefer `decodeFtmsMeasurement` for UUID-selected machine
data; it returns a known/unsupported union, common metrics and named raw values.
Use the older family parsers when their `ParsedFtmsPayload` shape is required.
Raw APIs preserve wire values and
are useful for protocol tools, equipment-side encoding and fixture comparisons.
Raw values are not display units; consult types/headers before conversion.

## Features, ranges and capability evidence

The recipe decodes cadence and power-target declarations plus a supported power
range of 0–500 W in 10 W increments. A declaration is not a successful command,
and a valid range does not establish current control ownership.

Feature/range convenience decoders return `{ ok, value }` or `{ ok, error }`.
Check `ok` before accessing `value`. A malformed read is not an all-zero feature
declaration. Keep absent, unread, failed and malformed evidence distinct.

For aggregate evaluation, supply one service instance and discovery generation
to `evaluateFtmsCapabilities`. Use its public `FtmsCapabilitySnapshot` type and
the [capability contract](../shared/protocol/capability-discovery.md), not an invented
device-class object. C callers use the matching requirements/evaluation pair and
caller-owned buffers; retain C.7 evidence and format options consistently in both
passes. Missing evidence stays unknown, not false. No evaluator performs discovery
or grants execution permission.

## Encode and decode control messages—without sending

The tested recipe encodes 250 W as `05 fa 00`, rejects fractional raw-grid input
250.5 W, and decodes the illustrative successful response `80 05 01`.
The response bytes are synthetic: they are not an acknowledgment from equipment.

Prefer `tryEncodeFtmsControlRequest` at untrusted boundaries. The throwing
`encodeFtmsControlRequest` convenience API is appropriate when the caller handles
exceptions. Raw codecs have their own result/throw contracts; inspect their
reference signatures rather than assuming all decoders behave identically.

Before an actual write, the host application must establish discovery/properties,
security, relevant features, machine ranges and increments, explicit user intent,
and control ownership. It must serialize procedures, correlate matching indications,
and handle rejection, timeout, disconnect and permission loss. FTMS has no
transaction identifiers; a late response must not be casually attributed to the
next command. These recipes deliberately do not implement or execute that lifecycle.

## Explicit formats and numeric inputs

The recipe explicitly selects `resistanceFormat: "uint8Tenths"`, encoding 12.3
as `04 7b`. Omitted options retain the existing signed16-tenths default; they are
not automatic negotiation. Never select formats from packet length, device name,
or a structurally valid alternate interpretation. See
[wire compatibility](../shared/protocol/wire-compatibility.md) and
[numeric-input rules](../shared/protocol/numeric-inputs.md).

## Diagnostics and More Data

Decode success can coexist with truncation, unknown/reserved values, trailing
bytes or More Data. Inspect diagnostics before treating a value as complete.
Unavailable measurements are not zero and should not be silently carried forward
as fresh observations. The application owns freshness and disconnection policy.

TypeScript parsers do not reassemble More Data fragments. C provides an optional
caller-owned record assembler in `measurement.h`; its generation and caller-tick
inputs still require host lifecycle decisions. Neither implementation infers
reconnection, runs a timer, or makes stale values safe to act on.
