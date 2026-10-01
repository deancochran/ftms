# Choose a language

<a id="ftms-packages"></a>

All nine packages implement FTMS protocol bytes without owning your Bluetooth
connection. Choose the language used by your application; do not choose by tag
spelling or assume matching package versions imply identical convenience APIs.
Integrate each package through the project-wide
[consumer adapter seam](../docs/architecture.md#consumer-adapter-seam): native
transport conversion, session lifecycle, application policy and control safety
remain consumer-owned.

## Install and decode your first packet

Use the [installation directory](../docs/install.md) for latest-selection commands
and the verified concrete dependencies required by C, Swift and Kotlin. Repository
verification examples remain pinned; they are not a requirement to start new apps
on an old version.

Follow your language's guide for the published dependency, a decoding example,
and its actual value/error representation. TypeScript and C also have runnable
installed-consumer quickstarts. No equipment connection is required for those examples.

| Language | Install and start | Package guide / API entry point |
| --- | --- | --- |
| C | [Installed-library quickstart](../examples/c-client/README.md) | [C guide](c/README.md); [installation options](c/INSTALL.md) |
| C# | [Install and decode](csharp/README.md) | [API reference](csharp/docs/api.md) |
| Dart | [Install and decode](dart/README.md) | [Dart guide](dart/README.md); [Flutter integration](dart/doc/flutter_integration.md) |
| Go | [Install and decode](go/README.md) | [Go guide](go/README.md) |
| Kotlin/JVM | [Install and decode](kotlin/README.md) | [Kotlin and Java examples](kotlin/README.md) |
| Python | [Install and decode](python/README.md) | [Python guide](python/README.md) |
| Rust | [Install and decode](rust/README.md) | [Rust guide](rust/README.md) |
| Swift | [Install and decode](swift/README.md) | [Swift guide](swift/README.md) |
| TypeScript | [Installed-package quickstart](../examples/typescript-quickstart/README.md) | [TypeScript guide](typescript/README.md) |

## Understand the result

- Check each guide's units: raw wire integers are not necessarily display units.
- Treat missing values, malformed input and unknown fields according to that
  package's documented contract, not another language's return types.
- A capability report is evidence, not permission to operate equipment.
- Keep discovery, security, connection lifecycle and control safety in the application.

See [current verified releases](../docs/released-packages.md) for exact published
versions and prerelease status. The [1.0 milestone](../docs/release-1.0.md) is a
preparation checklist, not an available package family.

## Next steps

- [API references by language](../docs/api.md)
- [TypeScript and C cookbook](../docs/integration.md)
- [Transport recipes: JavaScript and C](../docs/transport-recipes.md)
- [Consumer adapter seam](../docs/architecture.md#consumer-adapter-seam)
- [Support profiles](../docs/support-profiles.md) and [protocol coverage](../docs/coverage.md)
- [Troubleshooting](../docs/troubleshooting.md)

## Working on a port

Start with [contributing](../CONTRIBUTING.md), [architecture](../docs/architecture.md)
and the [conformance runner contract](../shared/conformance/README.md).
Sources, manifests, tests and language-specific tooling remain package-owned;
ports consume canonical shared assets rather than other ports or fixture copies.
The root pnpm workspace verifies TypeScript and the site, not native packages.
SwiftPM's thin root `Package.swift` is an ecosystem-required entry point into
package-owned Swift sources. See the [release process](../docs/releasing.md) for
each port's independent runbook and gates.
