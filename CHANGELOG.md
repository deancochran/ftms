# Changelog

All notable changes to `@deancochran/ftms` are documented here. The package
follows [Semantic Versioning](https://semver.org/).

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
