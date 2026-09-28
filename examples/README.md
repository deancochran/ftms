# FTMS integration examples

These are runnable external-consumer codec examples. They use installed package
boundaries rather than workspace imports and intentionally contain no BLE stack,
device identifiers, or control writes.

| Example | Status | Run |
| --- | --- | --- |
| [TypeScript client](typescript-client/) | Uses released `@deancochran/ftms@0.2.0` | `cd examples/typescript-client && npm install && node main.mjs` |
| [C client](c-client/) | Uses the unreleased local C `0.1.0` source candidate after an isolated install | See its README |

Both examples decode Indoor Bike and non-bike Treadmill values and construct
bytes only. Feature declarations, ranges, and successful codec calls are not
permission to control equipment. Real control procedures require caller-owned
discovery, properties, security, ownership, supported-range validation,
serialization, response handling, failure handling, and user authorization.

They are deterministic host simulations, not evidence of real equipment,
Bluetooth lifecycle behavior, PTS results, or Bluetooth qualification.

See [released package status](../docs/released-packages.md) before assuming a
source API is available from a registry. Follow the [equipment-test procedure](../docs/equipment-testing.md)
to record real observations; no equipment interoperability result is currently recorded.
