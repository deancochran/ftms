# Page-by-page FTMS implementation audit

## Audited text and checkout

This is an implementation audit of the **81 physical pages** of the recovered
FTMS 1.0 → 1.0.1 annotated comparison, not another version-difference summary.
The adopted 1.0.1 PDF resolves tracked deletions/insertions; ESR11 and GSS remain
separate sources where applicable. The comparison is courtesy material, not a
replacement governing specification. [Source identities and erratum mapping](specification-audit.md).

Comparison PDF SHA-256:
`0b2c150a6c3fb50520d04bb00e3632ff8d9d880d1578c9c6b51b75db455ce21a`.
Adopted PDF SHA-256:
`0d28454790276aab48350ae991ff6df83aaaa9bb9c52b65b89f26d261ce8f89e`.

`pdftotext -layout` extraction retains form-feed page boundaries. It produced
81 comparison pages and 78 adopted pages, with no missing/empty page silently
discarded. Full text stays in local project context, not package assets:

- `.context/ftms-audit/redline-pages/page-001.txt` through `page-081.txt`;
- `.context/ftms-audit/adopted-pages/page-001.txt` through `page-078.txt`;
- each directory's `manifest.json` records page number, filename, character
  count and SHA-256 of the extracted page.

Paths above are relative to the machine-local worktree workspace, not the
product checkout. Product base is `2b5ff79b81639e8beeea8bc9b219cbf78c2c7194`,
branch `audit/ftms-1-0-1`, with the existing uncommitted command-profile work.
The local `implementation-manifest.json` pins 93 source/header/test/corpus files
in the reviewed snapshot; SHA-256:
`051283e34fc0c99ad26e46a307d3f267a7ca20274d1643001e0fde65eeffaa46`.
This audit does not modify production behavior or silently repair findings.

## How to read the results

- **Checked**: the stated byte-level behavior was inspected in both implemented
  ports and linked to existing literal tests. This is not exhaustive proof of
  every possible input or compliance of an equipment product.
- **Partial**: some page requirements are implemented, but a specific gap,
  source conflict, or non-codec obligation prevents an overall passing verdict.
- **Outside**: BLE/GATT hosting, security, ownership, actuator/session behavior,
  SDP or other caller responsibilities, not implemented by these pure packages.
- **No runtime requirement**: cover/history/contents/legal/reference material;
  accounted for, not counted as a passed codec test or legal qualification.

Raw evidence preservation is not server conformance validation: retaining RFU
bits on decode does not mean a compliant server may transmit them. Likewise,
encodable bytes do not prove command permission, valid equipment state, range
enforcement, physical behavior, or data freshness. A test-only TypeScript
session reducer is not a production record assembler. Swift/Kotlin are scaffolds
and are not included as implemented ports.

## Evidence references

Paths in the page ledger are relative to the product root. These abbreviations
name concrete sources and test suites rather than a claim that all requirements
in a source file are covered:

- **Endian**: TypeScript `src/features.ts` raw feature/range DataView reads and
  writes; `src/control.ts` request reads/writes; `src/parsers.ts` field readers.
  C `src/ftms.c:read_u16le/read_u32le/write_u16le/write_u32le`, with corresponding
  helpers in `control.c`, `measurement.c`, `status.c`. Literal shared values
  cases `feature-unknown-bits`, `inclination-signed-extrema`, `power-negative`
  test byte order independently through both port adapters.
- **Families**: TypeScript `src/constants.ts:FTMS_DATA_CHARACTERISTICS` and six
  `parseFtms*Data` functions in `src/parsers.ts`; C
  `include/ftms/measurement.h` six measurement kinds and `src/measurement.c:defs`.
  `packages/typescript/test/measurements.test.ts` and shared
  `conformance/measurements/v1` cases exercise all six families.
- Unless a full path is shown, TS source/test paths have prefix
  `packages/typescript/`, C source/test paths have prefix `packages/c/`, and
  shared corpus paths have prefix `shared/`.

## Page ledger

