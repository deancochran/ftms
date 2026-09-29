# Explicit FTMS wire compatibility selections

Some deployed equipment has been reported with layouts that differ from the
historical FTMS characteristic tables. A caller may explicitly select one of
the formats below independently for ranges, measurements, and commands. These
selections are not inferred from a manufacturer, model, feature bits, packet
length, or another selection. No empirical selection is the default.

| Area | default | explicit alternative | raw representation |
| --- | --- | --- | --- |
| Bike, cross-trainer, rower resistance measurement | unsigned 8-bit whole | signed 16-bit tenths | integer as selected on wire |
| Treadmill instantaneous/average pace | unsigned 16-bit | unsigned 8-bit legacy | integer as selected on wire |
| Supported Resistance Range | three unsigned bytes, divisor 1 | six bytes: signed16 minimum/maximum and unsigned16 increment, divisor 10 | integer numerators |
| Control Point resistance request | signed 16-bit tenths (ESR11 E8991 and existing API default) | unsigned 8-bit tenths (literal FTMS 1.0.1 Table 4.15, conflicting with E8991) | integer tenths |

The command selection is independent of all other selections. Status opcode
`0x07` remains signed16 tenths per Table 4.26, even with UINT8 commands. See the
[normative audit](../../docs/specification-audit.md) for source identities and
the unresolved resistance scale annotations in the current GSS. The historical
command default has direct ESR11 E8991 support. The retrieved 1.0.1 PDF and HTML
Table 4.15 still print UINT8; that conflict does not establish that the erratum
was revoked. The explicit UINT8 selection is not a universal correction.

The reported Star Trac observation motivates the measurement resistance option;
it is not a complete packet capture. The reported 32-byte treadmill packet
motivates retaining a pace-width option but does not validate a pace display
unit conversion. The KICKR CORE firmware 3.0.23 raw `2AD6` six-byte value
`00 00 64 00 01 00` establishes width only, not a display-scale interpretation.
Fixtures marked `capturedCharacteristic` therefore do not claim a validated
display unit. Callers retain profile and normalization policy outside raw codecs.

Normalized TypeScript measurement parsing accepts the same explicit measurement
selection. Signed resistance is normalized from the selected signed-tenths wire
integer. A selected legacy treadmill pace consumes its one raw byte but leaves the
seconds-per-500m normalized fields null because its display unit is unknown; use
the raw decoder to retain that number. C intentionally retains selected raw
integers. C planning and its format-aware receive assembler apply one selected
profile consistently for a record lifetime. The legacy C assembler APIs remain
historical-layout only; separate format-context APIs copy an explicit profile at
initialization and never infer one from fragment bytes.

## Preserving capability interpretation context

Range inspection is an additive companion, not a replacement for capability
evaluation. Save the range kind, explicit options and inspection alongside the
unchanged capability report; pass the same options to both APIs. Inspect only
bytes from a successful read, not fabricated empty values for failed reads.
Discovery absence, read failure and selected-layout incompatibility are different
observations. Candidate success must not silently override the selected profile
or change a capability-v1 report. New inspection results do not retain input byte
buffers; retain original bytes separately if needed for diagnostic replay.

## Additive range inspection diagnostics

`inspectFtmsRangeRaw` and C `ftms_inspect_range[_with_format]` report the
caller-selected profile, observed and expected byte counts, selected structural
result, and raw candidate values. Resistance reports its two bounded layout
candidates (`uint8Whole`, `signed16Tenths`); other ranges report their one
canonical layout. A valid candidate does **not** select a profile, prove a
physical unit, prove device conformance, or grant control permission. The
selected decode remains malformed when its length or range check fails, even if
the other resistance candidate succeeds. Inputs remain caller-owned and the
inspection result contains no retained byte pointer.
