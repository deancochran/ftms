# Swift port

Status: reserved, not implemented. No Swift package is available to install.

## Intended package

- Native Swift Package Manager distribution, with byte-oriented codec APIs.
- No Core Bluetooth, UI, connection lifecycle, or timer dependency in the core.
- Idiomatic value types, optional values, and explicit errors/diagnostics.
- The same feature/range and capability semantics as the other implementations;
  capability discovery must not be limited to indoor bikes.
- Integrate with Core Bluetooth in examples, not by taking ownership of it.

With the first implementation, keep Swift `Sources/`, `Tests/`, documentation,
and package tooling under this directory. Swift Package Manager Git URL
dependencies conventionally require a repository-root `Package.swift`; choose a
thin root manifest that points here, or a dedicated distribution repository. The
recommended repository choice is the thin root manifest exception, but do not add
an empty one now. Set Swift and Apple deployment baselines only after validating
the chosen APIs.

## Required evidence before release

1. Run the applicable shared corpus from `../../shared/conformance/v1/` with native tests.
2. Verify byte offsets, signed values, normalized units, unavailable values, and
   malformed input without relying on aligned memory loads.
3. Build an isolated Swift Package Manager consumer from the Git URL (not merely
   a local directory) without Node or another port.
4. Validate the core on the documented toolchains/platforms and provide an iOS
   example receiving characteristic bytes through Core Bluetooth.
5. Document that permissions, subscriptions, security, control ownership, and
   connection lifecycle remain application responsibilities.

Simulator/build results and real-device BLE interoperability are separate gates.
See the [architecture](../../docs/architecture.md) and
[capability design](../../shared/protocol/capability-discovery.md).

This package will own its API docs and build/test tooling. It consumes the
independent shared layer; shared assets do not depend on Swift or its tools.
See the shared [conformance runner contract](../../shared/conformance/README.md),
[coverage matrix](../../docs/coverage.md), and
[versioning boundaries](../../docs/versioning.md).