| PDF page | Contents / requirements checked | Implementation and verification disposition |
| ---: | --- | --- |
| 1 | Cover, identity, courtesy-comparison warning | **No runtime requirement.** Identity verified against downloaded PDF; use adopted text for final rules. |
| 2 | Draft revision history, including superseded split-record ideas | **No runtime requirement.** Historical draft statements are not implemented as current requirements; final More Data rules are audited below. |
| 3 | Draft revisions: Request Control, statuses, stop/pause and spin down | **No runtime requirement.** Current messages and procedures are checked on their normative pages, not inferred from revision notes. |
| 4 | Adoption history, nine erratum IDs, acknowledgment heading | **No runtime requirement.** IDs reconciled to direct annotations in the source audit. |
| 5 | Acknowledgments | **No runtime requirement.** Not a codec or test obligation. |
| 6 | Legal/PCLA/copyright text | **No runtime requirement.** No legal/license/qualification compliance determination is made by host protocol tests. |
| 7 | Contents: introduction, features, treadmill, cross trainer | **No runtime requirement.** Navigation only; referenced body pages have their own rows. |
| 8 | Contents: cross trainer, step/stair climber | **No runtime requirement.** Navigation only. |
| 9 | Contents: rower, bike, training status, ranges | **No runtime requirement.** Navigation only. |
| 10 | Contents: controls, status, transport, appendices | **No runtime requirement.** Navigation only. |
| 11 | Contents: remaining spin-down examples | **No runtime requirement.** Navigation only. |
| 12 | Shall/should/may/can terminology | **No runtime requirement.** Used to classify mandatory, conditional and informative statements; recommendations are not reclassified as codec errors. |
| 13 | Introduction, six families, conformance, independence from other services, minimum Core 4.2, start of GATT requirements | **Partial.** Families evidence checks implemented message families. Neither port implements or verifies a Bluetooth Core stack or a complete conforming server; EC23224 is not a codec wire change. |
| 14 | Write/notify/conditional indicate/read-long; transport neutrality; no ATT application error codes; little-endian transmission | **Partial.** Endian evidence is checked. Local codec errors are not ATT application errors. GATT procedures and transport/security operation are **outside**, not passed by byte tests. |
| 15 | Primary-service recommendation and Fitness Machine Service UUID | **Partial.** TS `src/constants.ts:FTMS_SERVICE_UUIDS.FITNESS_MACHINE` equals `00001826-0000-1000-8000-00805f9b34fb`; C capability scope is caller-supplied. Neither port hosts/registers a primary GATT service; no host test proves correct BLE service registration. |
| 16 | Advertising Service Data fields: AD type, service UUID, available flag, machine-type bits | **Partial — coverage gap.** Neither public TS nor C API encodes/decodes this Service Data structure. Characteristic capability discovery is not an advertisement decoder. Advertising transmission is outside; the missing pure byte codec is separately recorded, not claimed implemented. |
| 17 | Six machine-type advertisement bits, RFU bits 6–15; §3.2 LSO/MSO convention | **Partial.** Advertisement bit codec absent as on p16. Endian evidence checks implemented characteristic codecs; correct characteristic dispatch does not substitute for parsing advertisement flags. |
| 18 | Characteristic inventory, instances, properties, CCCDs | **Partial.** TS `src/features.ts:capabilityKind` and property checks; C `src/capabilities.c` kind/property tables; `capabilities.test.ts` and C `test_capabilities.c`. The original Read-only C.7 finding has an implemented follow-up; no GATT service/CCCD creation. |
| 19 | C.1–C.7 conditions, encrypted Control Point, record definition and splitting | **Partial.** Same capability evidence; C `src/measurement.c` planner/record APIs tested in `tests/test_measurement.c:206–374`. C.7 caller evidence is implemented; caller still supplies security and connection state, and there is no MTU negotiation. TS production has fragment codecs, not a record assembler. |
| 20 | Training Session; two 32-bit Feature words; static values and RFU | **Partial.** TS `src/features.ts:59–77,226–280`, C `src/ftms.c:ftms_decode_features/ftms_encode_features`, capability unknown-bit reporting; `features.test.ts`, shared `values/v1` feature literals. No session clock or lifetime mutability enforcement; raw encoding deliberately preserves RFU. |
| 21 | Bonded reconnection indications; machine feature bits 0–7 | **Partial.** TS `src/features.ts:241–249`, C raw feature words/capability masks; TS feature matrix and C `test_capabilities.c:116–126`. Bits checked; bonding/reconnection/indication policy absent. |
| 22 | Machine feature bits 8–16 and RFU | **Checked: bit representation.** TS `src/features.ts:249–257`, C `src/capabilities.c:84–97`; feature matrix and unknown-bit literals. User-data retention and RFU-zero server policy are not implemented by raw feature encoding. |
| 23 | Target feature bits 0–8 | **Checked: bit representation.** TS `src/features.ts:258–266`, C `src/capabilities.c` target mapping; TS feature matrix and C `tests/test_capabilities.c:test_target_mapping`. Feature support is not execution authority. |
| 24 | Target bits 9–16, RFU; Treadmill notification behavior | **Partial.** TS `src/features.ts:266–273`, C target mapping and same bit tests. Neither port schedules notifications or gates on CCCD/data availability. |
| 25 | Treadmill transport and flags 0–9 | **Partial.** TS `src/parsers.ts:324–398`, C `src/measurement.c:treadmill field definition`, generic flags/planner; TS `measurements.test.ts:79–159,622–641`, C planner literals. Layout/diagnostics checked; transport excluded. Feature-to-payload consistency is not validated by the payload codec. |
| 26 | Flags 10–12; final-only speed; distance; inclination/ramp | **Checked: layout and sentinel.** TS `src/parsers.ts:335–351,384–393`, C treadmill definition/planner; TS More Data, full-layout and unavailable-value tests; C `test_measurement.c:77–107,206–273`. Inclination/ramp `0x7fff` handling is family-specific. |
| 27 | Elevation pair, pace, total energy | **Checked: selected wire layout.** TS `src/parsers.ts:209–223,353–373`, C treadmill definition/sentinel logic; complete treadmill and unavailable-energy literals. Current UINT16 pace and explicit legacy UINT8 selection remain distinct; no automatic inference. Session accumulation is caller-owned. |
| 28 | Energy/hour/minute, HR, MET, times, belt force | **Checked: layout/scaling/sentinels.** TS `src/parsers.ts:209–223,375–392`, C treadmill definition; TS all-family energy matrix and C `sentinels_and_overlap`. Energy/minute uses UINT8/255; source prose contains contradictory UINT16/decimal wording. No live time updates are proved. |
| 29 | Belt force/power sentinel; Cross Trainer behavior/flags | **Partial.** TS `src/parsers.ts:390–480`, C treadmill/cross definitions; force/power sentinel and cross full-layout tests. Notification timing/CCCD/MTU are outside. |
| 30 | Cross Trainer flags and movement direction | **Checked: flags/layout.** TS `src/parsers.ts:400–480`, C cross definition and planner direction metadata; TS cross full layout/RFU tests, C cross planner/direction cases. Three-byte flags and paired groups checked; support-bit consistency remains caller policy. |
| 31 | Cross speed, distance, step-rate pair, stride and elevation | **Checked: layout/sentinels.** TS `src/parsers.ts:411–441`, C cross definition; TS cross full layout/unavailable step rates, C full-layout literals. Stride uses 0.1; Cross Trainer step-rate sentinel is not applied to Step Climber. |
| 32 | Cross inclination/ramp, resistance, signed powers | **Checked under selected format.** TS `src/parsers.ts:442–460`, C cross definition/format selection; paired-sentinel and no-power-sentinel tests, C signed-resistance literals. Power `0x7fff` is valid, not unavailable. Resistance scaling conflict remains open below. |
| 33 | Cross energy, HR, MET, elapsed time | **Checked: byte/value behavior.** TS `src/parsers.ts:461–474`, C cross definition; cross full layout and all-family energy matrix. Session accumulation/time origin are outside. |
| 34 | Cross remaining time; Step Climber behavior and flags | **Partial.** TS `src/parsers.ts:471–527`, C step definition/planner; Step Climber full-layout and More Data cases. Both Floors and Step Count belong in final fragment; notifications remain outside. |
| 35 | Step flags and Floors/Step Count/rate/elevation fields | **Checked: layout.** TS `src/parsers.ts:494–523`, C step definition; TS complete step layout, C full payload/prefix cases. Positive elevation only; no invented negative field or cross-family sentinel. Generic RFU mask is tested, not an exhaustive per-bit matrix for this family. |
| 36 | Step rates, elevation, energy, HR | **Checked: layout/sentinels.** TS `src/parsers.ts:503–515`, C step definition/sentinel logic; TS step full layout and energy matrix, C full-layout cases. C retains raw units; no session accumulator. |
| 37 | Step MET/times; Stair Climber behavior/flags | **Partial.** TS `src/parsers.ts:511–575`, C step/stair definitions; both family full-layout/More Data tests. No notification scheduler or Training Session state machine. |
| 38 | Stair flags; final-only Floors and field semantics | **Checked: layout.** TS `src/parsers.ts:529–575`, C stair definition/planner; stair full-layout, More Data and truncation tests. Floors is the sole mandatory group, unlike Step Climber. |
| 39 | Stair rates, elevation, stride, energy group | **Checked: layout/sentinels.** TS `src/parsers.ts:529–571`, C stair definition; `equipment-stair-climber-all-fields`, `minimal-stair` and energy matrix. Energy/minute prose inconsistency does not change the one-byte field. |
| 40 | Stair HR/MET/times; Rower notification behavior | **Partial.** TS `src/parsers.ts:559–570`, C stair definition/record APIs; stair full-layout/truncation and C assembly tests. No notification interval/transport validation. |
| 41 | Rower flags, RFU, feature relationships | **Checked: flag layout.** TS `src/parsers.ts:577–637`, C rower definition/mask `0x1fff`; `minimal-rower`, `equipment-rower-all-fields`, `more-data-rower`. Diagnostics are not strict RFU rejection in every API; payload codecs do not cross-validate Feature values. |
| 42 | Rower stroke rate/count, pace, distance, power | **Checked: layout/scaling.** TS `src/parsers.ts:589–612`, C rower definition; rower full-layout and split literals. Half-rpm stroke rate, UINT24 distance, signed power and mandatory group checked. |
| 43 | Rower power/resistance, energy, HR | **Checked under selected format.** TS `src/parsers.ts:607–627`, C rower/format definitions; rower full-layout, unavailable-energy and signed-resistance cases. Universal resistance scaling remains unresolved; energy/minute remains one byte. |
| 44 | Rower MET/times; Indoor Bike behavior/flags | **Partial.** TS `src/parsers.ts:625–650`, C rower/bike definitions; full-layout and record tests. Notification timing and MTU negotiation are outside. |
| 45 | Indoor Bike flag table; E9555 cadence presence | **Checked.** TS `src/parsers.ts:640–694`, C `src/measurement.c` bike definition: bit 2 set means cadence present. Bike full-layout/registry cadence and raw corpus literals exercise it. No runtime fix needed for E9555. |
| 46 | Bike speeds/cadences, distance, resistance, powers, energy | **Checked under selected format.** TS `src/parsers.ts:651–681`, C bike definition; complete bike and C formatted-record literals. Speed and half-rpm cadence normalization checked; resistance ambiguity remains documented. |
| 47 | Bike energy, HR/MET/time; split elapsed-time rule | **Partial.** TS `src/parsers.ts:679–693`, C bike definition/record APIs; unavailable-energy matrix and split cases. Byte layout checked; update timing/session origin are outside. |
| 48 | Bike remaining time; Training Status structure/behavior | **Partial.** TS `src/parsers.ts:746–828,1690–1751`, C `src/status.c:126–158`; shared `statuses/v1`, TS `status.test.ts`, C `test_status.c`. String/flags/status bytes checked; read/notification transport absent. |
| 49 | Training flags, status 0–15, UTF-8, extended string | **Partial.** Same status codecs/tests, including invalid UTF-8 evidence and encode rejection. No MTU notification-prefix planner, Read Long retrieval or ten-second update policy. Full-value UTF-8 validation is not evidence of extended notification-fragment handling. |
| 50 | Status string; speed/inclination ranges and conditional presence | **Partial.** TS `src/features.ts` range codecs/capabilities, C `src/ftms.c:47–120` and `src/capabilities.c`; `features.test.ts`, shared range literals, C codec/capability tests. Layout/order/scales checked against selected definitions; service exposure and actual supported extremes are caller assertions. No separate speed/inclination scale defect established. |
| 51 | Resistance/power/heart-rate ranges | **Partial.** Same range sources/tests plus explicit resistance format cases. Resistance unit/exponent conflict remains unresolved; do not generalize it to all ranges merely because codecs have no exponent field. No live read/exposure proof. |
| 52 | Control envelope; request/reset/response opcodes | **Checked: wire structure.** TS `src/control.ts` raw request/response codecs; C `src/control.c:request_length` and encode/decode functions; TS control literal vectors and C `test_control.c`. Hosting/indications outside. |
| 53 | Target speed/inclination/resistance/power/HR parameters | **Partial — source conflict.** TS/C control codecs and shared `controls/v1` literals verify widths/scales. Resistance default SINT16 tenths follows ESR11 E8991; explicit `uint8Tenths` follows literal adopted table. No basis to silently revoke either interpretation. |
| 54 | Start/stop; targeted energy/steps/strides/distance | **Partial.** Same control sources/literal vectors and action/bounds tests check UINT24 distance and actions 1/2. Conditional support and actual machine transitions are not codec behavior. |
| 55 | Time/zone arrays, simulation, wheel circumference | **Partial.** TS `src/control.ts` zone/simulation encoding, C `src/control.c:99–111`; literal vectors for 2/3/5 zones, simulation and circumference. Layout checked; conditional server support/execution outside. |
| 56 | Spin Down, cadence, reserved opcodes and C.1–C.15 | **Partial.** TS/C request codecs; spin action, half-rpm cadence, reserved-opcode and target mapping tests. Capability evidence does not prove a server implements every conditionally mandatory procedure. |
| 57 | Permission, Request Control, Reset semantics | **Partial.** Request/reset/status literals in TS/C control/status tests check bytes. No control owner, reset defaults, Training Status transition or indication executor. |
| 58 | Apply speed/inclination/resistance/power procedures | **Partial.** TS/C control and corresponding status codecs, control/status literals. No equipment application or permission state; p53 source conflict applies. |
| 59 | HR, start/resume, stop/pause and time updates | **Partial.** TS/C control/status literals check `[07]`, `[08,01]`, `[08,02]` and HR byte. No periodic clock or actuator state transition. |
| 60 | Stop/pause actions and response; energy/steps targets | **Partial.** TS `src/control.ts` action/UINT16 codecs, C `src/control.c:72–99,146–152`; all-opcode literals and action bounds. Time-field stop semantics and permission remain outside. |
| 61 | Strides, UINT24 distance, UINT16 training time | **Checked: wire structure.** TS raw/high-level controls, C request length/operand code; control corpus and C all-opcode literals check widths/order/bounds. Procedure completion not proved. |
| 62 | Two-zone times; three-zone procedure | **Checked: cardinality/order.** TS ordered tuples and zone encoder, C `control.h` zone array and request codec; two/three-zone literal vectors. |
| 63 | Three/five-zone times | **Checked: cardinality/order.** Same codecs and three/five-zone independent literals; UINT16 seconds in specified order. No heart-rate-zone runtime controller. |
| 64 | Simulation signed wind/grade, Crr/Cw; circumference | **Checked: selected encoding.** TS/C control/status simulation codecs and literals. Cw UINT8/0.01 is unitless per E10187; retained legacy kg/m field names documented, not reinterpreted. Wheel circumference UINT16/0.1 mm. |
| 65 | Spin Down Start/Ignore and speed response; cadence | **Partial: contextual validation.** TS `src/control.ts:168–254`, C `src/control.c:168–205`, response literals accept 3/7-byte success. Start requires speeds; Appendix A.3.3 shows Ignore success without speeds. These response-only APIs lack the initiating action and cannot distinguish them. Accepting the three-byte form is not by itself a defect. |
| 66 | Cadence and Procedure Complete envelope | **Checked: implemented wire forms.** TS/C cadence and response codecs/literals verify half-rpm UINT16 cadence and `80/request/result` framing. Generic unknown parameters are diagnostic evidence, not arbitrary canonical encodable responses. |
| 67 | Result values, Spin Down speeds, operation arbitration | **Partial.** TS/C result mappings and response tests check success/unsupported/invalid/failed/not-permitted. Request-context limitation from p65 applies; abort/arbitration/Start error policy is outside. |
| 68 | Unsupported/invalid requests; ATT busy/CCCD errors; status exposure | **Outside for server behavior.** Codec tests cover byte structures/local errors, not ATT errors, busy-state sequencing or characteristic instantiation. |
| 69 | Status structure and opcodes 01–0A | **Checked.** TS `src/parsers.ts:831–953,1529–1612`, C `src/status.c:33–76`, shared status literals and port tests. Resistance status `07` remains SINT16 tenths independently of command profile. |
| 70 | Status 0B–15, simulation, circumference, Spin Down and cadence | **Checked.** TS `src/parsers.ts:954–1024`, C `src/status.c:64–118`; status corpus, reserved-spin diagnostics, all-opcode C tests. Widths/order/selected units checked. |
| 71 | Status notification/control permission lost; stale data | **Partial.** Status codecs and C generation/reset/expiry APIs checked by status/record/simulation tests. Caller owns disconnect detection, notification loss/storage and freshness policy. TS lifecycle reducer is test-only. |
| 72 | More Data ordering and transport distinctions | **Partial.** Both codecs honor bit 0; C production planner/assembler in `src/measurement.c:135–300` and literal planner/record tests. TS has no equivalent production snapshot planner/assembler. No universal loss/reordering detection is possible without a sequence identifier. |
| 73 | BR/EDR SDP record/descriptors/handles | **Outside.** Neither package hosts SDP, L2CAP, ATT or a service database. |
| 74 | Acronyms | **No runtime requirement.** Terminology only. |
| 75 | References | **No runtime requirement.** Sources, not executable assertions; identities recorded in the specification audit. |
| 76 | Informative single/split record examples | **Partial.** TS fragment parsing/raw encoding and C production planner checked against literals. TS lacks production planning/assembly; informative diagram is not transport execution evidence. |
| 77 | Informative normal control transaction | **Partial.** Both ports encode/decode request/response bytes, tested by controls corpus. Write response, indication and confirmation are outside. |
| 78 | Informative busy-procedure transaction | **Outside.** No busy queue, ATT error dispatcher or procedure executor in either pure codec. |
| 79 | Informative requested Spin Down success | **Partial.** Control response speed and individual status literals checked in both ports. No physical spin-down timing, actuator sequence or contextual lifecycle is implemented. |
| 80 | Informative client Spin Down error | **Partial.** Individual response/error-status bytes checked; event-order state machine and machine behavior outside. |
| 81 | Informative Spin Down Ignore | **Partial.** Ignore request and no-parameter success are represented/tested by both control codecs. This is evidence against globally requiring speeds for every successful opcode 13 response. Sequence termination is caller-owned. |

