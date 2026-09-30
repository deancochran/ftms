# FTMS protocol project

Transport-independent codecs and shared protocol design for the Bluetooth
Fitness Machine Service (FTMS). Implementations interpret bytes; applications
own Bluetooth discovery, connections, control permission, and physical safety.

## Current support

Start with the [released-package status and examples](docs/released-packages.md).
The [TypeScript example](examples/typescript-client/README.md) works with the
published npm 0.2.0 compatibility baseline; the [C example](examples/c-client/README.md)
uses an installed source archive. A [limited passive KICKR CORE pilot](docs/equipment-results/2026-09-29-kickr-core-linux.md)
records 55 telemetry packets across two connections. It does not establish
universal device compatibility, physical accuracy or safe control execution.

[TypeScript / JavaScript](packages/typescript/README.md) is distributed as
`@deancochran/ftms`; the current source version is **0.4.0**. It provides codecs
for all six FTMS machine-data families, features, supported ranges, statuses,
and Control Point requests/responses. See its README for installation and API
usage and its [changelog](packages/typescript/CHANGELOG.md) for releases.

C/C++ has independently released bidirectional C99 codecs for Features, ranges,
all six measurement families, Control Point and statuses, plus static capability
interpretation. Its current source version is **0.2.0**. Both ports add explicit
range-inspection diagnostics without changing existing defaults or automatically
selecting device formats. [Swift](packages/swift/README.md) now has native codecs,
range inspection and capabilities with independent SwiftPM version **0.1.0**;
installation uses the Swift-specific tag or commit, not npm version ranges.
[Kotlin/JVM and Java](packages/kotlin/README.md) are supported by the independent
Maven Central package **`io.github.deancochran:ftms:0.1.0`**, including an Android
artifact-consumer build check.
[Rust](packages/rust/README.md) has an independent, allocation-free `no_std`
raw-codec implementation and gated crates.io publishing. Its **0.1.0** source is
not yet published; capability interpretation and fragment assembly are not implemented.
See [verified releases](docs/released-packages.md) for actual publication status
and [compatibility verification](docs/compatibility-verification.md) for scope and
test accounting. Neither regression tests nor one trainer pilot establish
universal interoperability, PTS results or Bluetooth qualification.

## Layout and dependencies

| Location | Ownership |
| --- | --- |
| [shared/](shared/README.md) | Language-neutral protocol definitions/design and versioned conformance fixtures |
| [packages/typescript/](packages/typescript/README.md) | npm API docs, changelog, sources, tests, compiler configs, and npm-specific scripts |
| [packages/c/](packages/c/README.md) | Portable bidirectional C99 codecs and static capability evidence, consumable from C++ |
| [packages/swift/](packages/swift/README.md) | Native Swift 6 protocol package for SwiftPM, independent of other ports |
| [packages/kotlin/](packages/kotlin/README.md) | Independent Kotlin/JVM FTMS package on Maven Central, consumable from Java/Android |
| [packages/rust/](packages/rust/README.md) | Independent allocation-free `no_std` raw codecs, host/embedded compilation checks and crates.io release tooling |
| [docs/](docs/architecture.md) | Repository-wide [architecture](docs/architecture.md), [coverage](docs/coverage.md), and [versioning](docs/versioning.md) guidance |
| [examples/](examples/README.md) | Installed consumers and passive capture/replay examples outside protocol cores |
| Root configs and workflows | Repository orchestration, formatting, hooks, and release gates |

Ports and their build/test tools consume `shared/`; shared definitions and
fixtures depend on no language-specific package or tool. Ports are siblings,
not wrappers around TypeScript, and consumers need not install other ports.
The npm build stages shared corpus snapshots at its existing public export
paths; these generated files are not separately maintained fixtures.

Root conventional configs stay at the root. Package-specific tooling stays
with its package. A future `tools/` directory is appropriate only when actual
shared tooling is implemented, not as a home for speculative infrastructure.
See the [architecture](docs/architecture.md) and
[capability contract](shared/protocol/capability-discovery.md) for boundaries.
The [conformance runner contract](shared/conformance/README.md) records the
language-neutral v1 comparison and reporting rules.
The [deterministic simulation contract](docs/simulation.md) is separate,
host-only protocol/session evidence and is not Bluetooth qualification.

## Repository commands

Run from the repository root with Node.js 20+ and pnpm 10.33.0:

```sh
pnpm install --frozen-lockfile
pnpm verify
```

The private pnpm workspace includes only TypeScript. Root `pnpm test`,
`pnpm check-types`, `pnpm build`, `pnpm clean`, and `pnpm verify:package` forward
to it. `pnpm verify` runs root lint, TypeScript checks and tests, then fresh-build
linked-consumer and packed-artifact verification. Root `pnpm lint` and
`pnpm format` use Biome; Lefthook runs `pnpm test` before pushes.

From `packages/typescript`, the corresponding package commands run directly;
its lint/format scripts use the root configuration. C host verification runs with
`make -C packages/c test`; the optional `make -C packages/c check-embedded` target
records Cortex-M0 compile-only evidence. These use actual compilers and isolated
C/C++ consumers. pnpm success does not validate native code or devices.

## Policy and releases

[LICENSE](LICENSE) and [SECURITY.md](SECURITY.md) are canonical repository policy.
The TypeScript build stages those policies into the npm package. npm release
metadata and history belong to `packages/typescript/package.json` and
`packages/typescript/CHANGELOG.md`; existing tag, verification, and trusted
publishing gates apply only to that package. C uses the independently gated
`c-vVERSION` source-release workflow; registry submissions are separate.
