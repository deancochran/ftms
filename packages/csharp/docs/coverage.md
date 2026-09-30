# C# coverage

Local `0.1.0-alpha.1` source candidate; **not published on NuGet**.

| Area | Decode | Encode | Notes |
| --- | --- | --- | --- |
| Feature words | Yes | Yes | Raw unknown bits retained |
| Five Supported Ranges | Yes | Yes | Exact integers, units, scales; explicit resistance formats |
| Six measurement families | Yes | Yes | More Data, direction, optional fields, sentinels and diagnostics |
| 21 Control Point requests | Yes | Yes | Exact operand widths and independent resistance selection |
| Control Point responses | Yes | Yes | Spin Down speeds; unknown evidence diagnosed; canonical encode rules |
| Training Status | Yes | Yes | Raw text retained, strict UTF-8 diagnostics and UTF-16 encoder validation |
| Machine Status | Yes | Yes | Known parameter mappings, unknown opcodes and partial evidence |

Source profile: **`FullWire`**, plus `RangeInspection`, `CapabilityEvidence` and
`NormalizedViews`. This is a source/host-test claim, not a released-package claim.
Interfaces are idiomatic C# and do not duplicate every other port's convenience API.

Excluded: `RecordPlanning`, `RecordAssembly`, BLE transport, scheduling, ownership,
control procedure management, UI integration, live-equipment safety and qualification.

See [verification](verification.md) for exact corpus accounting and evidence limits.
