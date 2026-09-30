# Changelog

## 0.1.1

Prepared release; publication is not yet claimed.

- Added public allocation-free normalized range, human-unit control-request,
  control-response and Machine Status projections, retaining status actions.
  The normalized codec-v1 adapter now validates and
  accounts for all 97 canonical cases (zero unsupported/skipped); this is source
  capability after 0.1.0, not a change to that released artifact.

## 0.1.0

Initial Rust protocol-library release.

- Independent, allocation-free `no_std` implementation with no unsafe code or
  runtime dependencies; minimum supported Rust version 1.85.1.
- Bidirectional Features, five Supported Ranges, all 21 Control Point requests
  and responses, six measurement families, Training Status and Machine Status.
- Explicit independent wire-format selections, diagnostic range inspection,
  raw absent/unavailable distinctions and failure-atomic caller-buffer encoding.
- Shared literal conformance and structural-matrix tests, malformed-input and
  boundary checks, Cortex-M0 compilation and isolated packaged consumers.
- Gated `rust-vVERSION` crates.io publishing and checksum-pinned GitHub release evidence.

- Static capability-evidence interpretation with 63 exact canonical reports,
  typed Feature queries and normalized measurement projections, and bounded
  More Data planning/assembly. Normalized codec-v1 evidence covers 35 Feature
  cases; the remaining 62 cases are explicitly unsupported by that runner.

These host/package checks are not MCU execution, Rust BLE/device
interoperability, PTS or Bluetooth qualification evidence.
