# Changelog

## 0.2.0

Date: 2026-10-03

- Add `MeasurementReader.decode`, a UUID-selected, format-explicit normalized
  measurement view for all six FTMS data characteristics. It exposes named
  nullable physical metrics, typed unsupported/invalid outcomes, raw diagnostic
  access, and format provenance without inferring legacy treadmill pace units.

## 0.1.0

- Initial independent Kotlin/JVM raw FTMS implementation for Java and Android callers.
- Features, five ranges and inspection; all 21 controls and responses; all six
  measurement families; Training and Machine Status; static capability evaluation.
- Explicit wire-format variants, immutable raw evidence, strict encode validation.
- Canonical conformance suites, measurement layout matrix, API baseline, isolated
  Kotlin/Java artifact consumers and Android compilation check.

Package version is independent of protocol, corpus, TypeScript and C versions.