## Findings and follow-up priorities

1. **C.7 follow-up implemented; transport gap remains (pp18–21).** The original
   pinned-audit finding is historical: current capability snapshots accept
   caller-owned bonding/lifetime-mutability evidence and distinguish unknown from
   false. Remaining work is transport-owned bonding, reconnection indication and
   CCCD behavior, not static C.7 property interpretation.
2. **Missing advertising byte API (pp16–17).** Service Data available/type fields
   are not covered by either public codec. Adding a pure advertising codec is
   separable from adding Bluetooth transport; it is not implemented by this audit.
3. **Production record API parity (pp19,72,76).** C has snapshot planning and
   caller-driven record assembly. TS has fragment encode/decode and test-only
   lifecycle simulation, not equivalent production planning/assembly.
4. **Training Status extended delivery (pp48–49).** Complete-value decoding and
   UTF-8 tests do not establish correct MTU-prefix delivery or Read Long recovery.
   This needs a transport integration contract before claiming coverage.
5. **Spin Down contextual validation (pp65,67,81).** Do not remove three-byte
   success support: Ignore explicitly uses it. Checking that Start success has
   both speeds requires the request action, which the response-only APIs do not
   receive. A future transaction validator could provide that check without
   changing raw evidence decoding.
6. **Unresolved sources.** E8991 versus the adopted UINT8 resistance-command row
   and resistance GSS unit/exponent annotations remain unresolved. Explicit
   independent format choices preserve evidence; they are not a claim that every
   choice conforms to every source. Energy/minute prose contradictions do not
   justify changing existing UINT8 wire encoding. No separate general range
   exponent defect was established.
