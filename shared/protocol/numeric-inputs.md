# Normalized numeric input policy

This policy applies to human-unit Control Point encoders, not raw integer
codecs. It does not change wire layouts, corpus fixtures or advertised ranges.

1. Require a finite number.
2. Let `s` be the integer number of wire increments per human unit (1, 2, 10,
   100, 1000 or 10000). Canonical normalized bounds are `minimumRaw / s` and
   `maximumRaw / s`, represented in the API's numeric type.
3. Check the **original input** against these inclusive bounds before rounding.
   Reject any outside value. Negative zero equals zero; a negative nonzero
   value is invalid for an unsigned operand.
4. Compute `scaled = input * s` and its nearest integer candidate. TypeScript
   binary64 accepts grid representation noise only when
   `abs(candidate - scaled) <= 2 * Number.EPSILON * max(1, abs(scaled))`.
   This explicit relative envelope is not general rounding or clamping.
   Half-step values are rejected, including negative ties.
5. Validate the integer candidate's wire bounds before writing bytes.

Speed `0.1 + 0.2` encodes as 30 hundredths of km/h; `1.005` and
`1.0100000005` are rejected as misaligned. UINT8-tenths resistance accepts 25.5,
but not 25.5000000005. Adjacent representable values outside bounds are rejected.
Raw operands have no tolerance: fractions, NaN and infinities are invalid.
C currently exposes integer operands, so needs no floating-point changes.

Future ports may use integer/decimal APIs instead of binary64. Preserve the
no-clamping/no-implicit-quantization rule and document any representation
tolerance before implementing normalized convenience APIs. This policy does
not authorize controls or replace caller validation against equipment limits.
