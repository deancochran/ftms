# Bidirectional Feature and Supported Range corpus v1

These language-neutral fixtures pair literal raw values with independently
reviewed wire bytes for both client decoding and equipment encoding. They are
additive to immutable codec-v1 and do not alter its assets or npm exports.
Basis: FTMS 1.0 Feature/Supported Range characteristics with the specification,
ESR11 and EC23224 provenance recorded in `../v1/vectors.json`.

Feature words are unsigned 32-bit values; unknown/reserved bits remain raw bits,
not inferred capabilities. Range minimum, maximum and increment are integer
numerators with explicit unit and divisor. Speed uses km/h /100, inclination
percent /10, resistance whole levels, heart rate whole bpm, power whole watts.
Units are numbered 0 through 4 in that order. Inclination/power bounds are signed
16-bit; their increments are unsigned 16-bit. Resistance/heart-rate values are
unsigned bytes; speed values unsigned 16-bit. Reversed bounds, zero increments,
out-of-width values and wrong unit/divisor pairs are rejected by encoders.

Validate strict schema and globally unique IDs. Each of the 8 cases (3 Feature,
5 Range) has **two** independent assertions: encode supplied raw values to the
literal bytes, then decode those literal bytes to the supplied complete raw
values. Compare every field, byte and length exactly; do not generate expected
values by invoking the codec or accept only a round trip. Native invalid-argument
and encoder-rejection cases are additionally exercised in port tests.

Report all case/direction outcomes, case/category totals separately from the 16
assertions, all non-pass reasons, unsupported/skipped and runner errors. Identity
includes source HEAD/dirty state and SHA-256 of schema, vectors and this README.
Only a nonempty, fully executed error-free run is complete. Corpus schema version
is independent from FTMS and package versions. This is host regression evidence,
not device or Bluetooth qualification evidence.
