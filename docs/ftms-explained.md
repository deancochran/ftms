# FTMS explained: from bytes to a workout

**A bike reports `44 00 10 0e b4 00 fa 00`. Your application needs 36 km/h,
90 rpm and 250 W. FTMS defines the meaning of those bytes; this project's
libraries implement that translation so your application does not have to.**

This guide explains the protocol, works through the arithmetic, and shows the
actual public package interface. The worked packets are synthetic teaching
examples, not device captures. The snippets use the published TypeScript package
and run without equipment. The wire meanings also apply to the native ports;
their interfaces and optional convenience modules are language-specific.

## The protocol and the package are different things

**Fitness Machine Service (FTMS)** is a Bluetooth SIG service specification. It
defines how fitness equipment describes supported features, reports measurements,
and exchanges control messages. It covers treadmills, cross trainers, step
climbers, stair climbers, rowers and indoor bikes.

**FTMS Protocol Libraries** is this repository's implementation of that binary
protocol. A codec is a function that decodes bytes into values or encodes values
into bytes. These packages are not Bluetooth drivers or trainer controllers.

```text
Equipment sensors / equipment application
    -> FTMS measurement encoder
    -> Bluetooth stack sends a characteristic value
    -> application's Bluetooth stack receives bytes
    -> FTMS measurement decoder
    -> application's display, recording or analysis

Application's requested target
    -> FTMS request encoder
    -> application-owned control procedure and Bluetooth write
    -> equipment's FTMS request decoder
    -> equipment-owned validation, control and response
```

The equipment does not need to use this library for your application to use it.
Both ends need to agree on the wire format, not the programming language or
library. Likewise, firmware using the C port can exchange standard messages with
an application using a different FTMS implementation.

The library itself does no discovery, connection, subscription or transmission.
It can also process saved bytes in an offline tool, without a Bluetooth adapter.

## How the application knows what the bytes mean

Bluetooth GATT organizes data into **services** and **characteristics**. A
characteristic has an identifier (UUID), properties such as Read or Notify, and a
value. The UUID supplies context: the bytes alone are not self-describing JSON.

| Identifier | Meaning | Typical client operation |
| --- | --- | --- |
| `0x1826` | Fitness Machine Service | Discover the service |
| `0x2ACC` | Fitness Machine Feature | Read declared features |
| `0x2AD2` | Indoor Bike Data | Subscribe to measurements |
| `0x2AD8` | Supported Power Range | Read limits and increment |
| `0x2AD9` | Fitness Machine Control Point | Write requests and receive indicated responses |
| `0x2ADA` | Fitness Machine Status | Receive status notifications |

For example, `0x2AD2` expands to
`00002ad2-0000-1000-8000-00805f9b34fb`. Use the discovered characteristic to select
a decoder; do not infer an equipment type from a device name or packet length.
Availability and permitted operations still depend on the actual discovery and
read results. See [capability evidence](../shared/protocol/capability-discovery.md).

## Example 1: eight bytes become three measurements

Consider this Indoor Bike Data characteristic value:

```text
44 00 | 10 0e | b4 00 | fa 00
flags | speed | cadence | power
```

Hexadecimal is a readable notation for bytes, not text transmitted by the device.
The multi-byte integers here are **little-endian**: the least significant byte
comes first.

For two unsigned bytes `low` and `high`:

```text
raw = low + 256 × high
```

### Flags determine which fields exist

The first two bytes give `0x0044 = 68 = 2² + 2⁶`.

- Bit 0 (More Data) is clear: instantaneous speed is present in this packet.
- Bit 2 is set: instantaneous cadence is present.
- Bit 6 is set: instantaneous power is present.
- The other optional fields are absent, not zero.

The cadence-bit interpretation follows the corrected specification; the original
FTMS 1.0 table has a known polarity error. See the
[specification and errata audit](specification-audit.md).

### Decode the fields in the specified order

| Byte offset | Bytes | Raw interpretation | Physical value |
| --- | --- | --- | --- |
| 0–1 | `44 00` | Flags = 68 | Speed, cadence and power layout above |
| 2–3 | `10 0e` | `16 + 256 × 14 = 3600` | `3600 × 0.01 = 36 km/h` |
| 4–5 | `b4 00` | `180 + 256 × 0 = 180` | `180 × 0.5 = 90 rpm` |
| 6–7 | `fa 00` | Signed 16-bit integer = 250 | `250 × 1 = 250 W` |

