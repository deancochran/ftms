# Go coverage and remaining parity work

Status: **unreleased raw codecs and capability interpretation**. The proposed final target is `FullWire`
with `CapabilityEvidence`, `RangeInspection`, `NormalizedViews`, `RecordPlanning`,
and `RecordAssembly`. This milestone does not claim that final target is complete.

## Implemented wire directions

| Family | Decode | Encode |
| --- | --- | --- |
| Feature bitmaps, including unknown bits | Yes | Yes |
| Speed, inclination, resistance, heart-rate, power ranges | Yes | Yes |
| Treadmill, cross trainer, step climber, stair climber, rower, indoor bike | Yes | Yes |
| Control requests, all 21 opcodes | Yes | Yes |
| Control responses including Spin Down speeds | Yes | Canonical responses |
| Machine Status and Training Status | Yes | Canonical statuses |

Decode-only malformed/unknown evidence is not canonical encode support.
Encoders validate their inputs and do not return a partial packet on failure.
Control requests expose ordered raw operands; a named-operation convenience
interface remains a pre-release design consideration.

## Executed shared evidence

All assets are read directly from the source checkout, never copied into this port.

| Contract | Cases | Directional assertions / reports |
| --- | ---: | ---: |
| `values/v1` | 8 | 16 |
| `controls/v1` | 41 | 72 |
| `measurements/v1` | 26 | 47 |
| `statuses/v1` | 38 | 63 |
| `compatibility/v1` | 9 | 18 |
| **Five schema-validated additive corpora** | **122** | **216** |
| `inspection/v1` | 9 | 9 exact complete reports |
| `capabilities/v1` | 63 | 63 exact complete reports |
| `measurement-matrix/v1` | 181,760 layouts | 363,520 structural assertions |

The matrix also checks 46 sentinel positions, 47 RFU bits (decode and encode
rejection), and 315 incomplete prefixes. These counts are separate from Go test
function counts. Expected layout bytes and field maps come from the shared
test-only declaration, not the production codec's layout table. Literal all-field
vectors remain independent anchors.

Every supported additive case/direction is executed; there are no skips or
unsupported cases inside those five named corpora. This does not imply that every
other project corpus is supported.

Capability evidence separately passes all 63 cases with no failures, skips, or
unsupported cases: discovery 12, duplicates 3, features 5, forward-compatibility 2,
measurements 7, operations 4, properties 22, ranges 8. Counts are discovered from
the canonical file. Every entire report is compared exactly, including ordered
diagnostics, all observations, C.7 consequences and all 21 operations; no subset
matching or numeric tolerance is used. Source templates and each independently
expanded snapshot/report are schema-validated. See `verification.md` for all four
identity hashes and reporting requirements.

Additional native tests exercise the full C.7 truth table, failed reads combined
with unknown C.7, duplicate observation diagnostics, invalid argument rejection,
explicit resistance-range selection alongside other ranges, UUID matching and
input/result ownership. These tests do not extend the canonical corpus claim.

## Not implemented or not claimed

- Original normalized `shared/conformance/v1`: all 97 cases remain outside this
  milestone; passing raw corpora is not passing that comparison contract.
- `RecordPlanning` and `RecordAssembly`: no byte-concatenation substitute is
  exposed. The C planner's 650 matrix budget cases do not run for Go.
- `NormalizedViews`: ranges only; normalized measurements remain pending.
- Real devices, BLE lifecycle, physical-control safety, PTS, Bluetooth qualification,
  TinyGo, and embedded targets: no evidence or support claim.
- Public publication and pkg.go.dev indexing: not performed.

Before the first full-parity release, complete the pending modules, validate all
their contracts, finish exported interface documentation and ergonomic review,
and execute the public consumer gate described in `releasing.md`.
