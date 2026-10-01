# FTMS for Rust

`ftms` is an independent Rust crate for pure FTMS binary data. Version 0.1.1 is
published on crates.io, including the normalized range/control/status projections.
See the [verified release evidence](https://github.com/deancochran/ftms/blob/main/docs/released-packages.md#published-rust-011).
It is `#![no_std]`, allocation-free, safe (`#![forbid(unsafe_code)]`), and has no
runtime dependencies. It does not own Bluetooth, permissions, device lifecycle, or
control safety.

**Support profile:** [`FullWire`](https://github.com/deancochran/ftms/blob/main/docs/support-profiles.md)
raw codecs with `RangeInspection`, `CapabilityEvidence`, `RecordPlanning`,
`RecordAssembly`, and `NormalizedViews`.
The release matrix records archive identity and public-consumer evidence separately.

Integrate through the [consumer adapter seam](https://github.com/deancochran/ftms/blob/main/docs/architecture.md#consumer-adapter-seam):
transport conversion, BLE/session lifecycle, retries, subscriptions,
UI/application policy and control safety remain outside this protocol package.

Select a compatible current release in your application:

```sh
cargo add ftms
```

Retain the saved dependency and, for applications, Cargo.lock. To reproduce the
recorded release specifically, use `cargo add ftms@=0.1.1` instead.

For the published crate, see [crates.io](https://crates.io/crates/ftms/0.1.1)
and then see the existing [raw measurement and status interfaces](#raw-measurement-and-status-interfaces)
before the contributor [toolchain and verification](#toolchain-and-verification)
instructions below.

## Implemented surface

Raw, bidirectional codecs are supported for:

- the eight-byte Fitness Machine Feature characteristic, retaining reserved bits;
- all five Supported Ranges (Speed, Inclination, Resistance, Heart Rate, Power);
- explicit caller-selected `Uint8Whole` or `Signed16Tenths` resistance range
  layouts and non-selecting inspection reports with both candidates;
- all 21 Control Point requests and raw responses, including the optional
  successful spin-down speed operands and retained unknown/trailing diagnostics;
- all six measurement families: Treadmill, Cross Trainer, Step Climber, Stair
  Climber, Rower and Indoor Bike; and
- Training Status and all 22 defined Machine Status opcodes, including retained
  malformed/unknown evidence on decode and canonical encoding.

Feature decoding rejects both payloads shorter than eight bytes and payloads with
trailing bytes (`Error::WrongLength`). This matches the raw Feature contract.
No typed feature interpretation is exposed yet, so callers can retain forward
compatibility rather than having unknown bits discarded.

Range, measurement and control-request format selections are separate
caller-owned options; neither is inferred from bytes, ranges, features, or a
device. Encoders take caller-owned mutable buffers and return
`Error::InsufficientStorage` without writing when capacity is inadequate.

`capabilities::evaluate_capabilities` evaluates only caller-owned discovery/read
evidence with caller-selected `RangeOptions` and a fixed diagnostic capacity. Its
result has declarations, prerequisites and reason flags, but deliberately has no
`canExecute`/permission result. UUIDs are native 16-byte display-order values;
read bytes remain borrowed by the caller.

`normalized::normalized_measurement` projects selected raw fields to named
physical units. It returns `None` for absent/incomplete fields and
`NormalizedValue::Unavailable` for selected sentinel values, never a fabricated
physical zero. `records::plan_measurement` emits bounded characteristic values
for a caller byte budget, and `RecordAssembler` combines caller-delivered
fragments under explicit generation and caller-clock age inputs. Neither owns a
timer, connection, subscription, or BLE/GATT operation.

Not implemented: BLE/GATT operations. Rust real-device
interoperability remains unverified. This is partial FTMS conformance evidence,
not Bluetooth qualification.

## Raw measurement and status interfaces

Import measurements from `ftms::measurement` and statuses from `ftms::status`.
`decode_measurement`/`encode_measurement` operate on `RawMeasurement` and explicit
`MeasurementOptions`. `MeasurementField::index()` addresses one of the 30 raw
integer slots; `MeasurementField::mask()` addresses the corresponding bit in
`present`/`unavailable`. `MeasurementKind` selects the characteristic, not a
manufacturer or model. Rustdoc includes executable encoding examples.

- `present` distinguishes a complete field from an absent or incomplete field.
  A defined unavailable sentinel sets both masks and leaves its value slot zero;
  it must not be presented as a physical zero.
- Flags, including More Data and Cross Trainer direction, are retained. Missing
  flag bytes are `WrongLength`; later incomplete fields return a partial report
  with `truncated`. `bytes_read` stops after the last complete field. RFU flags
  and trailing bytes are reported, not silently guessed into a different layout.
- Encoders require the exact presence mask selected by the flags and reject RFU
  flags, invalid sentinel masks and out-of-width values. Use `RawMeasurement::new`
  then set flags, masks and raw values. Derived decode metadata is not encoder
  input; encoding a complete report with trailing bytes omits those extra bytes.
  Retain original packets separately if lossless diagnostic replay is needed.
- The maximum current complete measurement encoding is 41 bytes; this is not a
  BLE MTU or notification size assumption. No fragment assembly is performed.
- All buffer encoders validate before writing. Errors leave the entire output
  buffer unchanged; success writes only the returned prefix.

### Wire integers and units

The raw codec does not perform these conversions. The table documents selected
wire units, not independent physical scaling validation on equipment.

| Raw fields | Interpretation of ordinary raw integers |
| --- | --- |
| Speed, AverageSpeed | /100 km/h |
| Distance | metres |
| Inclination; RampAngle; Met | /10 percent; /10 degrees; /10 metabolic equivalents |
| PositiveElevation, NegativeElevation | Treadmill /10 metres; other families whole metres |
| InstantaneousPace, AveragePace | Default Treadmill and Rower: seconds/500 m; legacy Treadmill: raw evidence, display unit unspecified |
| Energy; EnergyPerHour; EnergyPerMinute | kcal; kcal/hour; kcal/minute |
| HeartRate; Elapsed, Remaining | bpm; seconds |
| Force; Power, AveragePower | newtons; watts |
| StepRate, AverageStepRate | steps/minute |
| StrideCount | Cross Trainer /10 strides; Stair Climber whole strides |
| FloorCount; StepCount; StrokeCount | floors; steps; strokes |
| StrokeRate, AverageStrokeRate; Cadence, AverageCadence | /2 strokes/minute; /2 revolutions/minute |
| Resistance | Default unsigned whole levels; explicitly selected signed16 tenths: /10 levels |

Only defined fields have unavailable sentinels: inclination/ramp angle and
Treadmill force/power use `0x7fff`; energy uses `0xffff`/`0xff`; Cross Trainer step
rates use `0xffff`. For example, Bike/Rower/Cross Trainer power `+32767` is a valid
number, not unavailable. Use masks, not value-based sentinel guesses.

`MeasurementOptions::default()` selects `MeasurementResistanceFormat::Uint8Whole`
and `TreadmillPaceFormat::Uint16`. Alternatives are `Signed16Tenths` and
`Uint8Legacy`. Options only affect applicable fields. They are never inferred
from packet length, ranges, Features, other formats, or equipment identity.

`decode_machine_status` returns `RawMachineStatus` with raw opcode/action and an
optional `ControlRequest`-shaped parameter in raw wire units. This represents a
reported target, not a request to execute it. Unknown opcodes and incomplete
parameters remain diagnostic evidence. Resistance status `0x07` always uses
signed16 tenths regardless of request options. Stop/Pause actions are 1–2;
Spin Down **status** actions are 1–4, unlike Spin Down **request** actions 1–2.

`decode_training_status` returns `RawTrainingStatus<'a>` borrowing text bytes from
the packet. Invalid UTF-8 is retained and flagged without allocation or lossy
replacement. Text length is caller-bounded, with checked output sizing and no
arbitrary protocol string limit. On an incomplete header, zero-initialized code
storage is not a received training state. Set `flags`, `code` and `text` on a
default report for fresh encoder input. Both status encoders reject diagnostic
states; decoded text offsets and descriptive booleans do not override flags.

## Toolchain and verification

See [`docs/verification.md`](docs/verification.md) for the supported raw-codec
matrix and local evidence. [`docs/releasing.md`](docs/releasing.md) describes the
CI matrix, tag-triggered crates.io publishing, authentication and pending delivery
gates. Publishing is a pipeline operation, not a manual local Cargo login/upload.

The declared MSRV is Rust **1.85.1**. `rust-toolchain.toml` pins verification to
the tested `1.85.1` compiler with `rustfmt`, Clippy, and the Cortex-M0 target.
The compiler installation itself is intentionally local and ignored under
`packages/rust/.toolchain/`; no global default or shell profile is changed.
Checkout-only package/consumer/release tooling requires Python **3.12+**; the
distributed Rust crate does not depend on Python or that tooling.

Host tests read canonical fixtures directly and validate available JSON Schema
Draft 2020-12 schemas before execution. Each corpus report
includes source HEAD/dirty state, its schema hash when it has a schema, vector
or fixture hash, README/contract hash, case and assertion totals, and all
non-passes/runner errors. Inspection has no schema asset, so its report records
`schemaSha256=none`. Values-v1 executes 8 cases / 16 literal directional
assertions, inspection executes 9 complete reports, and controls-v1 executes
41 fixtures / 72 directional assertions. New measurement/status/compatibility
corpora cover **26 / 38 / 9 cases** and **47 / 63 / 18 directional assertions**.
The independent shared structural matrix covers **181,760** measurement layouts
in both directions, 46 sentinel cases, 47 RFU cases and 315 incomplete prefixes.
Tests also cover malformed lengths, widths, action values, buffer capacity,
UTF-8, all Training Status flags/codes, and selected-profile independence.
The deterministic 10,000-packet malformed-input regression is separate from the
shared corpus and is not coverage-guided fuzzing or device evidence.
Fixture hashes and source identity remain run evidence, not package or
specification versions.

The immutable codec-v1 corpus has 97 cases. The host-only adapter for 0.1.1 validates the
canonical schema and executes all categories with 97 passes, zero failures,
unsupported cases or skips. `normalized` exposes typed Features, `normalize_range`,
`normalize_control_request`, `normalize_control_response`, and
`normalize_machine_status`, plus measurement metrics. Range/control/status
projections are new since 0.1.0; that release already includes Feature and
measurement views, capability evidence, and record planning/assembly.
The adapter's mappings retain raw codec APIs: codec-v1 wheel circumference
millimetres maps to its 0.1 mm wire integer, and rejected raw responses map to the
contract's `malformed_response` result rather than changing raw `Error` variants.

From this package directory, verify with:

```sh
# Only for the isolated toolchain installed in this checkout:
export CARGO_HOME="$PWD/.toolchain/cargo"
export RUSTUP_HOME="$PWD/.toolchain/rustup"
export PATH="$CARGO_HOME/bin:$PATH"

cargo fmt --check
python3 -m unittest discover -s scripts -p 'test_*.py' -v
rustfmt --check --edition 2021 tests/fixtures/consumer.rs
cargo clippy --locked --all-targets -- -D warnings
cargo test --locked
cargo test --locked --test raw_conformance --test measurement_status_conformance \
  --test measurement_matrix -- --nocapture --test-threads=1
cargo build --locked --target thumbv6m-none-eabi
RUSTDOCFLAGS='-D warnings' cargo doc --locked --no-deps
cargo package --locked --allow-dirty
sh tests/consumer.sh
```

The consumer check honors `TMPDIR`. Prefer an approved temporary directory;
this host's `/tmp/opencode` was not writable, so verification used `/tmp`.
Runner self-tests deliberately catch injected panics; `--nocapture` prints those
messages while the self-tests pass. They are not hidden conformance failures.

The embedded command is a compile-only `no_std` Cortex-M0 check, not a link,
runtime, device, PTS, or Bluetooth qualification result. The consumer script
packages the crate and builds an isolated temporary consumer against the packed
source; it does not publish anything. The source-checkout corpus tests are
excluded from the `.crate`, because their canonical shared fixture path is
intentionally not copied into a distributable package.
