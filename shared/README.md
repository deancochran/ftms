# Shared FTMS assets

This is the language-neutral layer, independent of ports and their tooling.
Dependency flow is **ports and build/test tools → shared definitions and
fixtures**, never the reverse. Nothing here requires npm, a language-specific
package, a native toolchain, BLE, or an OS lifecycle API.

- [protocol/capability-discovery.md](protocol/capability-discovery.md) describes
  static protocol interpretation rules and acceptance scenarios. The unreleased
  C interpreter implements them without BLE or control authorization.
- [conformance/v1/schema.json](conformance/v1/schema.json) and
  [conformance/v1/vectors.json](conformance/v1/vectors.json) are the canonical
  versioned codec regression corpus. Fixtures are executable expectations and
  provenance, not the specification itself or proof of Bluetooth qualification.
- [conformance/README.md](conformance/README.md) defines the v1 runner,
  comparison, case-accounting, and corpus-identity contract. It is authoritative
  for ports consuming these fixtures.
- [conformance/capabilities/v1](conformance/capabilities/v1/) is a separate,
  versioned static-capability corpus; it does not extend codec conformance v1.

The v1 corpus bytes and historical schema identity are preserved during this
relocation, including `/v0.2.0/conformance/v1/schema.json`. A new filesystem
location does not create a new corpus version or change published npm exports.
Capability fixtures have their own explicitly versioned schema and
[comparison contract](conformance/capabilities/README.md), rather than silently
extending codec v1. They are not part of the existing npm conformance exports.

Each port should read this corpus from a pinned checkout/tag with its own test
runner, without installing another port. Do not independently maintain copies.
TypeScript's package-owned build script stages distribution snapshots into
`packages/typescript/conformance/v1/` solely to preserve npm content paths.
Language-specific scripts and manifests belong to their packages; root configs
orchestrate the repository. Shared tooling belongs in a future `tools/` only
when there is real reusable implementation to own.
