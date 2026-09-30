# Changelog

Python distribution versions are independent of FTMS specification, shared
conformance corpus, and other language-package versions.

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
