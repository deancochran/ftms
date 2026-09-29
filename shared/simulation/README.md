# Deterministic simulation contract

`v1` is a synthetic scenario corpus, not exhaustive FTMS conformance, BLE,
or device qualification. A profile fixes `kind`, `maxAge`, and the complete format
object (`resistance`, `pace`) at initialization; runners copy it rather than infer
format from a packet. Capability events replay caller-supplied discovery evidence;
they do not perform discovery. Control exchanges are scripted codec checks, not
control ownership, command-queue, actuator, or safety models.

`at` is a non-negative relative unsigned-32 tick. `baseTick` defaults to zero and
the effective clock is `(baseTick + at) >>> 0`. Steps are stable-sorted by `(at,
original index)`. The first More Data fragment establishes a fixed deadline; unsigned
age expires at `age >= maxAge`, including wrap. Generation is checked before expiry.
Disconnect and reconnect clear pending state. A dropped packet is deliberately not
delivered. There is no sequence number: a complete assembled record cannot prove
that an optional fragment was not lost.

Every completion contains hand-authored full raw evidence: all thirty values, masks,
flags, direction, diagnostics, and byte count. Expected outcomes never go to the C
bridge. The TS test session is a conceptual array of decoded accepted fragments then
a 30-field reduction; C uses its production record assembler. Both require strict
canonical fragment decoding. Reports continue after mismatches and include per-step
actual traces, counts, runner errors, source identity, and SHA-256 input identity.

## Event and oracle contract

- `feed` delivers the exact bytes and explicit generation to the selected receiver.
  Raw completion objects compare exactly, including all 30 integer fields, absent
  zeros, presence/unavailable masks, and diagnostics. Non-completion results must
  contain only a status. C additionally checks that non-completion leaves its
  output buffer untouched.
- `reset` clears pending data without reconnecting; `disconnect` clears data and
  disables delivery. `connect`/`reconnect` initializes a fresh session with the
  event's generation and the same profile. A feed while disconnected returns the
  harness status `disconnected`, without invoking a codec. There are no real links.
- `drop` records `dropped` and delivers nothing. Deadlines are tested when the next
  notification arrives, matching the C API; there is no background timeout timer.
- `capabilities` references a case ID in `shared/conformance/capabilities/v1`.
  Its expanded literal snapshot and full report are used independently. A snapshot
  is a separate observation: its generation comes from that fixture, not implicitly
  from the measurement session. Missing evidence remains missing.
- `control` and `response` reference request/response cases in
  `shared/conformance/controls/v1`. Decode compares to the authored value; encode
  takes that authored value, **not** the decoder's result, and compares to literal
  bytes. A response with `encode: false` is a decode-only diagnostic case.
  The request case's optional explicit format is passed to both independently
  authored decode and encode calls. Scripted success/rejection is not proof of
  physical command execution.

All objects and arrays compare recursively and exactly; object key order is not
significant. Booleans are not numeric values, and missing/extra fields fail.
Referenced corpora are schema-validated. Duplicate IDs, missing profile/case
references, unknown fields and malformed result shapes are runner errors. No
scenario is silently skipped. There are no network calls, wall-clock sleeps or
unseeded random decisions. These are explicit fault scripts, not a randomized
state-space exploration engine; replay uses the exact scenario files.

## Versioning, reporting and scope

`schemaVersion: 1` names this simulation format, not a package or FTMS version.
The source commit, dirty state and per-file SHA-256 values identify the scenario,
schema, comparison contract and all referenced corpus/schema/contract files.
`inputSha256` additionally identifies the actual in-memory input used by mutation
tests. Only canonical JSON inputs are accepted; Git metadata and hashes are report
metadata, not event scheduling inputs.

The current matrix has **10 profiles, 38 scenarios and 79 scheduled steps**.
Every runner emits scenario and step totals, individual outcomes, a stable trace
with source index, relative and wrapped ticks, actual/expected values, failure
reasons, unsupported/skipped counts and runner errors. `complete` requires all
scenarios and steps accounted for without failures or runner errors. A reference
step may make both encode and decode assertions; step counts are not codec-call
counts. Strict bridge failures are not successful simulated device errors.

C reports `c-production-record-assembler`; TypeScript reports
`typescript-session-harness`. Both exercise production measurement/control codecs
and capability interpretation. TypeScript's receive lifecycle is test-only, not a
new exported API or evidence of production assembler parity. Cross-port trace
agreement supplements the literal oracle; it is not itself the oracle.

See [design and commands](../../docs/simulation.md). Open Trainer integration,
virtual BLE, physical-device validation and additional language ports are optional
future work, not acceptance gates for this suite.
