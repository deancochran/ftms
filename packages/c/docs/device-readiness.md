# Device-readiness improvements — 2026-09-28

> Historical local evidence for the checkout identified below, including its
> then-unreleased 0.1.0 candidate. Not current release status; see the
> [release matrix](../../../docs/released-packages.md).

Source: `scaffold/native-capabilities`, HEAD
`41023a60cff6efdeef5e36730c3d7356a91d26b6`, dirty/local/unreleased.
This record distinguishes implemented host-verifiable improvements from the
remaining SDK and hardware work. It does not supersede the recorded corpus basis.

## Delivered

### Measurement packet planning and assembly

Public APIs in `ftms/measurement.h`:

- `ftms_measurement_plan`: validates an immutable complete measurement, queries
  required packet count, and fills caller-provided packets bounded by a supplied
  characteristic-value budget. Groups remain intact; mandatory instantaneous
  fields are in the final More Data=0 packet. Cross Trainer direction and
  unavailable sentinels are retained. Errors leave output/count unchanged.
- `ftms_record_init/reset/feed`: bounded receive context, disjoint optional-group
  assembly, caller-supplied generation/time, non-sliding expiry, strict malformed
  fragment rejection and output only on completion. No allocator, clock or OS.
  Generation rejection precedes expiry. Assembled `bytes_read` is zero because
  no single input span exists; standalone results retain their decoded length.

One context requires caller serialization. Generation checks are not locks.
COMPLETE does not prove lossless delivery: FTMS has no general record sequence
identifier. These APIs do not select BLE subscriptions or authorize controls.

Tests cover all six families at a 20-byte value budget, literal fragment bytes,
group preservation, too-small budgets/capacities, query/error atomicity, standalone
and assembled results, duplicate fields, direction contradictions, malformed/RFU
input, expiry/wrap, stale generations and output preservation.

### External equipment-session prototype

`/home/deancochran/Dev/ftms-equipment-trial` consumes a separately installed C
archive and headers. It implements **host-tested simulated equipment state**, not
a BLE service or SDK adapter:

- Feature encoding and C-port-encoded Control Point responses.
- Simulated mandatory Request Control, Reset, Start/Resume and Stop/Pause;
  no actuator connection exists. Optional target controls remain unsupported.
- Invalid Parameter for malformed known requests, Not Supported for unknown
  opcodes, CCCD/busy rejection, ownership and response-before-status sequencing.
- Bounded queued versus awaiting-confirmation state, backpressure retry without
  repeating accepted indications, per-procedure tokens and connection generations.
- Timeout poisoning until a new connection generation; late confirmations cannot
  finish a newer transaction. Subscription disable drops queued telemetry.
- Immutable measurement records using the packet planner, explicit submit-busy,
  and configurable payload budget. No fabricated unconditional Reset notification.

Session object is 2400 bytes on the host, of which the fixed packet queue is 2304.
This is intentionally simple, not an optimized small-MCU allocation strategy.
`make demo` currently runs the executable scenario suite; it is not a radio demo.
The adapter must serialize session access. Arbitrary callback reentrancy is not
supported; synchronous confirmation/disconnect paths are tested.

### Reproducible C consumption

- Independent candidate version `0.1.0` in `packages/c/VERSION`; **not released**.
- CMake 3.16+ source build, `ftms::ftms`, relocatable find-package exports and
  pkg-config metadata. Basic compilation does not need Python or Node.
- GCC/G++ and Clang/Clang++ installed consumers, moved prefixes containing spaces,
  pkg-config static linking and an add_subdirectory planner consumer all execute.
- Deterministic local source candidate with license and actual-file hash manifest.
  It intentionally omits repository test tools and canonical shared fixtures;
  therefore it is a source-installation artifact, not a self-contained conformance
  test distribution. Extract each changed candidate into a fresh build tree, or
  use a clean rebuild: reproducible zero timestamps can hide source changes from
  timestamp-based incremental build tools if archives are overlaid.
- Native CI now includes CMake consumer verification; workflow execution remains
  local-only evidence until a remote run is authorized and performed.

## Actual final checks

All passed:

```sh
make -C packages/c BUILD=build/readiness-final test
make -C packages/c BUILD=build/readiness-final check-embedded
CMAKE=/opt/android-sdk/cmake/3.22.1/bin/cmake python3 packages/c/scripts/verify-cmake.py
env -u TMPDIR pnpm verify
```

Native regression remains 97/97 original codec cases, 49/49 capabilities, and
188/188 additional directional assertions. Planner/assembler native units run
under strict warnings and ASan/UBSan. Existing 20,000 bounded fuzz iterations
remain codec/session-family tests, not a new claim of assembler fuzz coverage.
The actual final TypeScript run reports **512 tests** and passed packed-artifact
verification. No TypeScript files were edited by this implementation lane. Final
inspection found several TypeScript source files differ from the old pre-migration
HEAD, so this record does not assert byte identity for that separately evolving
source tree. Original codec-v1 JSON was checked byte-for-byte against HEAD and
remains unchanged. Unrelated workspace changes were preserved.

Equipment prototype: `make dependencybuild test sanitizer demo` passes with an
installed archive. Its consumer/session sources are sanitizer-instrumented;
that separate installed archive is not instrumented by the trial target.

Source candidate generated twice with identical bytes, extracted, clean-built,
installed and consumed by a C executable:

`build/source-candidate/ftms-c-0.1.0.tar.gz`

SHA-256: `5405ac927ccfe5b56a5ffc07c0105cfbd813ee2ce076362945f50e495a876922`.

Clang Cortex-M0 compilation passed. Per-function static frames: planner 312 bytes,
record feed 368 bytes. These are not whole-call-chain stack bounds, linked-image
size or RTOS high-water measurements; compiler memory/ABI helpers still need a
target runtime.

Independent review found and prompted fixes for malformed control response
mapping, mandatory virtual base procedures, equal-generation token reuse,
fabricated status events, assembler result metadata and serialization contracts.

## Remaining gates — not implemented or verified

| Original improvement | Remaining work |
| --- | --- |
| Embedded reference target | Select exact BLE-capable board and pin SDK/toolchain; ESP-IDF/Zephyr are not installed in this environment |
| Equipment-side BLE example | Register real GATT service, map stack callbacks/buffer ownership to the tested session, compile/link/boot firmware |
| MTU/backpressure | Radio validation of planner/assembly, dropped fragments and per-peer limits; telemetry age/drop policy in actual adapter |
| Session lifecycle | SDK indication confirmation, service changes, buffer exhaustion, multi-client policy, security and safety integration |
| API ergonomics | Independent new-developer SDK trial and feedback; no claim every ergonomic issue is resolved |
| Source release | Maintainer review and explicit tag/publication authorization; current artifact is only a candidate |
| Second stack | Real Zephyr/Nordic module integration and build; no untested placeholder manifests added |
| Interoperability | Named board/firmware/phone/equipment matrix, device execution, Bluetooth qualification and separate product safety processes |

No SDK download, system installation, firmware flashing, production action,
device-control write, commit, push, tag or publication occurred in this work.
