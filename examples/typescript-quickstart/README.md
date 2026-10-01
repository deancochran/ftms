# TypeScript quickstart

Prerequisites: Node.js 20+ and npm. The package is ESM-only; `.mjs` works without
changing an application's module setting. TypeScript declarations ship with it.

## Add to your application

```sh
npm install @deancochran/ftms
```

This selects npm's `latest` dist-tag. Retain the saved dependency and lockfile,
and consult the changelog when upgrading. See [all-port installation guidance](../../docs/install.md).

## Reproduce the verified example

From this directory in a source checkout (the example deliberately pins its tested release):

```sh
npm install --ignore-scripts --no-audit --no-fund
npm start
npm test
```

Alternatively, copy `package.json`, `main.mjs`, `recipes.mjs` and `transport.mjs`
to a new directory and run the same commands. All imports resolve through the
installed npm package, not repository source. This example pins the current
[verified release](../../docs/released-packages.md); the older
[0.2.0 client](../typescript-client/README.md) is a separate compatibility fixture.

Expected `npm start` output (after npm's command banner):

```text
speedMps=10 cadenceRpm=90 powerWatts=250 hrBpm=null
complete.truncated=false short.truncated=true
```

`main.mjs` asserts every displayed value. `npm test` additionally exercises UUID
dispatch, features, ranges, control codecs, a nonzero-offset DataView, and
nullable base64 from the react-native-ble-plx payload contract. `base64-js` is an
example-only conversion dependency; it is not a dependency of the protocol core.

Read [main.mjs](main.mjs), then [recipes.mjs](recipes.mjs) and
[transport.mjs](transport.mjs). The [cookbook](../../docs/integration.md) explains
API choices and application responsibilities.

These tests are host-only and send no commands. They do not validate browser
permissions, Metro, a mobile BLE stack, device behavior, or physical control safety.
