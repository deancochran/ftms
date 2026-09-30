# Real-equipment verification

## Current evidence

**A limited passive KICKR CORE result is recorded:**
[2026-09-29 Linux pilot](equipment-results/2026-09-29-kickr-core-linux.md).
It covers one authorized telemetry session, one successful reconnect path and
offline cross-port replay, not live controls, physical accuracy, exhaustive
reconnect/lifecycle behavior or MCU execution. The table separates package/host
verification from that limited device observation.
Do not interpret codec fixtures, literal example packets, simulated equipment,
compiler checks or successful package installation as Bluetooth device testing.

| Evidence | Status | Scope |
| --- | --- | --- |
| Published npm 0.4.0 package | Verified | Registry artifact and isolated consumers; no radio in package verification |
| Published C 0.2.0 source archive | Verified | Installed C/C++ consumers and simulated packet codecs; no radio in release verification |
| Published Swift/Kotlin/Python packages | Verified within each release's documented host/consumer scope | No live BLE runtime evidence |
| Real equipment, telemetry | Partial | One KICKR CORE/Linux passive pilot; 55 packets and one reconnect, using earlier artifact versions |
| Real equipment, control procedures | Not tested | Explicit operator authorization and physical safety arrangements needed |
| Bluetooth PTS / qualification | Not tested | Separate process; not implied by interoperability |

Runnable examples are in [examples](../examples/README.md). They deliberately do
not open Bluetooth connections or write controls. The C planner/assembler is an
additional C-only API; shared wire-codec parity does not imply equal platform or
convenience-layer features.

## First equipment test: start with passive telemetry

1. **Identify the actual equipment.** Record manufacturer, exact model, firmware
   version, machine family, power state and any relevant mode/configuration.
   Do not publish its MAC address, serial number or user-identifying data.
2. **Pin installed artifacts.** Record package version, registry/source URL,
   source revision if available, and integrity/hash. Install the released package
   into a clean consumer project. If a candidate is used, label it a candidate;
   do not attribute its results to a published version.
3. **Record the platform.** OS/version, Bluetooth adapter and stack/library,
   application version/commit and transport integration. A successful Linux test
   does not establish Android/iOS or firmware compatibility.
4. **Get consent to connect and capture.** Identify the operator and intended
   telemetry-only scope. Ensure no other app owns the connection. Do not change
   pairing/security settings or send control requests silently.
5. **Use a real, separately owned BLE transport.** Discover the selected FTMS
   service instance; record full characteristic UUIDs, properties, duplicate
   instances, read outcomes, permissions and negotiated value budget. Feed actual
   characteristic bytes into the library. Do not infer the service from a device
   name or force an indoor-bike interpretation.
6. **Read features and supported ranges.** Capture raw values and compare reported
   capabilities with what the equipment actually exposes. Preserve failed reads
   and absent characteristics as evidence, not zeros or false support declarations.
7. **Subscribe to supported telemetry.** Record a short idle interval and a safe,
   operator-driven active interval. Record raw bytes and decoder output, timestamps
   relative to session start, source UUID and observed truncation/RFU/unavailable
   diagnostics. Preserve More Data fragments rather than assuming one complete
   record per notification. Distinguish packet loss from parser behavior.
8. **Compare observations.** Compare a small selected set of measurements with
   the equipment display or an independent reference, documenting resolution and
   timing differences. This is not a calibrated accuracy certification.
9. **Disconnect and reconnect.** Verify caller-owned discovery/subscription state
   is refreshed and stale generation/assembly state is not reused. Record whether
   failures originate in transport integration, firmware or protocol decoding.
10. **Write and review the result.** Use the template below, attach sanitized
    captures and exact reproduction commands, and state only the tested scope.

## Control testing is a separate, opt-in session

Before any write, obtain explicit approval for the specific device, procedure,
target values and operator. Establish an accessible stop mechanism and a safe
physical setup. A static capability report is **not permission to execute**.

The transport/application must implement security, Control Point indications,
control acquisition, serialized procedures, timeouts, response handling and
ownership loss. Check equipment-supported ranges and the operator-approved limit.
Begin with the least intrusive authorized procedure; do not automatically proceed
to Start/Resume, speed, inclination, resistance or power changes. A negative
response or timeout is a result to record, not a reason to retry endlessly.

Record every request, response and related status in order, including whether
an operation was queued, accepted, rejected, timed out or cancelled. Never send
duplicate live control writes to compare two implementations. Replay the same
captured bytes offline through both ports instead. Do not use these protocol
examples as an actuator-safety controller.

## Evidence storage and result policy

Use `docs/equipment-results/YYYY-MM-DD-model-platform.md` for reviewed reports.
No such report should be created merely to fill out a matrix. A pending plan uses
`not_run`, not `passed`. Results are one of `passed`, `failed`, `partial`,
`not_run` or `not_applicable`, per test. Preserve known failures and limitations.

Keep captures outside published packages. Review them for names, addresses,
serials, location, personal measurements and credentials before sharing. A
sanitized fixture may be proposed only with permission, provenance and a
specification-reviewed expected result; the library under test must not generate
its own expected answer. Do not modify the immutable codec-v1 fixtures to hide a
device quirk.

For each report distinguish:

- **Installation evidence:** which released artifact the consumer actually used.
- **Wire interoperability:** which characteristics/procedures exchanged real bytes.
- **Semantic evidence:** which values/results were independently checked.
- **Transport/lifecycle evidence:** which reconnect/security/timeout scenarios ran.
- **Unverified scope:** other models, firmware, platforms, controls and qualification.

## Report template

Copy this only when recording an actual session; never prefill a pass:

```markdown
# Equipment test: <model> / <platform>

Status: <partial / passed / failed>
Date and tester:
Equipment manufacturer/model/firmware:
Machine family and relevant configuration:
Client OS/Bluetooth adapter/transport-library versions:
Application source revision:
Package name/version and released-or-candidate status:
Artifact source and verified checksum/integrity:
Operator-approved scope: <telemetry only / named control procedures>
Physical safety arrangements (if controls approved):

## Reproduction
<Exact install command, example/application invocation, manual steps.>

## Results
| Check | Expected | Observed | Result | Evidence reference |
| --- | --- | --- | --- | --- |
| FTMS discovery and reads | | | not_run | |
| Feature/range interpretation | | | not_run | |
| Idle telemetry | | | not_run | |
| Active telemetry | | | not_run | |
| More Data / unavailable diagnostics, if observed | | | not_run | |
| Disconnect/reconnect | | | not_run | |
| Explicitly approved controls | | | not_run | |

## Sanitized captures and independent comparisons
<Files/hashes, capture permission and redaction notes. No private identifiers.>

## Failures and limits
<Open issues, firmware quirks, untested characteristics and controls.>

## Review
<Reviewer/date; exact compatibility claim supported by these observations.>
```
