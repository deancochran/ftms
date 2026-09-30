# Changelog

## 0.1.0

Initial Rust raw-codec release.

- Independent, allocation-free `no_std` implementation with no unsafe code or
  runtime dependencies; minimum supported Rust version 1.85.1.
- Bidirectional Features, five Supported Ranges, all 21 Control Point requests
  and responses, six measurement families, Training Status and Machine Status.
- Explicit independent wire-format selections, diagnostic range inspection,
  raw absent/unavailable distinctions and failure-atomic caller-buffer encoding.
- Shared literal conformance and structural-matrix tests, malformed-input and
  boundary checks, Cortex-M0 compilation and isolated packaged consumers.
- Gated `rust-vVERSION` crates.io publishing and checksum-pinned GitHub release evidence.

Feature/capability interpretation and fragment planning/reassembly are not yet
implemented. These host/package checks are not MCU execution, Rust BLE/device
interoperability, PTS or Bluetooth qualification evidence.
