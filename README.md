# FTMS Protocol Libraries

**Transport-independent Bluetooth Fitness Machine Service protocol libraries.**

Replace handwritten FTMS packet parsing with typed values, explicit diagnostics,
and bidirectional codecs. Decode telemetry, inspect capability evidence, and
encode protocol messages—without replacing your Bluetooth stack.

For application developers, firmware authors, and protocol tooling maintainers.
Created and maintained by Dean Cochran; contributions are welcome.

## Choose your implementation

| Environment | Start here | Distribution |
| --- | --- | --- |
| JavaScript / TypeScript | [Five-minute quickstart](examples/typescript-quickstart/README.md) | npm: `@deancochran/ftms` |
| C / C++ | [Installed-library quickstart](examples/c-client/README.md) | C99 source archive; CMake installation |
| Swift | [Swift guide](packages/swift/README.md) | SwiftPM: `swift-v0.1.0` |
| Kotlin / Java | [Kotlin guide](packages/kotlin/README.md) | Maven Central: `io.github.deancochran:ftms:0.1.0` |
| Go | [Go guide](packages/go/README.md) | Go module `github.com/deancochran/ftms/packages/go` v0.1.0 |
| Python | [Python guide](packages/python/README.md) | `deancochran-ftms` 0.1.0a1 alpha; capability evaluator available in unreleased source only |
| Rust | [Rust guide](packages/rust/README.md) | crates.io `ftms` 0.1.0; later range/control/status projections and 97-case evidence are unreleased |
| Dart / Flutter | [Dart guide](packages/dart/README.md) | Pure Dart 0.1.0 source candidate; not published on pub.dev |

The [canonical release matrix](docs/released-packages.md) records verified versions,
publication identity, installation requirements and evidence limits.
See [releasing](docs/releasing.md) for independent package tags and release steps.
The role-based [support profiles](docs/support-profiles.md) distinguish client and
equipment wire directions from optional package modules.

Rust is an independent, allocation-free `no_std` implementation with raw codecs,
static capability evidence, normalized views, and bounded record planning/assembly;
it does not own BLE, execution authority, or device lifecycle. See its
[coverage and evidence](packages/rust/docs/verification.md).

## Decode your first measurement

With Node.js 20+ in a new directory:

```sh
npm init -y
npm install @deancochran/ftms@0.4.0
```

Save as `reading.mjs`, then run `node reading.mjs`:

```js
import { parseFtmsIndoorBikeMeasurement } from "@deancochran/ftms";

const bytes = Uint8Array.of(0x44, 0x00, 0x10, 0x0e, 0xb4, 0x00, 0xfa, 0x00);
const reading = parseFtmsIndoorBikeMeasurement(bytes);
console.log(reading.metrics.speedMps);   // 10
console.log(reading.metrics.cadenceRpm); // 90
console.log(reading.metrics.powerWatts); // 250
console.log(reading.diagnostics.truncated); // false
```

These are illustrative bytes, not a device capture. The
[runnable quickstart](examples/typescript-quickstart/main.mjs) asserts these values
and checks a deliberately truncated input. No Bluetooth hardware is needed.

## What you get

- All six FTMS measurement families: treadmill, cross trainer, step climber,
  stair climber, rower and indoor bike.
- Features, supported ranges, training/machine statuses and Control Point codecs.
- TypeScript normalized metrics and raw APIs; C fixed-point values and diagnostics.
- Static capability interpretation that preserves missing and contradictory evidence.
- Shared, versioned regression fixtures and verified package-consumer boundaries.

See [coverage](docs/coverage.md) for exact scope. Protocol coverage is not universal
equipment compatibility. A [limited passive KICKR CORE pilot](docs/equipment-results/2026-09-29-kickr-core-linux.md)
is evidence for that recorded setup only, not control safety or qualification.

## What stays in your application

Bluetooth discovery, permissions, connections, subscriptions, timing, reconnection,
control ownership, procedure serialization and physical safety. Encoding a valid
command or observing a supported feature does **not** authorize sending it.
This is not a complete trainer controller or a Bluetooth-qualified product.

## Integrate

- [Documentation website](https://deancochran.github.io/ftms/)
- [Documentation and recommended reading order](docs/README.md)
- [Static documentation site: local preview and deployment](site/README.md)
- [Integration cookbook](docs/integration.md)
- [Web Bluetooth, React Native and C byte-boundary recipes](docs/transport-recipes.md)
- [Public API selection and reference](docs/api.md)
- [Troubleshooting](docs/troubleshooting.md)
- [TypeScript package details](packages/typescript/README.md) · [C installation](packages/c/INSTALL.md)

## Contribute and verify

See [CONTRIBUTING.md](CONTRIBUTING.md), [roadmap and non-goals](docs/roadmap.md),
[MIT license](LICENSE), and [security reporting](SECURITY.md).

From a source checkout with Node.js 20+ and pnpm 10.33.0:

```sh
pnpm install --frozen-lockfile
pnpm verify
pnpm docs:build
make -C packages/c test
```

pnpm checks validate TypeScript and documentation, not native code or devices.
Native tests need their own host compilers and dependencies; see the contributor guide.
No command above operates equipment or publishes a release.

Repository boundaries and package ownership are documented in
[architecture](docs/architecture.md). Protocol contracts and fixtures live under
[shared/](shared/README.md); language-owned sources and tools live under
[packages/](packages/README.md). Detailed historical verification remains available
through the documentation index, separate from the getting-started path.
