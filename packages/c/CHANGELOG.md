# Changelog

## 0.2.0

- Add `ftms_inspect_range` and `ftms_inspect_range_with_format`: selected profile,
  expected/observed lengths and bounded structural candidates without automatic
  selection. Non-valid values must not be read as valid zero ranges.
- Preserve existing decoder defaults, structures and capability report shapes.
- Add nine shared exact inspection reports and 181,760 generated measurement
  layout cases, 46 sentinel positions, 47 reserved bits and 650 planner budgets.
  Native matrix runs normally and under ASan/UBSan; installed consumers exercise
  the new inspection symbols.
- Add a host-only passive telemetry capture/replay example and document limited
  KICKR CORE evidence. No universal interoperability, safe-control, MCU runtime or
  Bluetooth qualification claim is made. Registry submissions remain separate.

This is an additive API release. The 0.x CMake package-version policy requires
consumers constrained to the 0.1 minor line to update their requested version.

## 0.1.0

Initial C99 source-package release: bidirectional Feature, range,
measurement, status and control-point codecs; bounded measurement planning,
generation-aware receive assembly and
static capability interpretation. It does not provide Bluetooth discovery,
permissions, lifecycle integration, control authorization, device certification,
or qualification.

Includes explicit resistance-command format selection, caller-owned tri-state
C.7 evidence APIs, shared conformance fixtures and deterministic simulation.
Legacy capability APIs treat omitted C.7 evidence as unknown, potentially adding
diagnostics and incomplete prerequisites. Query diagnostic capacities before
evaluation. Source archives are verified with native and installed consumers;
Conan/vcpkg public registry submissions remain separate from this source release.
