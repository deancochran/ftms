# FTMS for C

Portable C99 codecs for Bluetooth Fitness Machine Service telemetry, features,
ranges, statuses and control messages. Keep your existing Bluetooth stack.

**Start here:** [install the released archive](INSTALL.md), then run the
[installed C/C++ quickstart](https://github.com/deancochran/ftms/blob/main/examples/c-client/README.md).
See the [release matrix](https://github.com/deancochran/ftms/blob/main/docs/released-packages.md)
for publication identity and evidence limits. This library does not manage BLE
connections or authorize physical controls.

**Release status:** C **0.2.0** is published as the independently versioned
[`c-v0.2.0` source release](https://github.com/deancochran/ftms/releases/tag/c-v0.2.0).
The generated archive described below is a local candidate even when it has the
same version; building it is not publication evidence. See the exact
[release record](../../docs/released-packages.md) and role-based
[support profiles](../../docs/support-profiles.md).

**Support profile:** `FullWire`, with `CapabilityEvidence`, `RangeInspection`,
`RecordPlanning` and `RecordAssembly`. This names transport-independent protocol
interfaces, not a complete equipment/server implementation.

Integrate through the [consumer adapter seam](https://github.com/deancochran/ftms/blob/main/docs/architecture.md#consumer-adapter-seam):
transport conversion, BLE/session lifecycle, retries, subscriptions,
UI/application policy and control safety remain outside this protocol package.

## Additive range inspection in 0.2.0

`ftms_inspect_range` and `ftms_inspect_range_with_format` report the caller's
selected layout, observed/expected byte counts, selected decode status and up to
two structural candidates. They do not select a profile from received bytes.
Malformed lengths/ranges produce `FTMS_OK` with diagnostic status; invalid API
arguments produce an error and leave output untouched. Read `value` only when
its corresponding status is `FTMS_RANGE_INSPECTION_VALID`.

Successful candidates do not prove physical units, device conformance or control
permission. Existing decoders and capability reports are unchanged. When retaining
a capability report, retain its input kind and explicit range options alongside
the inspection and pass those same options to capability evaluation. A failed
selected decode is not proof that the device lacks the characteristic.

The shared inspection corpus compares all report fields in both ports. The
measurement structural matrix additionally exercises 181,760 layout cases,
46 sentinel positions, 47 reserved bits and 650 C planning budgets. See source
checkout `shared/conformance/{inspection,measurement-matrix}/v1/README.md` for
contract identities, accounting and limitations. These assets are test-only,
not dependencies of installed C consumers.

## Contributor-only local source candidate

`python3 packages/c/scripts/source-bundle.py` (from the repository root) builds
`packages/c/build/source-candidate/ftms-c-0.2.0.tar.gz` and its SHA-256 sidecar.
This is an **unreleased local artifact**, not a published version or Git tag.
`SOURCE.json` distinguishes a release candidate from an archive built at a tagged
source commit and always records `released: false`: building an archive does not
mean that a registry has published it.
It contains the C sources, public headers, standalone CMake installation files,
license and exact source manifest. Build it with the consumer's target compiler;
one host archive is not portable across CPU/ABI targets. Repository conformance
tooling and canonical fixtures remain outside this minimal source candidate.

See `docs/device-readiness.md` for the implemented improvements and the remaining
SDK/hardware gates. Neither CMake packaging nor Cortex-M0 compilation proves a
BLE firmware image works.

**Status: implemented protocol surface.** This portable C99 library implements:

- Feature encoding/decoding with all 17 machine and 17 target masks and raw unknown bits;
- all five Supported Range encoders/decoders, using fixed-point integers;
- encoding/decoding for all six measurement families, retaining presence,
  unavailable values, More Data and malformed-input diagnostics;
- a bounded, transport-independent measurement packet planner that splits a
  complete snapshot at FTMS field-group boundaries for an actual value budget;
- Training Status and all 22 defined Fitness Machine Status codecs in both directions;
- all 21 Fitness Machine Control Point request codecs in both directions, and
  Control Point response codecs in both directions (including Spin Down speeds);
- static capability interpretation of caller-supplied discovery/read evidence,
  covering six measurement families, five range relationships, and 21 control
  operation declarations/prerequisites.

It does **not** implement BLE discovery, subscriptions, security,
or control authorization. Swift, Kotlin, TypeScript and Python are separate
language packages; their convenience modules and public interfaces need not match C.

## Build and consume

Public headers are `include/ftms/{ftms,control,measurement,status,capabilities}.h`.
All have C++ linkage guards. Compile the corresponding `src/*.c` files as C99; add
`include/` to include paths and link the C objects/archive from C or C++11.
For host archive builds, `make -C packages/c all` produces `build/libftms.a`.

The target library uses no allocation, floats, I/O, BLE/OS API, retained caller
pointers, VLA, or mutable globals. It has no hosted `string.h` dependency, although
an embedded compiler may emit memory/ABI helper calls that its runtime must
provide. The tested Cortex-M0 build does so. Compatible C/C++ compiler ABI is
required; no universal vendor-toolchain compatibility is implied.

The package has a CMake 3.16+ manifest for ordinary C99 builds and installs. Its
source package version is recorded in `VERSION` (the sole source-version
authority); publication is recorded separately in the release matrix. The CMake
package config and `ftms.pc` metadata read that file; no public version header is added.
`find_package(ftms CONFIG REQUIRED)`
exports `ftms::ftms`; package-version compatibility is same-major-and-minor, so
pre-1.0 minor versions are deliberately not considered compatible. The installed
`ftms.pc` derives its prefix relative to its own location and is relocatable.

```sh
CMAKE=/opt/android-sdk/cmake/3.22.1/bin/cmake \
  python3 packages/c/scripts/verify-cmake.py
```

That optional verification uses GCC/G++, Clang/Clang++, Ninja, and `pkg-config`
to build, install under a prefix containing spaces, move that prefix, and compile
and run C/C++ `find_package` consumers plus a C `pkg-config --static` consumer.
It also builds a small planner consumer through `add_subdirectory`. Python is
only a verification dependency, not a library build or use dependency.

A Make install target is also provided **in repository checkouts only**; the
minimal released archive ships CMake files, not the repository Makefile:

```sh
make -C packages/c
make -C packages/c DESTDIR="$PWD/stage" PREFIX=/usr/local install
# Headers: stage/usr/local/include/ftms; archive: stage/usr/local/lib/libftms.a
```

Installation writes only the requested prefix/staging root; do not run a privileged
system installation implicitly. Tests install into fresh isolated local prefixes
and compile/run C and C++ consumers against the installed archive and headers.

Measurement values use native raw integers, not display-unit floats. Follow
`measurement.h` for per-kind units and sentinel rules. Decode success may include
truncation/RFU/trailing diagnostics: it does not mean a payload is complete or safe
to act upon. Status decoders similarly return partial evidence with diagnostics.
Training text is a caller-owned UTF-8 byte span identified by offset/length, not a
retained pointer. Encoders reject noncanonical inputs. Buffer overlap rules and
unchanged-output error contracts are documented in each public header.

### Measurement packet planning

`ftms_measurement_plan` (or `_with_format` for an explicit wire profile) turns one complete immutable measurement snapshot into
caller-owned characteristic values. Supply a **value** byte budget, rather than
an ambiguously named MTU (ordinary ATT notification values are commonly
`ATT_MTU - 3`). Query the fixed packet count first with `packets == NULL` and
capacity zero, then provide that many `ftms_measurement_packet` objects. The
planner has no BLE/OS behavior, queueing, retransmission, or receive-side
reassembly. It preserves raw units and unavailable sentinels, never slices an
encoded byte stream, uses More Data on every non-final packet, and places the
mandatory instantaneous group in the final packet. The public bound is 32
packets of 64 value bytes; actual FTMS 1.0 layouts require fewer than 32.

### Measurement record assembly

`ftms_record_context` reassembles receive-side More Data fragments for one
caller-owned equipment connection and generation using the historical layout.
For an explicit alternate wire profile, use `ftms_record_format_context` with
`ftms_record_init_with_format`, `ftms_record_reset_with_format`, and
`ftms_record_feed_with_format`. Options are copied by value at initialization
and remain fixed until reinitialization; `NULL` selects the historical layout.
Initialize with an explicit kind, generation, and caller-tick maximum age, then
feed each complete characteristic value under that one profile. It performs strict
wire decoding and emits only `FTMS_RECORD_COMPLETE`; `out` is unchanged for
pending, invalid, expired, and generation-mismatch results. Reset or initialize
again at disconnect/generation change. It has no BLE lifecycle, clock, queue,
allocation, or lost-fragment detection: duplicate field groups and conflicting
Cross Trainer direction are rejected and discard pending data. The deadline is
measured by unsigned caller ticks from the first non-final fragment and does
not slide; an expired incoming final is discarded rather than combined with old
state. Inputs, context, and output must not overlap. Do not mutate public context
storage except through these APIs; reinitializing to change profile discards
pending fragments rather than attempting to guess a format boundary.

## Capability API

1. Build an `ftms_cap_snapshot` for **one** FTMS service instance/generation.
   UUIDs are full canonical display/network-order bytes; values are wire bytes.
   The caller owns raw data and decides discovery completeness and freshness.
2. For C.7-aware Feature property evaluation, call `_with_c7` with explicit
   `ftms_cap_c7_evidence` (and the same range profile for both passes). Legacy
   APIs pass NULL C.7 evidence: it is unknown, not false, so a present Feature
   adds an insufficient-evidence diagnostic and applicable operations are
   incomplete; size diagnostic buffers from that call rather than reusing old
   capacities.
3. Supply caller-owned buffers and call the matching evaluation API. Buffer
   capacities are element counts. A caller may use fixed arrays and reject a
   snapshot that exceeds them; the library imposes no arbitrary device limit.
4. Read `out.report`; `operations[opcode]` separately reports declaration,
   prerequisite state, and reasons. `ranges` use native range-kind order; power
   and heart-rate target-bit order is different. Observation indices retain the
   association with the caller's original raw snapshot.

Input/output objects and buffers must not overlap, and inputs must stay stable
during each call. Invalid arguments or insufficient capacity leave all outputs
and buffers untouched. `FTMS_OK` means evaluation completed, not that a device
is conformant or controllable. Invalid bytes are report evidence rather than an
API error; failed/security-required reads remain distinct from malformed bytes.
Even `FTMS_CAP_PREREQUISITE_SATISFIED` is **not permission to execute controls**.
See the [shared interpretation contract](../../shared/protocol/capability-discovery.md)
and [design notes](docs/design.md) for exact rules and base-operation semantics.

## Control Point API

`ftms_control_request` carries a wire opcode and tagged union of raw fixed-point
fields; the member comments in `control.h` state each unit/divisor. No floating
point conversion occurs in the library. `ftms_encode_control_request` and
`ftms_decode_control_request` reject unknown request opcodes, invalid Stop/Pause
and Spin Down values, wrong exact lengths, and UINT24 distance overflow.
Response decode retains unknown request/result bytes and marks them with
`unknown_request`/`unknown_result` for forward-compatible callers; malformed
structure remains an error. Responses are exactly three bytes except successful
Spin Down Start limits, which are seven bytes (two UINT16 0.01 km/h values).
Encode capacity is checked before any write and `written` is changed only on
success. The codecs do not decide whether a connection is permitted to control a
machine.

For an explicit resistance-command layout, use
`ftms_encode_control_request_with_format(request, options, out, capacity, written)`
and `ftms_decode_control_request_with_format(data, size, options, out)` with
`ftms_control_format_options`. Set `resistance_format` to
`FTMS_CONTROL_RESISTANCE_UINT8_TENTHS` for the two-byte request `04 7b` with
`resistance_tenth_level = 123`. This profile accepts integer numerators 0–255
(0–25.5 levels); negative/out-of-range numerators fail without modifying output.
The legacy functions, NULL options, or
`FTMS_CONTROL_RESISTANCE_SINT16_TENTHS` retain the ESR11 E8991 signed16-tenths
default (`04 7b 00` for that same numerator). No struct layout was changed.

Only opcode `0x04` is affected. Do not infer this choice from packet length,
measurement/range formats, feature bits or device identity. Status opcode `0x07`
remains signed16 tenths. The literal 1.0.1 request table conflicts with E8991;
the UINT8 option is an explicit alternative, not a replacement normative default.
The source-checkout-only `docs/specification-audit.md` records the reconciliation;
it is not included in installed C package artifacts. Selection does not authorize
a Control Point operation.

For simulation opcode `0x11`, `cw_hundredth_kg_per_m` retains its legacy public
name. E10187 / FTMS 1.0.1 Table 4.20 defines Cw as **unitless**, with unchanged
UINT8 / 0.01 wire resolution. No physical-unit conversion or struct rename is
introduced; current units must not be inferred from that legacy field name.

## Verification

```sh
make -C packages/c test            # host compilers, sanitizers, corpora, C/C++ consumers
make -C packages/c check-embedded  # optional Clang Cortex-M0 compile-only evidence
```

Host tests require GCC/G++, Clang/Clang++, `ar`, Python 3 and `jsonschema`.
Neither Python nor Node is required for ordinary library compilation/use. CMake
packaging evidence is host-only; no Android/iOS SDK manifest or device test is
established by those commands. Source-archive publication is recorded separately.
The tests read canonical corpora directly:

- codec v1: **97 passed, zero failed/unsupported/skipped**;
- additional bidirectional corpora: controls 41 cases / 72 assertions, values
  8 / 16, measurements 26 / 47, statuses 38 / 63;
- capability v1: **63 complete-report cases**, with schema/template/comparator
  regression tests; native tests additionally isolate all 17 target bits and
  verify invalid-argument/buffer guarantees;
- strict C99 and ASan+UBSan tests, 10,000 codec/capability/control fuzz iterations
  plus 10,000 measurement/status iterations, and six installed C/C++ combinations.

`requirements-test.txt` records the host schema dependency. `.github/workflows/native-c.yml`
defines real native CI checks; local verification is not evidence of a remote CI run.

See [verification.md](docs/verification.md) for exact commands, corpus hashes,
failures/corrections and limitations. No board execution, full embedded image
link, real-device interoperability, Bluetooth PTS, or qualification is claimed.

## Release packaging

`VERSION` is strict SemVer and the only C package version authority. A release-mode
archive requires a clean checkout whose HEAD is exactly `c-vVERSION`:
`python3 packages/c/scripts/source-bundle.py --release`. It does not create a tag,
publish, or contact a registry. Candidate mode deliberately permits a dirty tree.

See [INSTALL.md](INSTALL.md) for installed CMake, vendored source, FetchContent,
Conan and direct compiler usage. The same instructions are included in the source
archive. `find_package` is discovery, not downloading; choose an acquisition path
first. A compatible compiler builds the library for the consumer's CPU/ABI.

The bundled Conan 2 recipe supports `conan create . --no-remote`; repository test
consumers build and run C and C++ against `ftms::ftms`. The vcpkg overlay accepts an explicit,
verified local archive and SHA-512 for validation. After an immutable release URL
exists, `prepare-registry-recipes.py ARCHIVE --tag c-v0.2.0 --output NEW_DIRECTORY`
generates a public vcpkg recipe with its real SHA-512 for separate review. It
requires a clean tagged release artifact and never submits or publishes anything.

Both package managers have passed local Linux installed C/C++ consumer checks.
Neither **vcpkg curated registry nor ConanCenter availability** is claimed.
`verify-package-managers.py` repeats those checks against a chosen artifact.
The source-release CI additionally gates publication on standalone consumers on
Linux, macOS and Windows; remote runs are distinct from local evidence.

See [the maintainer release runbook](../../docs/releasing-c.md) for review, CI,
environment protection, commit/merge/tag approval and registry submission steps.
The [release-readiness record](docs/release-readiness.md) identifies the tested
local artifact, tool versions, failure corrections and remaining external gates.
