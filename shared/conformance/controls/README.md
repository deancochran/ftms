# Bidirectional Control Point corpus v1

This language-neutral corpus covers request encoding/decoding and response
encoding/decoding. It is additive to, and does not change, the immutable codec-v1
assets or npm exports. Basis: adopted FTMS 1.0 Control Point procedures, ESR11's
signed 16-bit / 0.1 resistance correction, and governing EC23224 provenance in
`../v1/vectors.json`. It is regression evidence, not control authorization or
Bluetooth qualification.

## Representation and comparison

Each request has its wire opcode and ordered raw-integer `operands`, plus literal
wire `bytes`. An optional request-case `format` explicitly selects
`signed16Tenths` (the omitted/default profile) or `uint8Tenths`; it applies only
to opcode 04 resistance and is not a decoded field or a response property. ESR11
Part II p.184 E8991 corrects the default command field from UINT8 to SINT16 while
retaining tenths. `uint8Tenths` is therefore an explicit alternative profile for
the literal 1.0 table, not an inferred or universally normative default.
Valid formatted request fixtures must have decoded opcode 04. Invalid request
fixtures may retain an explicit format while testing malformed bytes (including
missing or invalid opcode bytes); response fixtures never accept a request format.
The production APIs deliberately accept valid options for unrelated opcodes
without changing them, but these are not format-specific valid corpus cases.
Opcodes 0, 1, 7 have no operands. Other operands are:

| Opcode (hex) | Raw operands in wire order |
| --- | --- |
| 02 | speed, 0.01 km/h (u16) |
| 03 | inclination, 0.1 percent (s16) |
| 04 | resistance, 0.1 level (s16 default; explicit `uint8Tenths` profile is u8) |
| 05 | power, watts (s16) |
| 06 | heart rate, bpm (u8) |
| 08 | stop=1 / pause=2 |
| 09, 0a, 0b | energy kcal / steps / strides respectively (u16) |
| 0c | distance, metres (u24) |
| 0d | training seconds (u16) |
| 0e, 0f, 10 | 2, 3, 5 zone durations in seconds respectively (u16 each) |
| 11 | wind speed 0.001 m/s (s16), grade 0.01 percent (s16), rolling resistance 0.0001 (u8), wind resistance coefficient 0.01 (u8; unitless in FTMS 1.0.1 E10187, kg/m wording in 1.0) |
| 12 | wheel circumference, 0.1 mm (u16) |
| 13 | spin-down start=1 / ignore=2 |
| 14 | cadence, 0.5 rpm (u16) |

Response fields preserve raw `requestOpcode` and `resultCode`, `parameter` (0 none,
1 spin-down speeds), raw `low`/`high` speeds in 0.01 km/h, and integer diagnostic
flags `unknownRequest`, `unknownResult`, `unexpectedParameters`. Unused low/high
values are zero. Generic non-spin trailing data is evidence with a diagnostic,
not an invented parameter. Successful spin-down responses are three bytes
(Ignore) or seven bytes (Start speeds); other successful spin-down lengths fail.
Unknown result values are retained on decode but rejected on encode. An unknown
request opcode may be encoded in an Op Code Not Supported response.

**Two views are intentional:** this corpus compares raw response evidence. The
older codec-v1 *validated-response* view projects `unknownRequest` or
`unexpectedParameters` to `malformed_response`; it preserves unknown result codes
with `reserved_value`. That projection uses actual decoder output flags, never
input bytes or fixture expectations to manufacture a failure. The raw corpus
independently checks every retained value and diagnostic.

Validate the strict JSON schema and globally unique IDs before running. Compare
complete normalized objects recursively: exact keys, ordered arrays, integer
values/types, strings and bytes; no tolerance or subset matching. Literal
expectations are authored independently of a codec. Host bridge conversion
failures are runner failures, not native codec error outcomes. Invalid vectors
use `kind`, `length`, or `range` native errors (C values 3, 2, 4 respectively).

## Accounting and identity

There are 41 fixtures (27 requests, 6 responses, 8 invalid decodes) and 72
directional assertions. Every valid request is independently encoded and decoded.
Two response fixtures explicitly specify `encode: false`: unknown result and
unexpected trailing parameters are decode-only evidence, not canonical encoder
inputs. Invalid vectors assert decode rejection. These declared direction scopes
are not skipped assertions or an encoder-completeness claim.

Report case/category counts separately from assertion counts, every ID/direction
outcome and failure reason, unsupported/skipped counts, runner errors, source Git
HEAD/dirty state, and SHA-256 of schema, vectors and this README. Only a nonempty,
fully executed error-free run is complete. Schema version 1 names this contract,
not a package version or FTMS revision. Each port owns its runner and reads these
canonical files directly without depending on another port's tools.
