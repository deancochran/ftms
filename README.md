# FTMS protocol project

Transport-independent codecs and shared protocol design for the Bluetooth
Fitness Machine Service (FTMS). Implementations interpret bytes; applications
own Bluetooth discovery, connections, control permission, and physical safety.

## Current support

Start with the [released-package status and examples](docs/released-packages.md).
The [TypeScript example](examples/typescript-client/README.md) works with the
published npm 0.2.0 package; the [C example](examples/c-client/README.md) currently
uses a clearly labelled local source candidate. There are **no recorded
real-equipment interoperability results**; see the [test procedure and evidence
requirements](docs/equipment-testing.md).

[TypeScript / JavaScript](packages/typescript/README.md) is the only published
package, released as `@deancochran/ftms` (currently `0.2.0`). It provides codecs
for all six FTMS machine-data families, features, supported ranges, statuses,
and Control Point requests/responses. See its README for installation and API
usage and its [changelog](packages/typescript/CHANGELOG.md) for releases.

C/C++ has unreleased bidirectional C99 codecs for Features, ranges, all six
measurement families, Control Point and statuses, plus static
capability evidence interpretation. Swift and Kotlin/Java remain README-only
design scaffolds. No native package is
released. Native CI and release workflows are configured in source; remote runs
and publication are separate gates. See the C [verification record](packages/c/docs/verification.md).
Aggregate capability interpretation remains unreleased and static-only. Unit tests and shared
regression vectors do not establish real-device interoperability, PTS results,
or Bluetooth qualification.

## Layout and dependencies

| Location | Ownership |
| --- | --- |
| [shared/](shared/README.md) | Language-neutral protocol definitions/design and versioned conformance fixtures |
| [packages/typescript/](packages/typescript/README.md) | npm API docs, changelog, sources, tests, compiler configs, and npm-specific scripts |
| [packages/c/](packages/c/README.md) | Unreleased C99 feature/range decoding and static capability evidence, consumable from C++ |
| [packages/swift/](packages/swift/README.md) | Future independent native Apple package |
| [packages/kotlin/](packages/kotlin/README.md) | Future independent Kotlin/JVM package, consumable from Java/Android |
| [docs/](docs/architecture.md) | Repository-wide [architecture](docs/architecture.md), [coverage](docs/coverage.md), and [versioning](docs/versioning.md) guidance |
| [examples/](examples/README.md) | Future integration examples outside protocol cores |
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
publishing gates apply only to that package. Native publishing requires a
 separate implementation and release design.
