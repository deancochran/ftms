# Device wire-layout compatibility

Current API guidance is followed by historical local verification. Claims about
what was unpublished in that recorded run do not describe current availability;
see the [release matrix](released-packages.md).

FTMS codecs default to the adopted historical layout. For known exceptional
wire layouts, pass an explicit range or measurement format option on every
raw decode and encode call that needs it. TypeScript also accepts measurement
options on normalized `parseFtms*` parsers and registry dispatch, and range
options on normalized resistance-range decoding and capability evaluation.
Omitted options preserve historical layouts.
C exposes the corresponding `_with_format` APIs. Do not auto-select an option from device
name, advertised features, a range length, measurement flags, or a prior
control request. Range, measurement, and command decisions are separate.

In TypeScript, omitted options (`undefined`) or an empty options object select
defaults. Null, primitives, arrays, unknown keys and invalid format values are
rejected. A signed-resistance **range** option is invalid for other range kinds.
For **measurements**, each option applies only to fields present in its defined
families (resistance: Cross Trainer/Rower/Indoor Bike; pace: Treadmill); the other
option has no effect for that family, identically in C and TypeScript. This lets
one explicit measurement-format object carry independent settings without
changing unrelated fields. Neither option changes Control Point operand formats.

Raw codec values remain raw integers in the selected format. Application code
may apply a caller-owned profile to normalize them only after selecting and
recording that profile. No option grants permission to issue a control command.

## Evidence-backed gap ledger (2026-09-28)

This is a bounded audit, not a claim to identify every firmware variant. Both
implemented ports (TypeScript and C) share the raw format options and regression
corpus. Swift and Kotlin remain scaffolds, not validated implementations.

