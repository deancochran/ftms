# Documentation

<a id="start-here-humans-and-coding-assistants"></a>

## Start here

1. [Understand FTMS](ftms-explained.md): protocol bytes, units, and what the libraries do.
2. [Choose a language](../packages/README.md): install and decode using any of the nine ports.
   [Installation and upgrades](install.md) distinguishes latest selection from reproducible pins.
3. Check [current releases](released-packages.md) and prerelease status before choosing a dependency.
4. Find your [API reference](api.md), then consult the
   [TypeScript and C cookbook](integration.md) or your package's examples.
5. Keep the [consumer adapter seam](architecture.md#consumer-adapter-seam) explicit,
   then use the [JavaScript/C transport recipes](transport-recipes.md) where applicable.
   Consult [troubleshooting](troubleshooting.md) for diagnostics.

Keep Bluetooth discovery, timing, permissions, session ownership and physical
control safety in your application. A valid request or capability report is not
authorization to execute a command.

<a id="reference-and-contracts"></a>

## Reference and compatibility

- [API references by language](api.md)
- [Support profiles](support-profiles.md): definitions of wire roles and optional modules
- [Protocol coverage](coverage.md): implementation and verification scope
- [Versioning](versioning.md): package compatibility, protocol and corpus identities
- [Capability evidence contract](../shared/protocol/capability-discovery.md)
- [Wire compatibility](../shared/protocol/wire-compatibility.md) and [numeric inputs](../shared/protocol/numeric-inputs.md)

## Releases

- [Current public packages and exact release evidence](released-packages.md)
- Package-owned changelogs describe changes; publication records establish artifact identity.
- [Planned 1.0 milestone](release-1.0.md): preparation status, not a published release

Migration guidance will be based on reviewed interface differences, not inferred
from the target version. Current installation commands remain valid until a new
public artifact is verified.

<a id="evidence-not-installation-instructions"></a>

Historical records are indexed in [Audits and evidence](evidence.md); they are not
current installation instructions.

<a id="maintainers-and-contributors"></a>

## Contributors and maintainers

- [Contributing](../CONTRIBUTING.md), [architecture](architecture.md), [roadmap](roadmap.md), [security](../SECURITY.md)
- [Conformance runner and corpus accounting](../shared/conformance/README.md)
- [Release process and per-port runbooks](releasing.md)
- [Equipment testing](equipment-testing.md) and [simulation](simulation.md)
- [Historical audits and evidence](evidence.md)
- [Documentation site development and deployment](../site/README.md)

Public integration does not require a repository checkout or private specification
context. Exported declarations and public headers remain package-owned references;
the site also publishes generated TypeScript API documentation.
