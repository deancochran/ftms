# Transport byte-boundary recipes

**Example languages: JavaScript/TypeScript and C.** Web Bluetooth and React Native
examples below adapt JavaScript values; the C recipe adapts a pointer and length.
These are not transport implementations for all nine ports. Start with your
[language guide](../packages/README.md) for its native input and ownership contracts.

These are integration examples, not additions to the protocol package. The
[tested conversion module](../examples/typescript-quickstart/transport.mjs) and
[assertions](../examples/typescript-quickstart/recipes.mjs) run with the installed
package. They perform no scanning, connecting, subscribing or writing.

## Web Bluetooth

Web Bluetooth exposes a characteristic value as a `DataView`. Pass exactly that
view's span, not its entire backing buffer:

```js
const bytes = new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
```

Here `value` is the `DataView` received by your application's notification handler.
For a complete callable implementation, use `parseBikeDataView` from the example
module. The tests use a two-byte prefix and a trailing byte outside the view, then
assert the same result as the original notification. A shortened view must report
truncation. The conversion creates a view, not a snapshot; copy with
`Uint8Array.from(bytes)` if your application retains bytes from a mutable buffer.

Browser Bluetooth availability, secure-context requirements, user permission,
subscription cleanup and reconnection are separate host responsibilities. Node
conversion tests do not establish browser Bluetooth support.

## React Native with react-native-ble-plx

The [react-native-ble-plx Characteristic contract](https://github.com/dotintent/react-native-ble-plx/blob/master/src/Characteristic.js)
defines `value` as nullable Base64. Verified against that public source on
2026-09-29; confirm the contract for your installed transport version.

Install `base64-js@1.5.1` in the **application**, then use the example module's
`parseBlePlxBike(characteristic.value)`. It returns `null` for a missing transport
value and otherwise converts with `base64.toByteArray` before parsing. Do not
decode base64 as UTF-8 or pass the encoded string into the protocol API.

The host tests exercise a known base64 payload, null/undefined, wrong input type,
and invalid length. `base64-js` is a decoder, not a general untrusted-input
validation layer; validate arbitrary external text separately. BLE monitor errors
must be handled before calling the conversion function. Use the transport
subscription's cleanup API when your screen/session ends.

This recipe validates conversion under Node, not Metro bundling, native permission
configuration, iOS/Android behavior or a live BLE connection. No React Native
dependency is added to `@deancochran/ftms`.

## C notification buffers

The complete [C client](../examples/c-client/main.c) supplies a `const uint8_t *`
and the actual received length to `ftms_decode_measurement`. In a notification
callback, use the transport's length—not the allocation capacity—and choose the
kind from the discovered characteristic. Check both the returned `ftms_result`
and the decoded diagnostic fields before consuming measurements.

The core does not retain the notification buffer. If the application queues
processing after callback return, it must first copy bytes according to the
transport's lifetime contract. Installed headers document output/capacity and
overlap rules; no platform SDK is needed to compile the host example.