7. **Not implemented here:** BLE service hosting, encryption/bonding, CCCDs,
   notifications/indications, SDP, Training Session clocks, control ownership,
   procedure scheduling, physical execution and actuator safety. These are
   integration obligations, not functionality proved by matching port traces.

The ledger accounts for every physical page, but it is a source-and-test review,
not an exhaustive generated assertion for each normative sentence. In particular,
RFU matrices and cross-characteristic consistency are not universally exhaustively
tested. A “Checked” field-layout result does not upgrade these limitations to
complete service conformance.

## Verification performed for this audit

- `env -u TMPDIR pnpm verify`: passed; lint, types, 551 tests in 13 files,
  build and packed-package checks. Local log:
  `packages/c/build/page-audit-ts.log`.
- `make BUILD=build/page-audit test` from `packages/c`: passed native strict
  and sanitizer tests, canonical corpus adapters, simulation/failure-injection
  checks, fuzz tests and installed/source-artifact consumers. Local log:
  `packages/c/build/page-audit-native.log`.
- Tests verify the implemented contracts and literals, not the absent server
  behavior or unresolved source interpretations above. No physical equipment,
  embedded target execution or Bluetooth qualification was performed.
- Only this audit report was added by the page-review task; existing API/corpus
  and earlier audit edits were preserved. No commit, push, merge or remote CI run
  was performed for this task.
