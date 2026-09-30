# Dart verification and evidence

Source implementation base: `accc347f12d1244b24f2e8a422627cca0dad2763`.
This is an unpublished, uncommitted source candidate until separately delivered.
The runner always records its actual HEAD and dirty state; never describe dirty
local evidence as a clean tagged release.

## Initial local execution (2026-09-30)

- Linux x86_64: Dart **3.11.0** minimum SDK and **3.13.5** current SDK are the
  validation targets. The initial minimum-SDK run passed 311 Dart tests, zero
  failures/skips, all nine corpus suites, documentation generation, zero-warning
  pub dry run and isolated VM/native-executable package consumers.
- Dart **3.13.5**: the same 311-test suite and full structural matrix passed in
  Chromium (Brave) with both **dart2js** and **dart2wasm**. This is executed browser
  evidence, not just compilation. Final reruns retain their exact runner hashes.
- Independent review found and corrected silent-loss paths for contradictory
  measurement metadata and Training Status text/offsets. Regression tests reject
  those inputs. Encode tests use fixture inputs independent of decoder output.
- macOS/Windows host jobs and Flutter Android/iOS consumer builds are implemented
  but have **not run locally**. Flutter is not installed in the validation session.
  Remote CI, tags, publication and post-publication checks have not run.

Codec-v1 identity at this source base:

| Asset | SHA-256 |
| --- | --- |
| `v1/schema.json` | `e6d976172a32e3124602d17e46ed5fbab337f4f1d6535aec85a83069637268e0` |
| `v1/vectors.json` | `9b5b61353b191179cc629d8c459b2a185b9e03b7ce5f3f51b715520162e8a5c7` |
| `shared/conformance/README.md` | `4ee407ecca3cdce77289ff15920bd831dc6687e5dff0ac9c0a8edf39d6034cc9` |

Capability-v1 identity:

| Asset | SHA-256 |
| --- | --- |
| schema | `1a23dd523896d41b6aa115eea906e6f899a9cfcc8008a87d133ba8c51409ef26` |
| vectors | `90a9b85e735455515c36fc089fa786bd928e217e81cf95f5ccef67c0d479d3dd` |
| comparison contract | `e844292d9a916aa63db9d1f6d22de5525c1923e3584afbcc5013d93d374e6a6a` |
| capability protocol | `541ddd5950999bcd048808fd6eff578dc0a7031eaaa0dc988f8711003ecd488f` |

All additive corpus identities are included in each machine-readable report.

## Acceptance accounting

| Corpus | Cases / assertions |
| --- | --- |
| Original codec v1 | 97 IDs, all seven categories |
| Raw values | 8 cases / 16 directions |
| Raw controls | 41 cases / 72 directional assertions |
| Raw measurements | 26 cases / 47 directional assertions |
| Raw statuses | 38 cases / 63 directional assertions |
| Compatibility | 9 cases / 18 directional assertions |
| Range inspection | 9 complete reports |
| Static capabilities | 63 complete reports |
| Measurement structural matrix | 181,760 layouts / 363,520 directions |
| Matrix boundaries | 46 sentinel, 47 RFU, 315 incomplete-prefix cases |

Each corpus's cases are enumerated from canonical assets, schema-validated where
a schema exists, and matched against actual named Dart test completion events.
Missing drivers, duplicate IDs, failures and skips prevent a complete report.
Matrix counts are emitted only after executing and asserting all generated cases.
Test-method totals are deliberately separate from generated case counts.

Original codec-v1 uses its exact historical subset/numeric comparison contract
(finite numbers, strict absolute error less than 0.005 for measurement metrics).
Additive raw and capability tests compare complete literal expectations. Encode
inputs are built from independent fixture values, never decoder output.
Capabilities expand literal input and expected templates independently and validate
both expanded sides against the checked-in schema.

Reports retain source commit/dirty state, exact SDK, platform/compiler, runner
hashes and schema/vector/contract SHA-256 identities. Capability identity also
includes `shared/protocol/capability-discovery.md`. Schema version alone is not
content identity. Inspection and matrix have no canonical JSON Schema; their
test-owned structural assertions and runner hashes are identified separately.

## Commands and outputs

Run `python3 tool/verify.py --package` from `packages/dart`. Browser runs use
`--platform chrome --compiler dart2js` or `dart2wasm`. Outputs are ignored under
`build/`; `verification.json` contains complete accounting, and `tests.jsonl` is
the original Dart reporter stream. Failures invalidate stale completion evidence.

`tool/verify_package.py` builds a deterministic source archive with a strict file
manifest, checks the root MIT license, performs pub's dry run, extracts into an
independent temporary directory and runs/compiles a consumer with a fresh cache.
This is local artifact installation evidence, not registry publication.
`tool/verify_public.py` separately checks the public pub.dev archive and hosted
consumer after an authorized release.

## Evidence limits

Minimum/current SDK, OS, browser and Flutter jobs are independent. A workflow file
is planned automation until it has actually run. Linux VM evidence does not prove
macOS/Windows execution, Flutter Android/iOS builds, Bluetooth operation, real
equipment behavior, control safety, PTS success or qualification.
