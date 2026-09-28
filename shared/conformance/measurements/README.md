# Measurement raw conformance corpus

This language-neutral corpus pins a raw-integer measurement representation.
`values` follows the exact 30-field `fieldOrder`; `present` and `unavailable` are
bit masks indexed by that order. Decoding compares complete objects exactly. Encoding
uses the decoded kind, flags, masks, and all 30 raw integers; unavailable values are
intentionally ignored by the encoder and vectors use zero there for canonical input.

This is separate from immutable codec-v1. The six `equipment-*-all-fields`
fixtures are literal FTMS wire-unit golden values independently transcribed from
the published field widths, signedness, and divisors; they cover every field of
each equipment kind in both directions. It also covers More Data fragments and
diagnostics, but does not claim BLE, device, or qualification evidence.

Kinds are 0 Treadmill, 1 Cross Trainer, 2 Step Climber, 3 Stair Climber, 4 Rower,
5 Indoor Bike. Flags retain the wire bit word. `moreData`, `backward`, `truncated`,
`trailingBytes` and `reservedFlags` are integer 0/1 diagnostics. `bytesRead` is
the offset after complete fields, not an incomplete field's supplied bytes.
Unknown flags remain on decode but encoders reject them. More Data is retained;
no fragment reassembly is performed. The raw `present` mask distinguishes fields
whose complete bytes were decoded from absent/incomplete fields; `unavailable`
is a subset marking defined wire sentinels. Unavailable raw values normalize to
zero. Encoders require exactly the fields selected by flags, not extra/missing
present bits. Field widths and flag groups follow the adopted FTMS layouts.

Wire units: speed/average speed 0.01 km/h (divide raw by 360 for m/s); cadence and
stroke rates 0.5 per minute; inclination/ramp angle/MET /10; Cross Trainer stride
count /10 but Stair Climber stride count whole; Treadmill elevation /10 metres
but other elevations whole metres. Distance, pace, energy, time, resistance,
power, heart rate and other counts are whole units. Signed unavailable `0x7fff`
applies only to inclination/ramp and Treadmill force/power. Energy uses `0xffff`
or `0xff`, and Cross Trainer step rates use `0xffff`. Bike/Rower/Cross Trainer
power **+32767 is valid**, as are all representable extrema of fields without a
sentinel. Negative signed minima remain valid.

Codec-v1's normalized metric projection differs from raw evidence: selected but
unread fields in a truncated packet become null metrics, derived from actual
decoded flags, kind, present bits and truncation. Unavailable complete fields
also become null. This does not change the raw presence/availability contract.

The current corpus has 26 cases / 47 directional assertions. Decode-only cases
carry explicit reasons for malformed/partial/unknown-flag evidence; they do not
claim canonical encoding. Validate strict schema and unique IDs, then compare
entire normalized objects (exact keys/types/array order/integers, no tolerance).
The original codec-v1 adapter separately uses its existing numeric subset rules.
Report every case/direction outcome, counts, non-pass reasons, runner errors,
source HEAD/dirty state and SHA-256 of schema, vectors and this README. A
nonempty, fully executed error-free run alone is complete. Format version is not
package or specification version. Specification/errata provenance is inherited
from `../v1/vectors.json` (FTMS 1.0, ESR11, EC23224); no port is the oracle.
