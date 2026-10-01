# Changelog

Python distribution versions are independent of FTMS specification, shared
conformance corpus, and other language-package versions.

## Unreleased

- Correct the development-status classifier from Pre-Alpha to Alpha to match
  the native alpha version and documented API maturity. This source-only change
  is for the next versioned release; immutable PyPI 0.1.0a2 metadata is unchanged.

## 0.1.0a2

- Add pure static capability evaluation with immutable discovery/read evidence,
  C.7 facts, duplicate and unknown evidence, and all 21 operation prerequisites.
- Support explicit resistance range profiles during capability evaluation.
- Verify all 63 shared capability cases with exact expanded-schema/type checks,
  full accounting, and canonical corpus/contract hashes.
- Add input validation, immutability, fixture-runner regression tests, and
  installed runtime/typed-consumer checks for capability APIs.

The API remains alpha. Capability evidence is not permission to execute controls.
No BLE, lifecycle, normalized control encoder, or record planning/assembly is added.

## 0.1.0a1

Initial partial alpha; APIs may change before a stable release.

- Pure synchronous Python with no runtime dependencies, Python >=3.11,
  immutable raw models, and inline typing.
- Bidirectional raw Features, all five supported ranges, structural range
  inspection, and normalized Feature/range views.
- Bidirectional raw codecs for all 21 Control Point requests and responses.
- Bidirectional measurements for treadmill, cross trainer, step climber,
  stair climber, rower, and indoor bike, with normalized metric views.
- Bidirectional Training Status and Machine Status, normalized views, and
  preservation of malformed/unknown decoding evidence.
- Explicit, independent range, command, and measurement wire-format options.
- Canonical shared fixture, structural matrix, and isolated package checks.

Not included: static capability evaluation, a public human-unit control encoder,
Bluetooth transport, device lifecycle, retries, execution permission, or safety
policy. Host tests are not device interoperability or Bluetooth qualification.
