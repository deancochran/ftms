# FTMS integration examples

These examples consume public installed packages. They contain no connection
attempts, device identifiers or control writes.

| Example | Purpose | Run |
| --- | --- | --- |
| [TypeScript quickstart](typescript-quickstart/README.md) | Recommended current-release entry; expected outputs and byte-boundary recipes | `npm install && npm test` in its directory |
| [C / C++ client](c-client/README.md) | Released archive, installed CMake target, assertions in both languages | Follow its download/install/build steps |
| [Historical TypeScript client](typescript-client/README.md) | Explicit 0.2.0 compatibility baseline, not the default quickstart | `npm install && npm test` in its directory |
| [C passive replay](c-passive-replay/README.md) | Offline capture replay; separate opt-in live-capture procedure | Follow its README; do not run capture implicitly |

Read the [release matrix](../docs/released-packages.md) before assuming a source
API is published. Features, ranges and successful encoders are not permission to
control equipment. See the [integration cookbook](../docs/integration.md).

Examples are host evidence, not Bluetooth qualification. The
[limited passive pilot](../docs/equipment-results/2026-09-29-kickr-core-linux.md)
records a separate real-equipment observation, not universal interoperability.
