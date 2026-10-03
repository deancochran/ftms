# Changelog

## 0.1.0-alpha.2

Date: 2026-10-03

- Add a pure UUID-selected measurement decoder for all six FTMS data layouts.
- Keep legacy uint8 treadmill pace raw-only rather than labeling it as seconds
  per 500 metres in normalized views.

## 0.1.0-alpha.1

Initial C# prerelease; the public interface is still evolving. Consult the
repository's release matrix for verified public availability.

- Pure managed bidirectional Feature, range, Control Point, measurement and status codecs.
- All six measurement families, explicit compatibility profiles, raw evidence and normalized views.
- Static capability interpretation with C.7 evidence, diagnostics and operation prerequisites.
- Independent canonical fixture runners, measurement matrix and schema validation.
- Local NuGet artifact, isolated target-assembly consumers and Linux NativeAOT verification.
- Credential-free CI and signed-tag NuGet Trusted Publishing with public-artifact verification.
