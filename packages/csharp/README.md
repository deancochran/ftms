# DeanCochran.Ftms

**Pure managed Bluetooth Fitness Machine Service protocol library for .NET.**

**[0.1.0-alpha.1 is published on NuGet](https://www.nuget.org/packages/DeanCochran.Ftms/0.1.0-alpha.1).**
The interface remains an evolving prerelease.

```sh
dotnet add package DeanCochran.Ftms --version 0.1.0-alpha.1
```

## Scope

- Bidirectional Feature words and all five Supported Ranges.
- Bidirectional treadmill, cross trainer, step climber, stair climber, rower and
  indoor bike measurements, with exact raw values and physical-unit projections.
- All 21 Control Point requests, responses, Training Status and Machine Status.
- Explicit range inspection and independent compatibility-format selections.
- Static capability interpretation, including uncertain/contradictory evidence,
  duplicate observations, conditional Feature properties and operation reports.

Targets **`netstandard2.1`** and **`net10.0`**, with no runtime package dependencies.
Inputs use `ReadOnlySpan<byte>`; encoders return fresh arrays or write to caller
spans after validation. Retained bytes and collections are defensively copied.

## Decode a measurement

```csharp
using DeanCochran.Ftms;

var result = MeasurementCodec.TryDecode(MeasurementKind.IndoorBike,
    new byte[] { 0x44, 0x00, 0x10, 0x0e, 0xb4, 0x00, 0xfa, 0x00 });
if (result.Success)
{
    var measurement = result.Value!;
    System.Console.WriteLine(measurement.Normalized.SpeedMetresPerSecond); // 10
    System.Console.WriteLine(measurement.Normalized.CadenceRpm);           // 90
    System.Console.WriteLine(measurement.Normalized.PowerWatts);          // 250
}
```

These are synthetic bytes, not a device capture. A successful raw decode can
still contain truncation or other diagnostics: inspect `measurement.Diagnostics`.
An absent raw field was not read; a present field with a null value is an explicit
unavailable sentinel, not zero.

## Build and verify from source

Run from `packages/csharp/` with the SDK pinned in `global.json`, Python 3.10+,
Git, and Bash (Git Bash on Windows). A virtual environment is recommended for the
test-only schema validator:

```sh
python3 -m pip install -r verification/requirements.txt
bash verification/verify.sh
```

This runs native unit tests, canonical conformance, the independent structural
matrix, local packing, portable-symbol/Source Link metadata checks and isolated
installed consumers of both target assemblies. Artifacts and evidence are written
under ignored `artifacts/`. No command publishes or operates equipment.

On a Linux x64 host with the .NET NativeAOT compiler prerequisites installed:

```sh
FTMS_VERIFY_AOT=1 bash verification/verify.sh
```

`VERSION` is the sole package-version authority. After verification, a local
consumer can restore from the absolute `artifacts/packages` directory:

```sh
dotnet add package DeanCochran.Ftms --version 0.1.0-alpha.1 --source /absolute/path/to/artifacts/packages
```

## Boundaries and evidence

There is **no BLE stack, connection lifecycle, timer, logging, UI framework, control
ownership or execution authorization** in this library. Capability prerequisites
being satisfied does not authorize transmitting a command or moving equipment.
Fragment planning/assembly is outside this initial package.

Linux host verification does not prove Windows/macOS CI execution, Unity/IL2CPP,
MAUI mobile runtime compatibility, real-device interoperability or Bluetooth
qualification. A .NET Standard target is an integration opportunity, not a tested
Unity claim. Classic .NET Framework is not supported by these targets.

Source-checkout documentation:

- [Interface and units](https://github.com/deancochran/ftms/blob/main/packages/csharp/docs/api.md)
- [Coverage](https://github.com/deancochran/ftms/blob/main/packages/csharp/docs/coverage.md)
- [Verification and exact evidence](https://github.com/deancochran/ftms/blob/main/packages/csharp/docs/verification.md)
- [Release prerequisites](https://github.com/deancochran/ftms/blob/main/packages/csharp/docs/releasing.md)

Those repository links identify intended main-branch locations.
