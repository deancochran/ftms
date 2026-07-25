# Changelog

All notable changes to `@deancochran/ftms` are documented here. The package
follows [Semantic Versioning](https://semver.org/).

## 0.2.0 - 2026-07-25

### Changed

- Moved application policy, machine detection, and the experimental control reducer to
  `@deancochran/ftms/application` so the root export remains protocol-focused.
- Control command timeouts now enter `control_uncertain` and require explicit transport recovery
  before control can be requested again.
- Corrected Cross Trainer stride-count scaling and unavailable step-rate handling from the pinned
  Bluetooth GSS definitions.
- Expanded the versioned conformance corpus to cover features, ranges, responses, diagnostics,
  optional fields, unavailable values, and mandatory FTMS errata.
- Releases now publish only from a matching source-controlled version tag.

### Added

- Cross-realm and offset binary-view compatibility across public decoders and parsers.
- A version-coupled `@deancochran/ftms/conformance/v1/schema` export.
- Packed-artifact browser bundling, content allowlist, source-map, and runtime-neutrality checks.
- Lefthook pre-push test enforcement for contributors.

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
