# TypeScript / C parity audit and closure

## Subsequent C additions

The later C measurement packet planner and bounded receive-record assembler
(`ftms_record_init/reset/feed`) are **C-only**. The shared raw codec and
capability parity below does not imply a corresponding TypeScript packet-planning
or assembly API. They form a transport-independent convenience layer above codecs, not a missing
TypeScript wire codec. This release-packaging milestone records that difference
rather than claiming renewed complete API parity or silently expanding protocol
scope. Swift/Kotlin remain scaffold-only and are not package releases.

Explicit format propagation is intentionally asymmetric: TypeScript propagates
caller-selected layouts through normalized measurement parsing, registry dispatch,
normalized resistance ranges and static capability evaluation. C keeps raw native
values but propagates formats through capability requirements/evaluation and packet
planning and receive assembly. There is no TypeScript planner and C's normalized
floating metrics are not invented. Legacy C assembly remains default-layout only;
its separate format context fixes an explicit copied profile for one record.

2026-09-28; local dirty branch `scaffold/native-capabilities`, base/HEAD
`41023a60cff6efdeef5e36730c3d7356a91d26b6`. No release or remote mutation.

## Gaps closed

TypeScript previously lacked Feature/range encoding, Control Point request
decoding and response encoding, measurement/status encoding, raw diagnostic
representations and aggregate capability interpretation. These are now additive
APIs in existing modules. Old normalized parsers, control request encoders,
validated response behavior and compatibility aliases remain intact.

Both ports now exercise the same canonical fixtures:

| Corpus | Cases | Directional assertions per port |
| --- | ---: | ---: |
| Original codec-v1 | 97 | 97 |
| Raw values | 8 | 16 |
| Raw controls | 35 | 62 |
| Raw measurements | 26 | 47 |
| Raw statuses | 38 | 63 |
| Capabilities | 49 | 49 complete reports |

All listed cases and declared directions passed in both ports. Invalid/decode-only
fixtures are scoped explicitly; they are not claims of successful encoding.
Expected outputs come from literal shared fixtures, not another port's output or
a round-trip oracle. Capability templates expand deterministically and full
reports compare exactly. Raw codec tests compare all normalized fields, not only
opcode or selected metrics. Tests run in existing TypeScript and native CI jobs,
so continued parity is checked against the same contracts rather than fixture
copies maintained separately in each package.

## Deliberate differences

- C uses caller-owned storage and error returns; TypeScript allocates byte arrays
  and throws typed `RawCodecError`. Parameter-validation precedence/error labels
  need not match where inputs cannot exist in one language (NaN, fractional
  numbers, wrong JS objects versus pointers/capacities). Shared invalid wire
  fixtures do match the prescribed categories.
- TypeScript retains human-unit APIs, strings, parser registry and richer existing
  diagnostics. C remains fixed-point and allocation-free. Raw protocol evidence
  and encoded bytes, not language-specific object layouts, are the parity target.
- Capability buffer requirements are necessary in C but not an additional
  operation in an allocating TypeScript evaluator. Both evaluate the same pure
  evidence, preserve generation and duplicates, and never authorize execution.
- The older TypeScript response decoder intentionally rejects some malformed
  responses that the new raw decoder retains with diagnostic flags. C's validated
  corpus adapter uses the same projection; this compatibility boundary is explicit.

## Review findings fixed

Independent review found realm-sensitive checks rejecting foreign byte arrays,
prototype-key range lookups leaking TypeError, forgeable binary type tags, unexpected action-status parameters
being silently discarded, and weak raw corpus comparisons. Fixed these and added
regressions. Coordinator verification also caught invalid measurement kinds being
classified as range instead of kind errors; corrected and asserted exact error
categories. Tests now independently encode Training Status from fixture inputs,
schema-validate raw corpora, check unique IDs and assert direction counts. Added
all-field truncated-prefix checks, malformed UTF-8 and nonfinite/fractional input
tests. No changes to C production code were needed for this parity milestone.

## Actual verification

`env -u TMPDIR pnpm verify` passed: 512 tests in 11 files, lint/typecheck/build,
97/97 original vectors, packed installation, exports/maps/browser/declarations
and unchanged 42-file tarball layout. Native `make BUILD=build/parity-native test`
passed all corpora, strict/sanitized units, 20,000 bounded fuzz iterations and six
real installed C/C++ consumer combinations. Logs are ignored local files under
`packages/c/build/parity-typescript.log` and `parity-native.log`.

The shared capability contract wording now acknowledges both implementations.
Its new SHA-256 is
`035867b2c8590aeb753ba71d24904c09efa41c20855a68fa5e897009ac95f6a3`.
Capability schema/vectors/comparison README are unchanged. Original codec-v1
schema/vector/contract identities remain unchanged; additive corpus identities
are those recorded in `packages/c/docs/verification-bidirectional.md`.
Previous source-byte-unchanged statements predate this explicitly authorized
TypeScript extension and are historical, not statements about current source.

These are local source capabilities, not additions already available in published
0.2.0. Package version/publication is unchanged. Neither port provides BLE
transport, permissions, connection/control ownership or actuator safety. Embedded
runtime/board, real-device interoperability and Bluetooth qualification remain
unverified; Swift/Kotlin remain scaffolds. No assertion of universal FTMS or
physical-equipment compatibility follows from these finite regression corpora.
