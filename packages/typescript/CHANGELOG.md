# Changelog

All notable changes to `@deancochran/ftms` are documented here. The package
follows [Semantic Versioning](https://semver.org/).

## 0.3.0

Unreleased release candidate. Publication is a separate maintainer action after
review and successful release checks.

### Added

- Bidirectional raw codecs for Features, all five Supported Ranges, all 21
  Control Point requests and responses, all six measurement families, Training
  Status and Fitness Machine Status. Existing normalized APIs remain available.
- Static capability interpretation with `evaluateFtmsCapabilities`, preserving
  incomplete discovery, duplicate characteristics, read failures and contradictory
  evidence without granting execution permission.
- Explicit opt-in resistance and treadmill-pace wire-format compatibility
  options on raw codec APIs (not existing normalized parsers/registry).
  Default layouts remain unchanged; no device-name inference or
  automatic format selection is introduced.
- Shared raw-codec, capability and compatibility fixtures, boundary tests and
  independent installed-package integration examples.

### Changed

- Moved TypeScript implementation and tooling into `packages/typescript` within
  the multi-language repository. Preserved package name, public module/export
  paths and the 42-file distribution layout.
- Hardened raw argument validation, including cross-realm byte sources, invalid
  format/kind values, unavailable sentinels and malformed status evidence.

Real-equipment interoperability and Bluetooth qualification are not established
by the synthetic protocol corpus or host examples.

## 0.2.0 - 2026-07-29

### Breaking

- Removed `@deancochran/ftms/application`; application policy, machine inference, presentation,
  and control lifecycle contracts now remain outside this protocol package.

### Changed

- Added authoritative provenance for mandatory Correction 23224, which updates FTMS 1.0
  conformance language without changing wire formats.
- Reserved Control Point request opcodes are now rejected, and reserved Training Status and result
  values produce diagnostics.
- Corrected Cross Trainer stride-count scaling and unavailable step-rate handling from the pinned
  Bluetooth GSS definitions.

### Added

- Cross-realm and offset binary-view compatibility across public decoders and parsers.
- Expanded versioned conformance vectors and schema, plus packed-artifact browser,
  runtime-neutrality, export, and source-map verification.

## 0.1.0 - 2026-07-24

### Added

- Runtime-neutral FTMS constants, feature and supported-range decoders.
- Parsers for all six FTMS machine-data characteristics, Training Status, and
  Fitness Machine Status.
- Encoders for all FTMS 1.0 Control Point procedures and response decoding.
- Parser registry, machine-type detection, diagnostics, and control-state
  helpers.
- Versioned language-neutral conformance vectors and JSON Schema.
- ESM, TypeScript, and React Native/Metro package exports.
