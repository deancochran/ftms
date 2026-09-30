# Static capability interpretation

`InterpretCapabilities(CapabilitySnapshot, CapabilityOptions)` implements the
language-neutral `shared/protocol/capability-discovery.md` contract. It performs
no I/O, owns no discovery cache, and never grants physical-control permission.

## Input ownership and construction

The caller selects one FTMS service instance and one discovery generation, then
supplies `Scope`, `Discovery`, `Generation`, and `Characteristics`. Every observation
has a full `UUID`, all 16 property-mask bits, a `ReadState`, a normalized failed-read
`Reason`, and raw `Bytes`. UUIDs are in canonical display/network order, not BLE
little-endian UUID order. `UUID16(0x2acc)` expands the assigned number into the
complete Bluetooth base UUID; arbitrary lookalikes are never truncated to 16 bits.

Use `PropertyRead`, `PropertyWrite`, `PropertyNotify`, and `PropertyIndicate` masks
when describing known properties. Unknown property bits remain visible and are
diagnosed on known characteristics, rather than silently discarded.

Bytes must be empty unless the read succeeded. A reason other than `ReasonNone`
is permitted only for `ReadFailed`. An empty successful read is a valid snapshot
input but malformed Feature/range evidence. Invalid enum values, invalid read
combinations, or invalid options return `ErrKind` with a zero report. These API
errors differ from ordinary incomplete/contradictory protocol evidence.

The function does not mutate or retain input byte slices. Do not mutate input
during evaluation. Every returned observation slice, diagnostic slice and range
value is independently owned; modifying one report does not alter input or another
report. Observation indices refer back to the original snapshot. Preserve that
snapshot if raw bytes will be needed later.

## Reading the report

- `Presence` retains unique, duplicate, absent and unknown states for every known
  characteristic kind. Slot `KindUnknown` is always unknown; inspect individual
  observations for unknown UUIDs.
- `Feature` separates presence, decoding and raw words. Raw/unknown masks remain
  available after valid decoding even when properties contradict the specification.
- `Ranges` are indexed by `RangeKind`: speed, inclination, resistance, **heart
  rate, power**. Non-nil values retain exact numerators, scale divisor and unit.
- `Operations` are indexed by wire opcode `0x00`–`0x14`. Their target-bit order
  differs from range order: target bit 3 is power, bit 4 is heart rate.
- `Diagnostics` are stable ordered evidence reasons with an optional input index.
  Check `HasInputIndex` before using an index; zero alone does not imply availability.

An operation has independent `Declaration` and `Prerequisite` states plus a
bitmask of `CapabilityReason*` flags. Inconsistency takes precedence over
incompleteness, while reason flags retain both when applicable. Unknown target
declarations do not invent required ranges. Optional wheel-circumference and
spin-down procedures retain their table metadata and still use their feature bits.

Confirmed complete absent service with no observations establishes not-supported
operations. Unknown/ambiguous scope does not decode evidence or invent support.
Contradictory absent scope does not become supported merely because bytes exist.
Observed presence remains visible in all scopes. Duplicate known characteristics
are ambiguous even if their bytes are identical; none is preferred for decoding.

## C.7 evidence is not connection security

`C7` has two independent `Truth` inputs: `BondingSupported` and
`FeatureMayChangeOverLifetime`. Their zero values mean unknown.

- Both true: Feature requires Read **and** Indicate.
- Either false: Feature requires Read and excludes Indicate.
- Otherwise: only the Read/Indicate ambiguity remains unresolved. Report
  `DiagnosticInsufficientC7` and incomplete prerequisites, while still rejecting
  missing Read and unrelated extra properties.

The caller must supply actual evidence; do not set false just to obtain a satisfied
result. These inputs do not assert that this connection is bonded or encrypted.
Base Control Point procedures still require valid Feature presence/properties,
but unlike target procedures do not require a successful Feature read.

## Explicit resistance-range layout

The default uses the three-byte whole-level range. To evaluate an explicitly
selected signed tenths range, pass:

```go
options := ftms.CapabilityOptions{
    Range: ftms.RangeOptions{Resistance: ftms.ResistanceSint16Tenths},
}
```

This changes only resistance-range decoding, not the other four ranges,
measurement layouts or Control Point operands. Retain the chosen options with
the snapshot/report. The shared 63 cases use the canonical default; native tests
add explicit alternate-layout and mixed-range coverage.

## Verification and limits

The schema-validated 63-case corpus is executed by the tagged conformance suite.
All full normalized reports are compared exactly. The output records all four
contract hashes, category totals and every case outcome. `example_test.go` contains
an executable public-interface example, and the isolated module consumer runs
capability interpretation without Python or sibling fixtures.

Even `DeclarationSupported` plus `PrerequisiteSatisfied` does **not** authorize
control. Security, subscriptions, current ownership, response matching, timeouts,
connection lifetime and physical safety remain caller responsibilities. There is
no `canExecute` field. No device interoperability or Bluetooth qualification is
implied by the host corpus.
