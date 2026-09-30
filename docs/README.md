# Documentation

## Start here: humans and coding assistants

1. Check the [release matrix](released-packages.md). Do not infer publication from a source version.
2. Run the [TypeScript quickstart](../examples/typescript-quickstart/README.md) or
   [C/C++ quickstart](../examples/c-client/README.md) against an installed artifact.
3. Select APIs using the [cookbook](integration.md) and [API index](api.md).
4. Connect your application's byte boundary using [transport recipes](transport-recipes.md).
5. Check expected outputs and diagnostics; use [troubleshooting](troubleshooting.md).

Prefer normalized TypeScript measurement parsers for application metrics; use raw
APIs for wire representations. C APIs use fixed-point integers. Keep BLE, timing,
session policy and physical control authorization in the application. Do not
create replacement codecs or import private source paths to complete these recipes.

## Reference and contracts

- [TypeScript package guide](../packages/typescript/README.md)
- [C package guide](../packages/c/README.md) and [installation](../packages/c/INSTALL.md)
- [API index and generated TypeScript reference](api.md)
- [Architecture](architecture.md), [coverage](coverage.md), [versioning](versioning.md)
- [Capability evidence contract](../shared/protocol/capability-discovery.md)
- [Wire compatibility](../shared/protocol/wire-compatibility.md) and [numeric inputs](../shared/protocol/numeric-inputs.md)
- [Conformance runner and corpus accounting](../shared/conformance/README.md)

## Evidence, not installation instructions

- [Adoption-readiness local verification](adoption-verification.md)

The following records describe specific historical runs. Their counts, source
identities and candidate versions are not automatically the current release:

- [Compatibility verification](compatibility-verification.md)
- [Boundary hardening verification](hardening-verification.md)
- [Cross-port parity](parity.md)
- [C verification record](../packages/c/docs/verification.md)
- [Equipment procedure](equipment-testing.md) and [passive pilot](equipment-results/2026-09-29-kickr-core-linux.md)
- [Deterministic simulation](simulation.md)

Host tests, synthetic traces, packet replay, live equipment observations and
Bluetooth qualification are separate evidence categories.

## Maintainers and contributors

- [Documentation website: develop, customize and deploy](../site/README.md)

- [Contributing](../CONTRIBUTING.md), [roadmap](roadmap.md), [security](../SECURITY.md)
- [TypeScript release guidance](../packages/typescript/README.md#release) and [C releases](releasing-c.md)

Public integration does not require private specification context, machine-local
agent instructions, or a repository checkout. The generated API reference is a
local convenience; exported declarations and public C headers ship with packages.
