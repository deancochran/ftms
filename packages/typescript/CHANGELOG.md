# Changelog

All notable changes to `@deancochran/ftms` are documented here. The package
follows [Semantic Versioning](https://semver.org/).

## 0.4.0

### Added

- Add `inspectFtmsRangeRaw`, a caller-profile-preserving range diagnostic with
  bounded structural candidates. It does not infer a format, physical unit, or
  control permission from a candidate's success.
- Add shared exact range-inspection fixtures and a structural measurement matrix:
  181,760 layout combinations, sentinel and reserved-bit cases across all six
  equipment families. Existing defaults and capability report shapes are unchanged.

### Fixed

- Reject inherited/accessor wire-format selections and C.7 evidence. Own data
  properties remain supported across realms and on null-prototype records.
- Check original normalized control bounds before grid alignment; use a
  documented binary64-relative tolerance instead of an absolute `1e-9` allowance.
  Raw integer codecs and default formats are unchanged. Out-of-bound inputs now
  report `out_of_range` before resolution validation.

## 0.3.0

Release prepared for publication through the verified tag workflow.

### Added

- Explicit resistance-command formats in raw and normalized APIs: the default
  remains signed16 tenths, with opt-in UINT8 tenths; status encoding is unchanged.
- Caller-owned C.7 bonding/lifetime-mutability evidence in capability snapshots,
  with shared true/false/unknown fixtures and conditional Feature Indicate checks.
- Deterministic shared equipment simulation and page-by-page specification audit.

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

- Capability snapshots without C.7 evidence now report insufficient evidence;
  applicable operation prerequisites can be incomplete rather than satisfied.
  This never grants permission to execute controls.

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
