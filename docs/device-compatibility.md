# Device wire-layout compatibility

FTMS codecs default to the adopted historical layout. For known exceptional
wire layouts, pass an explicit range or measurement format option on every
**raw** decode and encode call that needs it. TypeScript supports this through
`decode/encodeFtmsRangeRaw` and `decode/encodeFtmsMeasurementRaw`; the existing
normalized `parseFtms*` functions and UUID registry retain their historical
layouts and do **not** accept these options. Applications needing an alternate
layout must use the raw API and normalize its values using the selected format.
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

- The new options apply to **raw codecs only**. Existing normalized measurement
  parsers, aggregate capability range interpretation, and measurement packet
  planning do not yet carry explicit format options. An application must not
  assume selecting a raw range profile changes any of those paths.
- Resistance **commands** remain separate from measurement and range layouts.
  Legacy command widths, rounding and scale require independently justified
  contracts and tests; no command format was changed by this work.
- An Open Trainer adapter still needs DataView conversion at the application
  boundary, app-facing optional fields/timestamps, rounding/default/error policy,
  and upstream parser, command, trainer and simulator tests. The pure package
  still accepts Uint8Array/ArrayBuffer, not DataView or transport objects.
- Open Trainer transport observations do not supply all aggregate capability
  evidence. Do not fabricate complete properties/read/discovery evidence.
- [FTMS 1.0.1](https://www.bluetooth.com/specifications/specs/fitness-machine-service-1-0-1/)
  is adopted (2024-10-01). A section-by-section normative delta audit against
  the pinned 1.0 text and mandatory Errata 23224 remains necessary; existence
  of 1.0.1 alone is not grounds to silently change the published defaults.
- A verified device corpus still needs model/firmware, properties, original
  bytes and independently observed displayed units. Nine compatibility cases
  are mostly synthetic; the CORE range is the only captured characteristic in
  this new corpus, with conditional scale interpretation explicitly recorded.

## Verification boundary

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