The normalized TypeScript view reports speed in metres per second:

```text
36 km/h × 1000 metres/km ÷ 3600 seconds/hour = 10 m/s
```

These are reporting resolutions, not guarantees of sensor accuracy. Cadence can
also be fractional: raw `181` means `90.5 rpm`, not `90 rpm`.

Power is signed. For example, bytes `ce ff` represent unsigned `65486`; interpreted
as a signed 16-bit value, `65486 − 65536 = −50 W`. Treating every field as unsigned
would produce a very different measurement. Each field has its own type, scale
and, where defined, unavailable sentinel.

### Let the library do the translation

With Node.js 20+, in an empty directory:

```sh
npm init -y
npm install @deancochran/ftms@0.4.0
```

Save each JavaScript block in this guide as a separate `.mjs` file and run it with
`node filename.mjs`. Assertions check the stated results; they perform no I/O to
equipment.

```js
import assert from "node:assert/strict";
import { parseFtmsIndoorBikeMeasurement } from "@deancochran/ftms";

const bytes = Uint8Array.of(0x44, 0x00, 0x10, 0x0e, 0xb4, 0x00, 0xfa, 0x00);
const reading = parseFtmsIndoorBikeMeasurement(bytes);

assert.equal(reading.metrics.speedMps, 10);
assert.equal(reading.metrics.cadenceRpm, 90);
assert.equal(reading.metrics.powerWatts, 250);
assert.equal(reading.metrics.hrBpm, null);
assert.equal(reading.diagnostics.truncated, false);
console.log("10 m/s (36 km/h), 90 rpm, 250 W; no heart-rate field");

// The same layout can carry fractional cadence and signed power.
const signed = parseFtmsIndoorBikeMeasurement(
  Uint8Array.of(0x44, 0x00, 0x10, 0x0e, 0xb5, 0x00, 0xce, 0xff),
);
assert.equal(signed.metrics.cadenceRpm, 90.5);
assert.equal(signed.metrics.powerWatts, -50);

// Only one of the two power bytes remains: that is not a zero-watt reading.
const partial = parseFtmsIndoorBikeMeasurement(bytes.subarray(0, 7));
assert.equal(partial.metrics.speedMps, 10);
assert.equal(partial.metrics.cadenceRpm, 90);
assert.equal(partial.metrics.powerWatts, null);
assert.equal(partial.diagnostics.truncated, true);
```

The application decides whether to display the complete fields of a partial
reading. It must not present an old power value as a fresh measurement or convert
missing power to zero without an explicit application policy.

### Why fixed offsets are not a general solution

The eight-byte example is deliberately simple. If Average Speed is also present,
bit 1 is set and another field appears before cadence:

```text
46 00 | 10 0e | 18 0b | b4 00 | fa 00
flags | speed | average speed | cadence | power

Average speed: 0x0b18 = 2840 -> 28.4 km/h
Cadence now starts at offset 6, not 4.
Power now starts at offset 8, not 6.
```

A hard-coded read at offset 4 would now interpret average speed as cadence. A
general parser must walk the flags, honor ordering and widths, check lengths,
interpret signedness, preserve unavailable values, and apply the selected format.
The package centralizes that work; your call to the parser does not change.

## Example 2: a feature declaration is not a current reading

Fitness Machine Feature contains two 32-bit little-endian words. The first
describes measurement features; the second describes target-setting features.

```text
02 40 00 00 | 08 00 00 00
machine features | target-setting features

Machine word = 0x00004002 = 2¹ + 2¹⁴
    bit 1: cadence supported
    bit 14: power measurement supported
Target word = 0x00000008 = 2³
    bit 3: power target setting supported
```

Feature bits and measurement flags are **different bitfields**. Cadence support
is bit 1 of the Feature word; cadence presence in Indoor Bike Data is bit 2 of
that packet's flags. A capability declaration does not mean the field is present
in every notification.

A separate Supported Power Range example is:

```text
00 00 | f4 01 | 0a 00
minimum | maximum | increment
0 W | 500 W | 10 W
```

For this well-formed example, a requested target `p` is on the advertised grid if:

```text
0 ≤ p ≤ 500, and (p − 0) mod 10 = 0
250 W passes. 255 W is within the limits but not on the grid. 510 W exceeds it.
```

This is only a numeric preflight check against the advertised range, not proof
that a target is currently accepted or physically achievable. Equipment limits
can depend on current speed and operating conditions; the application still
needs its control policy and the equipment's procedure response.

```js
import assert from "node:assert/strict";
import { decodeFtmsFeatures, decodeSupportedPowerRange } from "@deancochran/ftms";

const features = decodeFtmsFeatures(
  Uint8Array.of(0x02, 0x40, 0, 0, 0x08, 0, 0, 0),
);
assert.equal(features.ok, true);
assert.equal(features.value.cadenceSupported, true);
assert.equal(features.value.powerMeasurementSupported, true);
assert.equal(features.value.powerTargetSettingSupported, true);

const range = decodeSupportedPowerRange(Uint8Array.of(0, 0, 0xf4, 1, 0x0a, 0));
assert.equal(range.ok, true);
assert.deepEqual(range.value, {
  kind: "power", min: 0, max: 500, increment: 10, unit: "watts",
});
console.log(range.value); // 0–500 W, in 10 W increments
```

Production callers must handle `ok: false`; assertions are used here to verify
known examples. Keep unread, failed and malformed observations separate. A failed
read is not a declaration that every feature is unsupported. Static capability
evaluation combines caller-provided evidence; it does not perform discovery or
grant permission to issue a command.

## Example 3: a target becomes a command, then a response

To request a 250 W target, the protocol uses:

```text
05 | fa 00
Set Target Power opcode | signed 16-bit target in watts

250 decimal = 0x00fa -> low byte fa, high byte 00
```

This is a target, not a power measurement. A synthetically successful response is:

```text
80 | 05 | 01
Response Code opcode | original request opcode | Success result
```

The same bytes can be encoded on one side and decoded on the other:

```js
import assert from "node:assert/strict";
import {
  decodeFtmsControlRequestRaw,
  decodeFtmsControlResponse,
  tryEncodeFtmsControlRequest,
} from "@deancochran/ftms";

// Client side: construct bytes, without sending anything.
const request = tryEncodeFtmsControlRequest({
  op: "setTargetPower", powerWatts: 250,
});
assert.equal(request.ok, true);
assert.deepEqual([...request.value], [0x05, 0xfa, 0x00]);

// Equipment/tool side: decode exactly those bytes to raw protocol values.
assert.deepEqual(decodeFtmsControlRequestRaw(request.value), {
  opcode: 5, operands: [250],
});

// A target must be representable on the wire: no silent fractional rounding.
assert.equal(tryEncodeFtmsControlRequest({
  op: "setTargetPower", powerWatts: 250.5,
}).ok, false);

// Synthetic response, not an acknowledgment from a real machine.
const response = decodeFtmsControlResponse(Uint8Array.of(0x80, 0x05, 0x01));
assert.equal(response.ok, true);
assert.equal(response.value.success, true);
console.log("Request: 05 fa 00; illustrative response: 80 05 01");
```

The encoder checks protocol representability; it does **not** automatically check
the machine's range or current control ownership. For example, an integer target
can fit the wire type but lie outside the example's 0–500 W range.

Before a real write, the application must establish the necessary discovery,
security, feature/range evidence, indication subscription, user intent and control
ownership. It must serialize procedures and handle rejection, timeout, disconnect
and permission loss. FTMS has no transaction IDs: an echoed opcode is not enough
to safely distinguish a late response from a subsequent request with that opcode.
A successful procedure response also does not independently measure actual power.

## What you stop implementing yourself

| Without a shared codec | With the FTMS package |
| --- | --- |
| Walk every optional field and maintain byte offsets | Select the characteristic/family and decode its bytes |
| Repeat signedness, scaling and sentinel rules | Consume documented raw values or normalized views |
| Build opcode/operand byte layouts | Construct requests through a codec |
| Distinguish partial data from valid zero values manually | Inspect presence/unavailable evidence and diagnostics |
| Maintain separate protocol interpretations in each application | Reuse a port tested against shared versioned fixtures |
| Mix device workarounds with general parsing | Keep application device knowledge and select supported formats explicitly |

