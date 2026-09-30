# Swift changelog

## 0.1.0

- Initial native Swift 6 implementation of the FTMS 1.0 + EC23224 protocol
  codecs: Features, five ranges, six measurement families, all 21 control
  requests/responses, Training Status and Machine Status.
- Explicit independent compatibility formats, normalized measurements/ranges,
  range inspection and conservative static capability interpretation.
- Canonical shared-fixture comparisons, exhaustive measurement-layout tests,
  malformed-input and API-invariant regressions, and isolated SwiftPM consumers.
- No BLE or application lifecycle dependency. Protocol capability evidence does
  not grant permission to execute equipment controls.

Distribution uses `swift-v0.1.0` in the existing FTMS repository. Install by
revision/tag, **not** a SwiftPM semantic-version range: the repository's `v*`
tags belong to npm. Swift's package version is independent of FTMS and corpus
versions. Release evidence records host tests and Apple SDK compilation
separately; neither is real-equipment interoperability or qualification.
