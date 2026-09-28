# TypeScript FTMS client example

This runnable Node ESM example uses the released `@deancochran/ftms@0.2.0`
package through its public package name. It decodes Feature and Supported Power
Range characteristic values, parses Indoor Bike and Treadmill characteristic
values, and constructs (but does not send) a Request Control byte sequence.

## Run

Node.js 20 or newer is required.

```sh
cd examples/typescript-client
npm install
node main.mjs
```

The package receives only characteristic bytes. Your BLE integration must supply
the bytes after its own discovery and subscription work. Feature declarations and
ranges are capability evidence, not permission to control equipment. Before any
control procedure, the application must discover the proper characteristic state
and properties, satisfy security requirements, handle control ownership and
indications, and validate the requested value against the actual supported range.

The released 0.2.0 package does not expose the unreleased aggregate capability
evaluation API, so this example deliberately does not claim that API is available.
It does not perform BLE I/O, write a control point, identify hardware, or provide
real-equipment or Bluetooth qualification evidence.