This is a reduction in **protocol responsibilities**, not a measured claim about
lines removed from someone else's repository. Codecs still require application
mapping, error handling, and equipment-specific decisions. They are especially
useful once a project supports optional fields, multiple machine families, both
wire directions, or more than one implementation language.

### The same protocol work appears in different products

- **A workout application** decodes telemetry for display and recording, and may
  encode target requests. It keeps its existing Bluetooth client and UI.
- **Equipment firmware or a simulator** encodes measurements and decodes incoming
  requests. It keeps its own GATT server, notification scheduling and safety logic.
- **A bridge or offline protocol tool** may use both directions. It retains the
  original bytes when exact replay matters: canonical encoding is not a promise
  to reproduce malformed packets or unknown trailing bytes.

The benefit does not depend on migrating a named application. The examples above
show the protocol responsibilities directly. For a fixed synthetic packet, a few
manual reads may be sufficient; for maintained protocol support, optional layouts,
errors and compatibility choices must also be handled somewhere.

## One wire format, independent language packages

Pick the implementation matching the host application; do not install every port.
The math above does not change with the programming language. The public interfaces
do change to fit that language's types, memory model and error handling.

| Environment | Package guide | Integration point |
| --- | --- | --- |
| JavaScript / TypeScript | [npm guide](../packages/typescript/README.md) | `Uint8Array` / `ArrayBuffer`; normalized parsers and raw codecs |
| C / C++ | [C guide](../packages/c/README.md) | Received byte pointer and length; fixed-point values and caller-owned storage |
| Swift | [Swift guide](../packages/swift/README.md) | `[UInt8]`; convert CoreBluetooth `Data` in the application |
| Kotlin / Java | [JVM guide](../packages/kotlin/README.md) | `ByteArray` / `byte[]`; no Android or coroutine dependency in the codec |
| Python | [Python guide](../packages/python/README.md) | Synchronous byte codecs beneath a client, server or offline tool |
| Rust | [Rust guide](../packages/rust/README.md) | Byte slices and caller-owned buffers; allocation-free `no_std` implementation |
| Dart / Flutter | [Dart guide](../packages/dart/README.md) | Pure Dart codecs beneath the application's Flutter/BLE integration |
| Go | [Go guide](../packages/go/README.md) | Native Go codecs; no other port required at runtime |
| C# / .NET | [.NET guide](../packages/csharp/README.md) | Native .NET codecs; transport remains application-owned |

Consult the [release matrix](released-packages.md) for exact installation versions,
prerelease status and toolchain requirements, and [support profiles](support-profiles.md)
for normalized views, capability evidence and record planning/assembly. Identical
wire coverage does not mean identical convenience interfaces.

## What the examples establish—and what they do not

The examples establish exact byte/value relationships and show which work the
public codec interface replaces. Shared fixtures test those relationships across
implementations. Neither mathematical agreement nor a passing codec test proves
physical measurement accuracy or compatibility with every device.

There is separate, limited [KICKR CORE passive pilot evidence](equipment-results/2026-09-29-kickr-core-linux.md):
55 notifications across two sessions decoded with matching C/TypeScript raw
reports. That record did not test live controls or independently validate physical
measurements, and the packets in this guide are not taken from that capture.

Explicit alternative layouts also exist in deployed equipment. Consult
[wire compatibility](../shared/protocol/wire-compatibility.md); do not automatically
select a format from packet length, device name, or another characteristic's
layout. When a measurement spans More Data notifications, decoding a packet is
not the same as assembling a record. Use a port's supported assembly module where
appropriate, with caller-owned lifecycle/freshness policy.

**The reason to use the package is focused:** keep the Bluetooth stack, application
architecture and equipment policy you already have, while replacing repeated
binary-protocol work with reusable, tested codecs.

Next: [run a quickstart](../examples/typescript-quickstart/README.md),
[choose the interface for your task](api.md), or
[connect your transport's byte representation](transport-recipes.md).
