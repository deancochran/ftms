# FTMS layout compatibility inventory

This inventory distinguishes required wire structure, explicitly supported
variants and implementation limits. Source identities and unresolved ambiguities
are pinned in [specification audit](specification-audit.md), rather than replaced
by device-name heuristics or guesses based on packet length.

## Fixed and procedure-specific structures

| Surface | Current layout policy | Source / decision |
| --- | --- | --- |
| Fitness Machine Feature | Exactly 8 bytes; two UINT32 words | FTMS §4.3 and characteristic definition. Retain unknown bits; no extra-word inference. |
| Speed Range | 6 bytes; unsigned minimum/maximum/increment, hundredths | FTMS §4.11 and GSS characteristic definition. Strict length remains. |
| Inclination Range | 6 bytes; signed minimum/maximum, unsigned increment, tenths | FTMS §4.12 and characteristic definition. Strict length remains. |
| Resistance Range | Default 3 unsigned bytes; explicit 6-byte signed-min/max alternative | FTMS §4.13, GSS §3.231; source unit annotations remain ambiguous. New inspection distinguishes selected mismatch and structural alternatives. |
| Power Range | 6 bytes; signed minimum/maximum, unsigned increment, watts | FTMS §4.14 and GSS §3.230. Strict length remains. |
| Heart Rate Range | 3 unsigned bytes, beats/minute | FTMS §4.15 and characteristic definition. Strict length remains. |
| Control requests | Exact opcode-specific lengths | FTMS §4.16 and applicable errata. Default resistance is SINT16 tenths per E8991; literal-table UINT8 tenths is separate explicit selection. |
| Control responses | Procedure-dependent parameters | Ordinary response prefix is 3 bytes; successful Spin Down can include 4 parameter bytes. Do not treat all responses as fixed at 3. |
| Training Status | 2-byte prefix, optional UTF-8 string controlled by flags | FTMS §4.10; preserve raw string/diagnostic distinctions. |
| Machine Status | Known opcode-specific structures, up to 11 bytes | FTMS §4.17. Resistance status remains SINT16 tenths; unknown opcodes are not guessed. |

The codec implementations are `packages/typescript/src/{features,control,parsers}.ts`
and `packages/c/src/{ftms,control,measurement,status}.c`. The additive inspection
surface concerns Supported Ranges; it is not a universal packet-format detector.

## Flag-driven measurement structures

| Family | Flag bytes | Complete default bytes | Largest supported layout |
| --- | ---: | ---: | ---: |
| Treadmill | 2 | 36 | 36; legacy pace alternative is 34 |
| Cross Trainer | 3 | 40 | 41 with signed resistance |
| Step Climber | 2 | 23 | 23 |
| Stair Climber | 2 | 23 | 23 |
| Rower | 2 | 29 | 30 with signed resistance |
| Indoor Bike | 2 | 29 | 30 with signed resistance |

These complete-layout sizes are not required notification lengths. Field presence
comes from flags, More Data changes mandatory-field presence, and records may be
split across notifications. The packet itself and the selected explicit profile
determine decoding; Feature declarations or equipment identity do not determine
field presence. Field ordering, grouped fields, sentinel applicability and
reserved-bit rules derive from FTMS §§4.4–4.9 and characteristic definitions.

Default resistance telemetry is UINT8 whole levels; Cross Trainer, Rower and Bike
can independently select signed16 tenths. Treadmill pace is normally UINT16;
the legacy UINT8 option does not establish normalized physical units. Do not
transfer a range-profile choice into either measurements or commands.

## Observation and resource boundaries

- A successful read can fail decoding under a selected profile. Preserve both
  facts; absence, read failure and interpretation failure are not interchangeable.
- Capability-v1 reports do not include profile provenance. Retain inspection,
  kind, bytes and options separately; pass the same explicit options to evaluation.
- C planner storage is 64 bytes per planned value and at most 32 packets. Current
  supported complete layouts fit. These are not universal incoming GATT limits.
- Example capture/replay buffers and simulation limits are harness policies,
  not additional requirements imposed by FTMS on equipment.
- Valid structural candidates do not prove units or provide permission to control
  equipment. The KICKR pilot establishes observed width and host decoding only.

## Follow-up, not silently included

Pure advertising Service Data codecs and a TypeScript production record assembler
remain separate potential milestones. Future/unknown layouts need explicit
contract additions, not permissive reinterpretation of bytes. Independent device
or vendor evidence is still needed to settle ambiguous physical scaling.

See [verification](compatibility-verification.md) for exact generated-case counts,
shared contract identities, installed-consumer evidence and qualification limits.
