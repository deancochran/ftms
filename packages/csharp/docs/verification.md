# C# verification evidence

## Published alpha.1

NuGet **`DeanCochran.Ftms` 0.1.0-alpha.1** is now published and verified. The
[canonical release record](../../../docs/released-packages.md#published-prerelease-c-010-alpha1)
contains the exact clean source, corrected recovery-tooling identity, public hashes
and successful Linux/macOS/Windows release run. Public consumers executed both
target assemblies, and the NuGet repository signature/payload comparison passed.
This supersedes the initial local-only publication and CI limits below, not their
remaining Unity/MAUI/real-device/qualification exclusions.

## Initial local development evidence

Verified locally on Linux x64 with .NET SDK **10.0.100** and .NET runtime **10.0.0**.
Source base: `accc347f12d1244b24f2e8a422627cca0dad2763` plus the uncommitted C# work;
generated reports explicitly record `dirty: true`. This is not clean-release evidence.

## Executed checks

| Check | Observed result |
| --- | --- |
| Release builds | `netstandard2.1` and `net10.0`; zero warnings/errors |
| xUnit tests | 12 passed, including 2,080 deterministic malformed payloads across decoders |
| Capability ownership checks | 4 checks in the capability runner |
| Package safety tests | 3 Python tests for canonical versions, ZIP paths/duplicates and signature-only payload differences |
| Canonical schema validation | 7 schema/vector pairs passed |
| Codec v1 | 97 cases passed |
| Raw values | 8 cases / 16 directions |
| Raw controls | 41 cases / 72 directions |
| Raw measurements | 26 cases / 47 directions |
| Raw statuses | 38 cases / 63 directions |
| Compatibility | 9 cases / 18 directions |
| Range inspection | 9 cases / 9 reports |
| Capability v1 | 63 cases passed |
| Measurement matrix | 181,760 layouts, each encoded/decoded; 46 sentinels, 47 RFU cases, 315 incomplete prefixes |
| Local NuGet installation | Both target assemblies compiled and executed in isolated consumers |
| Installed Standard assembly | All codec, capability and matrix runners repeated against its packed DLL |
| Portable symbols | Both PDBs opened; nonempty Source Link metadata verified |
| NativeAOT | Packed `net10.0` library rooted for complete analysis; Linux x64 native consumer published locally and executed |

Codec/raw/inspection evidence totals **228 distinct fixture IDs**, with **330
comparisons**. This separates case accounting from encode/decode directions and
legacy metric/diagnostic comparisons. Capability evidence adds a separate **63**
IDs. Every executed suite has zero failures, unsupported cases and skipped cases.

Reports are generated under `artifacts/`, including separate installed-Standard
reports. The codec runner discovers fixture IDs before running codecs and records
unexecuted directions explicitly on failure. Capability templates are expanded
from independent deep copies. Expected values are not produced by the implementation.

## Exact identity and comparisons

- Codec schema: format 1, retaining its historical `$id` containing `v0.2.0`.
- Capability schema: format 1, `urn:ftms:capabilities:conformance:v1`.
- Structural matrix: `ftms-measurement-matrix-v1`.
- Each runner hashes the exact canonical schema, vector and comparison README files;
  capability identity additionally hashes `shared/protocol/capability-discovery.md`.
- The initial codec vector SHA-256 is
  `9b5b61353b191179cc629d8c459b2a185b9e03b7ce5f3f51b715520162e8a5c7`;
  capability vector SHA-256 is
  `90a9b85e735455515c36fc089fa786bd928e217e81cf95f5ccef67c0d479d3dd`.
- Full identity records, including comparison-contract hashes and source state, are
  in `codec-conformance.json`, `capability-conformance.json` and `matrix-conformance.json`.

Raw and capability comparisons are exact. Legacy codec-v1 follows its individual
comparison rules, including strict measurement tolerance `< 0.005`, subset status
expectations and diagnostic issue inclusion. No fixture is copied into this package.

## Reproduce

From `packages/csharp/`, with the pinned SDK on PATH:

```sh
python3 -m pip install -r verification/requirements.txt
FTMS_VERIFY_AOT=1 bash verification/verify.sh
```

Omit `FTMS_VERIFY_AOT=1` on hosts without native compiler prerequisites. Dependency
restore uses committed package lockfiles for the regular library/test/runner projects.
Framework/toolchain packs can be downloaded during isolated and AOT consumer checks;
FTMS package resolution is restricted to the exact local candidate feed.

## Limits

The added workflow configures Windows/macOS/Linux checks, but only Linux has been
executed in this local delivery. No remote CI was dispatched. No Unity, IL2CPP, MAUI,
mobile-device runtime, BLE exchange, physical-control safety or Bluetooth qualification
evidence is claimed. Standard conformance was executed on a .NET 10 host, not Unity.
Source Link metadata has been verified, not public availability of this uncommitted
source at its eventual release commit. No NuGet account or public package was changed.