| Gap | Evidence and limits | Disposition across implemented ports |
| --- | --- | --- |
| Resistance measurement width and scale | [Star Trac first-hand report](https://stackoverflow.com/a/79157774): two-byte signed tenths on bikes/ellipticals; exact models, firmware and complete capture unavailable | Explicit signed16-tenths raw encode/decode for bike, cross trainer and rower; synthetic regression fixtures, not device validation. Rower support is a format capability, not evidence of that device scale. |
| Resistance range width | [KICKR CORE, firmware 3.0.23](https://github.com/natrontech/wattroom/issues/43#issuecomment-5462827007): `00 00 64 00 01 00` | Explicit six-byte signed min/max, unsigned increment codec. Divisor 10 is caller-selected interpretation; capture proves width, not scale. Default three-byte layout preserved. |
| Treadmill pace width | Same Star Trac report: 3,449 notifications, flags `0x17fe`, 32 rather than 34 bytes | Explicit uint8 raw pace option; uint16 default preserved. Display units remain unresolved; no normalized conversion invented. |
| Historical resistance units are inconsistent | [2017 XML import](https://github.com/oesmith/gatt-xml/tree/4fd2ede1d3da9365fdc6dec89290c346581a03f9): bike/rower signed16 resolution 1, cross trainer and range 0.1 | Do not describe signed16-tenths as a universal legacy profile. Separate whole-unit signed16 semantics and normalized APIs remain open. |
| Direction-specific speed units | [Vitalwalk Apollo 11 Max / TM11GY report](https://github.com/cagnulein/qdomyos-zwift/issues/5100): `02 64 00` reportedly sets 1 mph while telemetry uses km/h | Open caller-profile work. Keep telemetry, range, command and status units independent; no global mph mode. Owner report includes AI-assisted analysis, firmware and independent reproduction unavailable. |
| Start/Resume and subscription side effects | Same Vitalwalk report: `07` reportedly toggles running state; enabling indications reportedly stops belt once | Session/transport safety policy, not a changed opcode definition. No automatic start-before-target or hardware probing added. Success response does not prove intended physical effect. |
| Rower pace at rest | [JOROTO MR280PRO report](https://github.com/cagnulein/qdomyos-zwift/issues/4986): `2c 0b 00 00 00 00 00 00 ff ff 00 00 00 00 00 00 00 58 00 00` | Both raw decoders retain pace 65535; device-specific rest/unavailable interpretation remains open. Do not introduce a global sentinel without normative support. |
| Zero or missing telemetry | [Life Fitness ellipticals](https://github.com/cagnulein/qdomyos-zwift/pull/4818): zero speed despite advancing distance; [split rower packets](https://github.com/cagnulein/qdomyos-zwift/pull/4956) | Preserve zero versus absence. Derived speed and fragment accumulation require caller-owned freshness/generation policies. Reports lack sufficient complete capture/model evidence for a core workaround. |
| Reserved Training Status | CORE capture `fb ff` | Existing decoders preserve reserved value/flag diagnostics. No invented idle state or control permission. |
| Cross-trainer flag width | [BH report](https://github.com/dudanov/python-pyftms/issues/71) | Three-byte flags already implemented in both ports; no demonstrated core defect. |
| Advertisement machine type absent | [Bodytone DU30 report](https://github.com/dudanov/python-pyftms/pull/67) | Existing capability discovery uses observed GATT characteristics, not advertisement/model allowlists. Missing observations must remain unknown. |

## Open integration and normative work

- The selected option must be supplied consistently to each related decode,
  capability pass, and (in C) measurement-planning or record-assembly pass.
  Legacy C record APIs retain the default layout; format-aware record contexts
  copy one explicit profile at initialization and reinitialization discards
  pending fragments before changing it.
- Resistance **commands** remain separate from measurement and range layouts.
  Commands now have an independent explicit UINT8-tenths option matching the
  literal FTMS 1.0.1 Table 4.15. ESR11 E8991 directly supports the preserved
  signed16-tenths default; the source conflict remains unresolved. See the
  [audit and usage](specification-audit.md). Neither range nor measurement
  selection changes the command format.
- An Open Trainer adapter still needs DataView conversion at the application
  boundary, app-facing optional fields/timestamps, rounding/default/error policy,
  and upstream parser, command, trainer and simulator tests. The pure package
  still accepts Uint8Array/ArrayBuffer, not DataView or transport objects.
- Open Trainer transport observations do not supply all aggregate capability
  evidence. Do not fabricate complete properties/read/discovery evidence.
- [FTMS 1.0.1](https://www.bluetooth.com/specifications/specs/fitness-machine-service-1-0-1/)
  is adopted (2024-10-01). The [focused normative audit](specification-audit.md)
  checks all service sections against the pinned 1.0 text, resistance by
  direction, pace, unavailable values, ESR11 E8991/E9135 and Errata 23224.
  It adds explicit UINT8-tenths commands while preserving the erratum-backed
  default. The recovered official annotated comparison now attributes all nine
  errata listed in 1.0.1's history, including cadence-flag and Cw-unit corrections
   missed by the first text-only pass. Source conflicts and Cw API limitations
   remain explicit in the audit; C.7 static compatibility is implemented, while
   bonded-reconnection indication and CCCD behavior remain transport limitations.
- A verified device corpus still needs model/firmware, properties, original
  bytes and independently observed displayed units. Nine compatibility cases
  are mostly synthetic; the CORE range is the only captured characteristic in
  this new corpus, with conditional scale interpretation explicitly recorded.

## Verification boundary

### Format-aware receive assembly follow-up

Pulled `main` and fast-forwarded the working branch to
`ba182b1a68a80774f23bf36a13bfdf8200ac66cf` before delivery. The new
`ftms_record_format_context` copies its profile at initialization and retains it
across resets; reinitialization discards any pending update. Existing context
layout and record API signatures are unchanged.

`make BUILD=build/record-formats test` and `env -u TMPDIR pnpm verify` passed
locally, including 532 TypeScript tests, native strict/sanitized suites, all
shared corpora, 20,000 deterministic fuzz inputs and installation/source-artifact
consumer checks. New tests use literal alternate-format bike and treadmill
fragments, verify copied profile lifetime, independent contexts, reset/reinit,
invalid input, duplicate fields, direction changes, expiry, timestamp wrap and
generation boundaries. A CMake consumer links and calls the new record APIs.
These remain host protocol tests, not physical-device or embedded execution.

### Format propagation follow-up

Verified locally on `release/ports-installation-readiness`, base
`65fc11f0a137f42f3b1d0556e893a35e48f217ea`, with uncommitted changes:

- `env -u TMPDIR pnpm verify`: 532 tests in 12 files, lint/types/build and packed
  package checks passed. Tests include all three normalized resistance families,
  registry and deprecated bike dispatch, unknown-unit legacy pace omission,
  complete selected-profile capability reports, and preserved range error results.
- `make BUILD=build/format-propagation test`: passed strict/sanitized tests,
  original 97 vectors, 49 capability cases, 18 compatibility assertions, both
  10,000-input fuzz suites, installed C/C++ and source-artifact consumers. New
  native tests verify literal planned packet bytes, profile-dependent counts,
  indivisible field groups, invalid options and unchanged outputs on errors.
  The CMake consumer also links and calls the three new format-aware APIs.
- Independent review findings (normalized profile validation and contradictory
  README guidance) were fixed and re-reviewed. The full TypeScript suite passed
  after those fixes. An initial added capability expectation omitted the new
  six-byte observation length; the literal expectation was corrected.

Canonical corpus JSON and comparison READMEs were not modified. Capability
protocol-contract SHA-256 is
`a50e3a7a00d39afeec8ead6594b6d6de065bc3a09b3ae9e883bda28d3d1b3742`;
wire-compatibility contract SHA-256 is
`b0a7dcbfceeae84382be1417c7185bf070d8cc400d965b5c3b1fdad7a479b6f4`.
Native reports record all corpus/schema/comparison hashes and case accounting.
C receive assembly has a separate format-aware context API; legacy assembly
remains historical-only and alternate fragments require their matching copied
record profile.

### Earlier raw-codec verification

The shared compatibility corpus has 9 cases and 18 independent encode/decode
assertions per implemented port. Native runner reports include exact corpus,
schema and comparison-contract hashes. See
`shared/conformance/compatibility/README.md` for accounting. Full local
`env -u TMPDIR pnpm verify` and `make BUILD=build/compat-final test` passed after
the initial fixture profile mismatch and formatting failures were corrected.
This is host protocol evidence, not physical equipment, embedded runtime,
Bluetooth qualification, released-package or Open Trainer integration evidence.
No compatibility release has been published.

Independent focused review found no concrete blocker in the supported raw
format paths. Follow-up tests cover signed measurement extrema, invalid
selection/bounds, short-buffer atomicity, and TypeScript explicit-default
equivalence. Remaining verification work includes a shared malformed/truncated
format matrix, explicit C NULL-option equivalence, and focused range encoder
atomic-error canaries; the valid-case corpus does not replace those checks.
