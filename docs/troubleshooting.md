# Troubleshooting

| Symptom | Check | Next step |
| --- | --- | --- |
| Import fails in Node | Check runtime, module format and installed version | Use Node 20+ and the package root. From 0.5.0, ESM `import` and CommonJS `require` are supported; earlier versions require ESM. Run the isolated quickstart |
| TypeScript reports missing APIs | Installed version may differ from main | Check the installed manifest and [release matrix](released-packages.md); do not import private source files |
| Browser packet decodes nonsense | A DataView may cover only part of its buffer | Preserve `byteOffset` and `byteLength`; see [transport recipes](transport-recipes.md) |
| React Native value is a string | BLE library may expose base64 | Convert using the documented transport contract; do not treat it as UTF-8 or pass it directly to the parser |
| Metric is `null` | Field absent, unavailable sentinel, or incomplete payload | Inspect flags and diagnostics; do not replace missing values with zero or stale data |
| Values differ by a constant factor | Wire and normalized units differ | Check public type/header units; C cadence may be a 0.5-rpm numerator while normalized TypeScript uses rpm |
| Decoder reports truncation | Advertised fields exceed the received bytes | Preserve the actual received span and inspect diagnostics; report a sanitized minimal packet if reproducible |
| Extra bytes or unknown flags appear | Device or protocol variation, wrong characteristic, or unsupported fields | Check dispatch and documented profiles; do not silently guess a format from length |
| Feature decode fails | Invalid length is not a zero feature declaration | Preserve malformed evidence separately from absent/unsupported capabilities |
| Encoder rejects a target | Out-of-bounds, wrong scale/grid, invalid options | Check API numeric rules and machine range/increment separately; do not clamp silently |
| Valid request is rejected by equipment | Encoding does not establish ownership or supported execution | Debug the host procedure, matching indication, capabilities, ranges, security and user authorization |
| Connection, permission or reconnection fails | These are transport/application concerns | Reproduce with the transport library's own diagnostics; this package cannot connect a device |
| CMake cannot find `ftms` | `find_package` does not download dependencies | Install first, then pass the correct `CMAKE_PREFIX_PATH`; see [C quickstart](../examples/c-client/README.md) |
| C++ link fails | C/C++ ABI or build configuration mismatch | Compile the library as C99, use its linkage-guarded public headers and the installed target |

## Useful bug reports

Include package version, runtime/compiler, characteristic UUID or explicit C kind,
format options, expected result, actual diagnostics, and the smallest sanitized
byte sequence that reproduces the issue. Distinguish synthetic bytes from a real
capture and say whether the package came from a registry, archive or local build.

Do not post credentials, device addresses/identifiers, personal activity records,
or unreviewed raw logs. Suspected security problems belong in the
[private reporting channel](../SECURITY.md), not a public issue.

Run the [TypeScript](../examples/typescript-quickstart/README.md) or
[C/C++](../examples/c-client/README.md) host example first. Passing it narrows the
problem; it does not establish device compatibility or safe physical controls.
