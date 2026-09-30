# C# codec conformance runner

This console adapter exercises the public C# library against canonical shared
fixtures. It does not contain production codecs or generate expectations from
actual results. Encoder inputs come from literal fixture values; decoder inputs
come from literal fixture bytes.

From `packages/csharp/`:

```sh
dotnet run --project verification/CodecConformance -c Release -- artifacts/codec-conformance.json
```

The runner executes 97 immutable codec-v1 cases and 131 additive cases: values,
controls, measurements, statuses, compatibility and range inspection. The current
corpus results in 330 comparisons, not 330 distinct cases. Case IDs and required
directions are discovered first; unexecuted directions are recorded explicitly if
an adapter fails. The report includes per-case outcomes, per-comparison outcomes,
category totals, source state and exact fixture/comparison-contract hashes.

Exact comparison rejects extra/missing keys, mistyped values and reordered arrays.
Legacy comparison follows the prescribed subset/tolerance semantics. The package
verifier separately performs JSON Schema validation, capability conformance and
the independent measurement matrix. All of these checks are required together.

`FtmsAssembly` can select a prebuilt reference for isolated runner development;
normal verification references the package project. Package-installation checks
also compile these same runner sources against the installed Standard DLL rather
than a source project or silently selected modern assembly.
