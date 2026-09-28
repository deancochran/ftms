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
