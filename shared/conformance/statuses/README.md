# Bidirectional status corpus v1

Language-neutral, raw-integer evidence for Fitness Machine Status and Training
Status. Basis: adopted FTMS 1.0 status characteristics, ESR11 and governing EC23224
provenance from `../v1/vectors.json`. These additive fixtures do not change that
codec corpus or npm exports, and are not BLE/device/qualification evidence.

## Machine Status

Reports retain raw opcode, raw action (Stop/Pause or Spin Down Status), nullable
parameter, and integer flags `unknownOpcode`, `reservedValue`, `truncated`,
`trailingBytes`. A parameter is an opcode/ordered-operands object using the raw
units in the [control corpus](../controls/README.md). Status opcodes `05–09`
map to request opcodes `02–06`; statuses `0a–13` map to requests `09–12`, and
status `15` to request `14`. All numbers in this sentence are hexadecimal.
Stop/Pause status permits actions 1–2; **Spin Down Status permits 1–4**, unlike
the Control Point Spin Down request's 1–2 actions. Base statuses have null
parameters. Unknown opcodes are retained, not guessed into a known structure.

Truncated known parameters remain null with `truncated=1`. Empty input has
opcode zero, unknownOpcode=1, truncated=1: this is evidence, not a valid status.
The older codec-v1 view projects an unread status code to null rather than
treating zero-initialized native storage as a received value. Partial evidence
is a successful interpretation with diagnostics, not canonical encoder input.

## Training Status

Reports retain flags, code, text offset/size, integer flags textPresent,
extendedString, reservedValue, invalidFlags, invalidUtf8, truncated, trailingBytes,
and the raw `reservedFlags` bitmask. `textHex` is the actual span designated by the
decoded offset/size, never a guessed string. Strings are UTF-8; raw invalid text
is retained with diagnostics. Extended string requires string-present. Codes
0–15 are defined; other codes are retained with reserved-value evidence.

Encoder inputs use authoritative flags/code and explicit UTF-8 text, not decoded
offsets. It rejects RFU/invalid flags, reserved codes, invalid UTF-8 and diagnostic
states. No platform string object, allocator or arbitrary protocol string limit
is implied. The C bridge limits host input to 1024 bytes and fails on overflow;
the library accepts caller-bounded text with checked size/capacity arithmetic.

## Comparison, direction accounting and identity

Strict schema and unique IDs are required. Compare complete decoded objects:
exact keys, JSON types, ordered operands, raw integers/hex and diagnostics.
Encoding assertions use independent literal raw values and expected wire bytes,
not values produced by a decoder during the test. Decode-only malformed cases
are explicitly marked and are not encoder pass claims.

There are 38 fixtures: 28 Machine Status (all 22 defined opcodes plus diagnostics)
and 10 Training Status, yielding 63 directional assertions. Report case/category
counts separately from assertions, every ID/direction outcome, failures/reasons,
unsupported/skipped counts and runner errors. Identity includes HEAD/dirty state
and SHA-256 of schema, vectors and this README. Only a nonempty fully executed,
error-free run is complete. Schema format, FTMS revision and package versions
remain independent; each port consumes these files directly with its own runner.
