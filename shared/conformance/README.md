# Conformance corpus contract

`v1/schema.json` and `v1/vectors.json` are the canonical, language-neutral FTMS
codec regression corpus. They are inputs to a port's tests, not an implementation
API, a universal runner, a substitute for the Bluetooth specification, or proof
of Bluetooth qualification. Expected values must be reviewed against the adopted
FTMS specification and applicable errata; TypeScript is a consumer of this corpus,
not its oracle.

Static capability fixtures live under `capabilities/v1/` with their own schema
and contract. They do not alter this codec-v1 comparison contract or historical
identity.

## Identity and versioning

The corpus currently has `schemaVersion: 1`. That names the JSON format and
comparison contract, not an FTMS specification revision and not a package version.
`v1` retains its historical schema `$id` ending in
`/v0.2.0/conformance/v1/schema.json`; moving the files did not alter that identity.
The content revision is a separately pinned source checkout/tag plus checksums of
both JSON files. The comparison contract is also content: a runner must report
the immutable source commit, whether that checkout is dirty, the schema version,
and SHA-256 checksums of `schema.json`, `vectors.json`, and this `README.md`.
JSON hashes alone do not identify comparison semantics in a dirty snapshot. See
[versioning](../../docs/versioning.md).

The seven categories and current case counts are: features (35), ranges (7),
control requests (21), control responses (12), measurements (8), statuses (4),
and diagnostics (10): 97 IDs in total. A runner must enumerate every category,
validate globally unique IDs, and count each case. It must report an explicit
unsupported result for a category or case it cannot execute; it must not drop it
or call a partial run passing. `skip` is only meaningful when recorded with its
case ID and reason in the summary, and is not a pass.

## Required v1 comparison behavior

Before comparing cases, validate `vectors.json` against the exact `schema.json`.
Use the bytes exactly as supplied: byte values are unsigned 0--255, ordering and
length are significant, and a range or malformed payload must not be repaired.
An adapter may expose normalized language-native objects and idiomatic field names;
it need not reproduce TypeScript field spelling. It must retain a documented,
unambiguous mapping for each expected field, unit, unavailable value, and
diagnostic code.

The following pins the behavior of the current TypeScript v1 consumer:

| Case kind | Comparison |
| --- | --- |
| Features with `expected` | Exact object equality: the complete key/value structure must match. |
| Features with `expectedTrue` | The set of fields whose adapted value is exactly `true` must equal the expected set. `supportsERG`, `supportsSIM`, and `supportsResistance` are v1 compatibility names, not new canonical cross-language API names. |
| Valid ranges | Exact object equality after adding the vector `kind`. |
| Invalid ranges and invalid control responses | Subset-object match requiring at least `ok: false` and the expected error `code`; additional fields are permitted. |
| Control requests | Exact byte-array equality, including length and element order. |
| Valid control responses | Exact equality after reducing issue objects to their `code` arrays. Objects have no extra keys; arrays have the same length and positional order. |
| Measurements and diagnostic metrics | Expected metric keys are a subset: every listed key is checked, extra actual metrics are permitted. Numeric expected values require finite actual numbers with `abs(actual - expected) < 0.005`; the boundary `0.005` fails. Strings and `null` compare exactly. |
| Statuses | Subset-object match: every expected key/value is required and extra actual keys are permitted. |
| Diagnostics | `truncated` compares exactly. Every expected issue code must be present; issue-code order is insignificant and extra codes are permitted. Optional expected metrics/status code use the rules above. |

Exact object equality includes exact enumerable keys and recursively exact values.
Exact arrays require the same length and positional values. A subset object is
recursive: every expected object key must match, while extra actual object keys
are permitted. Arrays in a subset comparison must have the same length and match
each element in order under that same recursive rule; they are not prefixes or
unordered sets. The only current unordered collection rule is diagnostic issue
code inclusion. An expected key with `null` requires actual `null`; it is not a
missing value. An expected numeric zero is a required finite number, not absence
or falsiness. If a key is absent from a subset expectation it makes no assertion
about an extra actual key; if it is present and the actual key is missing, the case
fails.

## Runner outcome and reporting

A port may implement its runner in its own test framework. There is deliberately
no required shared executable harness yet. Its invocation should, at minimum:

1. load the exact schema and vectors from a pinned revision;
2. validate the corpus and reject an invalid corpus as a runner failure;
3. execute every supported case using the category operation and v1 comparison
   rules above; and
4. emit a summary with corpus identity, total discovered cases, passed, failed,
   unsupported, and skipped counts, plus IDs/reasons for every non-pass and any
   runner-level error.

The summary must make category counts visible, so a report cannot imply that a
port covered all of v1 when it ran only a subset. A clean run has zero failed,
unsupported, and skipped cases. Host tests, consumer-installation tests, embedded
cross-builds, fuzzing, and real-device/PTS evidence are separate evidence streams.

The current TypeScript Vitest consumer emits this port-local summary from its
conformance test. It identifies the current Git `HEAD`, marks the known dirty
checkout state, hashes the canonical schema, vectors, and contract bytes, and
records every v1 vector's pass/fail outcome. This is evidence from that local
test run, not a shared runner framework or a native-port result.

See the [coverage matrix](../../docs/coverage.md) for the current TypeScript
surface and the [shared layer overview](../README.md) for repository ownership.
