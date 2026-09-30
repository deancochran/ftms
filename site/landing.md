# FTMS Protocol Libraries

## Your Bluetooth stack. Shared protocol foundations.

Replace handwritten Fitness Machine Service packet parsing with typed values,
explicit diagnostics, and bidirectional codecs. Build a fitness application,
embedded integration, or protocol tool without taking on another connection stack.

| Build with | What you get | Start |
| --- | --- | --- |
| TypeScript / JavaScript | ESM, normalized metrics, raw codecs and declarations | [Run the quickstart](../examples/typescript-quickstart/README.md) |
| C / C++ | Portable C99, fixed-point values, caller-owned memory | [Install the source archive](../examples/c-client/README.md) |

## A focused boundary

Decode measurements, features, ranges and statuses. Construct control messages.
Interpret capability evidence. Keep Bluetooth discovery, connections, permissions,
timeouts, procedure ownership and physical safety in your application.

**A valid packet is not permission to control equipment.** Host tests and shared
fixtures are evidence of tested behavior, not universal device compatibility or
Bluetooth qualification.

## Integrate with confidence

- [Cookbook](../docs/integration.md): choose the right public API for the task.
- [Transport recipes](../docs/transport-recipes.md): preserve the exact received byte span.
- [Releases and support](../docs/released-packages.md): distinguish source from published packages.
- [Protocol coverage](../docs/coverage.md): inspect tested scope and evidence limits.
- [Contributing](../CONTRIBUTING.md): report problems and improve the project.

MIT licensed. Created and maintained by Dean Cochran.
