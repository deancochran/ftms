# FTMS 1.0.1 and units audit

## Scope and source identity

This audit compares all service sections in the adopted 1.0 and 1.0.1 texts
against product base `2b5ff79`, with follow-up on 2026-09-29. It is not a Bluetooth
qualification assessment. The recovered official annotated comparison now gives
direct attribution for all nine errata listed in 1.0.1. Standalone erratum issue
documents were not recovered; the comparison is the redline evidence used below.
The complete source documents stay in machine-local context, not package assets.

Primary sources consulted:

- **Recovered official annotated comparison**, titled
  `FTMS_v1.0.1_showing_changes_since_FTMS_v1.0`, Bluetooth SIG, Inc., 81 pages.
  [Archived original download](https://web.archive.org/web/20260117142059id_/https://docman.bluetooth.com/download/ftms_v1-0-1_showing_changes_since_ftms_v1-0/?tmstv=1729629827),
  captured 2026-01-17 14:20:59 UTC; retrieved 2026-09-29, 843,732 bytes.
  PDF SHA-256:
  `0b2c150a6c3fb50520d04bb00e3632ff8d9d880d1578c9c6b51b75db455ce21a`.
  Its cover identifies it as a courtesy comparison, not the governing adopted
  specification. Tracked deletions/insertions can interleave in extracted text;
  final types and values are checked against the adopted PDF, not read literally
  from strings such as `USINT816` in redline extraction.

- [FTMS 1.0.1 adopted page](https://www.bluetooth.com/specifications/specs/fitness-machine-service-1-0-1/),
  adopted 2024-10-01, and its
  [official HTML](https://www.bluetooth.com/specifications/specs/html/?src=ftms-v1-0-1_1756429637/FTMS_v1.0.1/out/en/index-en.html).
  SHA-256 of locally extracted specification text:
  `6f1812d3346d52ba370890b4da659e24eae611233121a46f0b209bea68346a26`.
  This identifies an extraction, not a publisher-issued PDF checksum.
- The [official 1.0.1 PDF](https://files.bluetooth.com/download/ftms_v1-0-1/),
  recovered through the public download page's manual-download link. PDF SHA-256:
  `0d28454790276aab48350ae991ff6df83aaaa9bb9c52b65b89f26d261ce8f89e`.
  Its Control Point row agrees with the HTML's literal UINT8 text.
- The project's pinned adopted FTMS 1.0 PDF, SHA-256:
  `a958d9f133b3d38e7ba9b675fcc1c53897f39371e092a8892d768e094184391e`.
- [ESR11](https://www.bluetooth.org/DocMan/handlers/DownloadDoc.ashx?doc_id=436247),
  19 December 2017. The download is a ZIP, not a PDF. ZIP SHA-256:
  `5122284ffcff2e60ef14b327f2d60d6ea1a8f6a06aa4ad8a468ffb6ed7c322a8`.
  Contained `ESR11_v1.0_ext.pdf` SHA-256:
  `811ab3868a4aeae74ec3f2f551d3b2c67e66c3b0fb608b7de95f34d87a58c3a9`.
- [Mandatory Errata Correction 23224](https://www.bluetooth.org/DocMan/handlers/DownloadDoc.ashx?doc_id=572314),
  dated 2023-08-01. PDF SHA-256:
  `e6486d78e0acc07c41037d2927bf2f50bb00ca5af15910bdeab78426e7f42ac0`.
- [GATT Specification Supplement](https://www.bluetooth.com/specifications/gss/),
  [PDF](https://btprodspecificationrefs.blob.core.windows.net/gatt-specification-supplement/GATT_Specification_Supplement.pdf),
  version date **2026-09-09**. PDF SHA-256:
  `34ad6b5f2e48c29759c2ef17f01502cb60080aff5d213712a6f581c56c9150b8`.
  This is a current characteristic definition source, **not** proof of what an
  archived Assigned Numbers revision said at adoption in 2024.

## Erratum reconciliation and evidence limits

| Erratum | Direct evidence | Disposition |
| --- | --- | --- |
| E8991 | ESR11 Part II §4.1, printed p.184 | Changes FTMS 1.0 §4.16.1 request `0x04` from UINT8 to SINT16; resolution remains 0.1. Existing signed command default is erratum-backed. |
| E9135 | ESR11 Part II §3.1, printed p.183 | Changes **Fitness Machine Profile** 1.0 §4.4.14.2.5 command operand to SINT16. It does not define Cross Trainer stride resolution. Corrected only the erroneous provenance description in codec-v1 vectors; byte/value expectations are untouched. |
| EC23224 | §2 and Table 2.1, FTMS 1.0 §1.1 entry | Replaces conformance wording, matching 1.0.1 §1.1. No wire-format change. |
| 9555 | Comparison p.45, annotation BSIG8 | Table 4.10 cadence bit 2 corrected: 0 means absent, 1 means present. Existing TS/C decoders and cadence fixtures already follow the corrected rule. |
| 10187 | Comparison p.64, BSIG9 | Table 4.20 Cw unit changes kg/m to **unitless**, retaining UINT8 / 0.01 resolution. Existing bytes/scaling agree, but public `cwKgPerM` / `cw_hundredth_kg_per_m` names are historical and must not be treated as the 1.0.1 unit definition. |
| 10194 | Comparison p.69, BSIG10 | Status 0x07 parameter changes UINT8 to SINT16, resolution 0.1 unchanged; existing status codecs agree. The annotated change does not change the Control Point request row or resolve its E8991 conflict. |
| 16264 | Comparison pp.18–20, BSIG5–7 | Conditional Feature Indicate property/C.7 and changed-feature indication to subscribed bonded collectors after reconnection; capability/transport limitation recorded below. |
| 16265 | Comparison p.73, BSIG11 | Removes GATT Start/End Handle parameters from SDP Protocol #1; adopted §5 confirms resulting table. Outside pure codecs. |
| 18751 | Comparison pp.6, 76, 77, 79, BSIG2/13–15 | Legal text and explicit INFORMATIVE labeling of appendices. No new codec behavior inferred. |
| 18972 | Comparison p.4, BSIG1 | Contributors renamed Acknowledgments; editorial. |
| 22596 | Comparison pp.13, 75, BSIG4/12 | Minimum Core compatibility and reference move from 4.0 to 4.2; platform/integration requirement. |
| 23316 | Comparison p.13, BSIG3 | Conformance replacement consistent with mandatory EC23224; no wire change. |

The live `docman.bluetooth.com` download still returned HTTP 400/403, and the
public-files counterpart returned 404. An Internet Archive availability lookup
of the **complete original URL including `?tmstv=1729629827`** found the archived
PDF; omitting that query had missed it. The archive copy retains the official
title/author, all nine revision-history IDs and the explicit BSIG annotations
above. The redline-attribution gate is closed by that evidence, not by guessing
from the erratum numbers. An additional official TCRL download, currently
`TCRLpkg104/Integrated Errata - GATTBased TCRL_p9.xlsx`, independently lists all
nine IDs and matching issue titles on its FTMS sheet. Its mutable download URL
contains `2024` but serves package 104, so it is not treated as a pinned 2024
artifact or as a substitute for the annotated redline.

**Correction after recovery:** the earlier text-only comparison missed E9555's
cadence flag inversion and E10187's Cw unit correction. The accounting below now
includes both. The runtime bit handling and wire scaling already agree; the Cw
public field names remain a compatibility/documentation limitation.

**Correction to the first audit pass:** signed16 was incorrectly described as
merely a compatibility default. E8991 explicitly supports it. The retrieved
1.0.1 PDF/HTML still print UINT8 in Table 4.15, unlike the ESR11 correction.
That is a source conflict, not evidence that E8991 was revoked or that UINT8 is
a universal new requirement. Keep the signed default; callers may explicitly
select the literal-table UINT8 alternative. Do not infer either from status.

## Complete service-section accounting

The comparison covers numbered sections 1–7, all 4.1–4.19 subsections and the
three appendices. Neither document has section 8. “Unchanged” below means no
substantive rule delta identified in these service texts; it does not audit
every historical revision of their external characteristic definitions.

| Sections | Net adopted-text result | Product mapping / evidence boundary |
| --- | --- | --- |
| 1.1 | Conformance text replaced | EC23224 directly reconciled above; no codec change. |
| 1.2 | Service dependencies unchanged | Service composition belongs to the caller. |
| 1.3 | Minimum Core 4.0 becomes 4.2 | BLE/firmware integration requirement, not a byte-codec version. |
| 1.4–1.7 | GATT sub-procedures, transports, error codes and little-endian order unchanged | Existing little-endian codecs; no transport qualification claimed. |
| 2 | Service declaration unchanged | GATT service instantiation is outside these packages. |
| 3, 3.1–3.1.2 | Service-data advertisement flags/type unchanged | Capability inference continues to use supplied evidence, not mandatory advertisement or device-name assumptions. |
| 3.2 | Byte Ordering text unchanged: LSO is the low-numbered octet of the topmost field; MSO is the high-numbered octet of the bottommost field | Reviewed in both adopted PDFs; complements §1.7's little-endian transmission rule. No codec change. |
| 4, Table 4.1 | Adds Feature Indicate condition C.7 | Required when bonding is supported and Feature can change over device lifetime; otherwise excluded. See capability caveat below. |
| 4.1–4.2 | Data Records and Training Sessions unchanged | Production C planner/assembler and explicit TS test-session model; application lifecycle stays outside codecs. |
| 4.3–4.3.1.2 | Adds Feature indication after reconnect to bonded collectors when subscribed and features changed | Feature bit definitions unchanged. No bonding, CCCD or indication engine implemented here. |
| 4.4–4.9, all field subsections | E9555 corrects Indoor Bike cadence flag bit 2 polarity in Table 4.10; More Data and unavailable-value rules unchanged | Existing codecs already consume cadence when bit 2 is set. Existing measurement corpora and cadence tests retain that behavior. No new cross-family sentinel inferred. |
| 4.10, all field subsections | Training Status flags/values/string behavior unchanged | Existing status corpus; UTF-8/raw evidence remains distinct. |
| 4.11–4.15 | Range-presence conditions and purpose unchanged | Existing range/capability codecs; external GSS scale ambiguity remains below. |
| 4.16–4.16.1 | Opcode/operand table materially unchanged between adopted editions | UINT8 command row conflicts with intervening E8991; explicit profiles preserve both interpretations without changing default. |
| 4.16.2.1–4.16.2.22 | All 22 procedures inspected; E10187 changes Cw units in §4.16.2.18 Table 4.20 to unitless, not bytes or resolution | Request Control, Reset, five target controls, Start/Resume, Stop/Pause, energy/steps/strides/distance/time, two/three/five HR zones, simulation, circumference, spin down, cadence, completion. Legacy Cw API names retain kg/m wording; no physical-unit conversion is justified by this naming. Codec tests cover messages, not procedure ownership or actuator execution. |
| 4.16.3–4.16.4 | Error handling and procedure timing unchanged | ATT errors, CCCD configuration, command queuing and completion timing belong to transport/session code. |
| 4.17 | Status `0x07` operand changes UINT8 to SINT16, still 0.1 | Both implemented status codecs already use SINT16; existing status regression fixtures agree. Do not derive request width from it. |
| 4.18–4.19 | Time-sensitive discard and More Data transmission rules unchanged | Lifecycle simulations test supplied resets/generations, not actual BLE loss detection; no universal record sequence ID. |
| 5 | SDP table removes GATT Start/End Handle parameters | BR/EDR SDP integration change outside packages. |
| 6–7 | Acronyms/reference presentation updated, including Core 4.2 and Supplement v11-or-later references | No extra wire-layout change inferred from reference updates alone. |
| Appendices 1–3 | Substantively unchanged examples/guidance, reorganized numbering | Informative examples do not substitute for canonical literal fixtures. |

### Historical C.7 audit finding and implemented follow-up

The following was the finding against the original pinned audit manifest, not a
claim about the current capability corpus: Feature indication was **not fully
covered by the then-existing capability contract**:
the snapshot has no bonding/lifetime-mutability evidence and currently compares
Feature properties against Read only. Both evaluators can flag Read|Indicate as
unexpected and invalidate dependent prerequisites. Do not present that result as
a complete 1.0.1 server-conformance verdict. Supporting C.7 correctly needs a
separate explicit capability-contract change and regression cases; this audit
does not silently loosen that versioned contract or fabricate bonding evidence.

The C.7 follow-up is now implemented separately: caller-owned bonding and
lifetime-mutability evidence distinguishes true, false and unknown; only
Indicate is conditional, and unknown evidence remains incomplete rather than
fabricated. The current 63-case capability corpus pins that behavior. This does
not change this audit's original source identity or turn static evidence into
bonding, CCCD, reconnection, encryption, or transport proof.

Observed source defects are retained as audit findings, not patched protocol:
the 1.0.1 §4.16.2 overview links Request Control to §4.16.2.21 (cadence), while
the actual Request Control heading is §4.16.2.1. The Request Control paragraph
also retains the older Reset-completion wording. Treadmill energy-per-minute
still pairs `0xFF` with incorrect explanatory decimal/type text; the byte sentinel
and GSS UINT8 definition support existing `0xFF` handling, not a new value 257.

## Confirmed direction-specific rules

| Surface | Primary location | Finding and implementation disposition |
| --- | --- | --- |
| Control Point resistance request `0x04` | ESR11 E8991; conflicting FTMS 1.0.1 §4.16.1, Table 4.15 | E8991 specifies SINT16 tenths, retained as default. Explicit `uint8Tenths` represents the literal uncorrected table only; no claim that it supersedes the erratum. |
| Resistance status `0x07` | FTMS 1.0.1 §4.17, Table 4.26 | SINT16, resolution 0.1. Existing codecs agree; command selection must not change status decoding. |
| Resistance telemetry | FTMS §§4.5.1.11, 4.8.1.10, 4.9.1.7; GSS §§3.69, 3.213, 3.139 | Current GSS says UINT8 and explicitly labels the unit as 1. Existing byte width agrees. GSS also prints exponent `d = 1` alongside that unit description: the scale annotations are inconsistent, so this audit does not claim to resolve them. Whole-unit defaults remain unchanged, signed16-tenths remains explicit compatibility policy. |
| Supported Resistance Level Range | FTMS §4.13; GSS §3.231, Table 3.357 | Current GSS defines three UINT8 fields. The same exponent/unit inconsistency occurs here. Preserve the three-byte default and independent six-byte compatibility option; a six-byte capture proves width, not scale. |
| Treadmill pace | FTMS §§4.4.1.8–9; GSS §3.258 | UINT16 seconds per 500 metres in current GSS. Existing default agrees. One-byte compatibility input retains raw values without inventing normalized units. |
| Rower pace | FTMS §§4.8.1.6–7; GSS §3.213 | UINT16 seconds per 500 metres. No general `0xFFFF` unavailable rule is supplied in these pace sections; retain raw 65535 rather than invent a rest sentinel. |

The service text delegates many characteristic field definitions to the SIG's
characteristic definitions. Reading only the service prose is insufficient to
settle widths and units. Conversely, measurements and range tables do not
override the Control Point and status parameter tables.

## Unavailable and reserved evidence

- Treadmill §4.4.1: inclination/ramp and force/power pairs use `0x7FFF` when
  the grouped field must be present but its value cannot be supplied; energy
  uses `0xFFFF`, `0xFFFF`, `0xFF`. Existing TS/C behavior agrees.
- Cross Trainer §4.5.1: paired step rates use `0xFFFF`; inclination/ramp uses
  `0x7FFF`; energy uses the same three sentinels. Existing behavior agrees.
- Step Climber §§4.6.1.4–5 and Stair Climber §§4.7.1.3–4 do **not** repeat the
  Cross Trainer step-rate sentinel rule. No new sentinel is inferred across
  families. Their energy rules, and Rower/Bike energy rules, remain supported.
- Reserved Training Status and Fitness Machine Status values are not promoted
  to meaningful states. Raw evidence/diagnostics and strict canonical encoding
  remain distinct. A diagnostic named `unknown_opcode` rather than `reserved`
  is library policy, not by itself a normative wire-format defect.
- RFU sender requirements do not imply that a permissive evidence decoder must
  discard the entire packet. Existing diagnostic decoding and strict encoding
  are not replaced with an unverified universal receive policy.

EC23224 replaces conformance language and applies to FTMS 1.0. It does not
change resistance or pace bytes, authorize controls, or establish that these
libraries alone constitute a qualified Bluetooth product.

## Explicit command selection

```ts
encodeFtmsControlRequest(
  { op: "setTargetResistance", resistanceLevel: 12.3 },
  { resistanceFormat: "uint8Tenths" },
); // 04 7b
encodeFtmsControlRequestRaw(
  { opcode: 4, operands: [123] },
  { resistanceFormat: "uint8Tenths" },
); // 04 7b; raw operands are integer tenths
```

C callers use `ftms_control_format_options` with
`FTMS_CONTROL_RESISTANCE_UINT8_TENTHS` and the request `_with_format` functions.
The existing `resistance_tenth_level` member carries the integer numerator.
Legacy functions and NULL C options retain signed16-tenths. TypeScript omitted
or empty options retain that default; invalid options, including null, fail.

For the selected UINT8 layout, raw values are 0–255 (normalized 0–25.5).
Normalized TS encoding retains its existing rounding policy; raw encoding does
not accept fractional numerators. No option is inferred from a device name,
capability bit, notification, supported range, or request length. Other request
opcodes are unaffected. This selection neither authorizes execution nor changes
reported capability evidence.

Regression tests in both ports use literal `04 00`, `04 7b`, `04 ff` requests,
not just encoder/decoder round trips, plus wrong lengths, bounds, invalid
selections and default preservation. Native tests check failure atomicity.
The shared controls corpus now carries an optional explicit request `format`;
omission preserves signed16-tenths and responses cannot carry a request format.
It has 41 fixtures / 72 directional assertions. Simulation directly references
the three authored UINT8 cases and a scripted response, with 38 scenarios / 79
steps overall. Both runners pass each fixture's format to encode and decode
independently. Existing case expectations are preserved. The original codec-v1
E9135 provenance description is corrected as described above, changing its
content identity but neither its comparison semantics nor any expected bytes.

## Remaining audit gates

1. Archive the characteristic-definition revision used at adoption if needed for
   historical GSS claims; the current GSS is independently dated. All nine listed
   errata now have direct attribution in the recovered comparison.
2. Resolve GSS resistance exponent versus explicit unit wording with authoritative
   clarification before changing normalization or claiming universal scale.
3. Reconcile the E8991 versus 1.0.1 request-table conflict with authoritative
   clarification before recommending the UINT8 alternative as a standard default.
4. The explicit C.7 evidence/policy gate is implemented in the static capability
   contract and corpus. Transport obligations (bonding, CCCD subscription,
   reconnection indication and authorization) remain unimplemented and unqualified
   by pure protocol tests.
5. Plan a compatibility-safe Cw API naming improvement: E10187 specifies a
   unitless coefficient, while the existing public names say kg/m. Preserve
   existing fields and wire values rather than silently introducing a conversion.

Hardware validation, Open Trainer integration, native mobile ports, publication
and Bluetooth qualification remain separate work.

## Historical verification before the final C.7 capacity follow-up

- `env -u TMPDIR pnpm verify`: historical pass: lint, types, **551 tests in 13 files**,
  build and packed-package checks. An initial formatting failure was corrected
  before this successful full run. Existing npm entry points and artifact layout
  are unchanged.
- `make BUILD=build/audit-reconcile test` from `packages/c`: passed the full native
  suite, normal and ASan/UBSan checks, existing shared corpora, fuzz tests and
  installed/source-artifact consumers. The C consumer calls both new format-aware
  request APIs and checks literal bytes.
- TypeScript and normal/sanitized native simulation each passed **38 scenarios /
   79 steps**. Their complete traces and per-file identities matched, including
  selected-command reference events.
- Both ports' simulation metatests deliberately ignore the selected format and
  corrupt encoded bytes; each fault fails all three selected request steps while
  retaining complete step accounting. Native malformed-command tests also check
  missing format-command operands return bridge errors rather than crashing.
- Structural comparisons against base confirm all historical codec, controls
  and simulation case expectations are unchanged; only the original corpus's
  E9135 provenance metadata changed, in addition to new control/simulation cases.
- Independent code review found no blocking defect; it explicitly identified the
  earlier shared selected-format corpus gap, now covered by canonical references.
  Follow-up review identified overly broad valid-fixture format placement and
  missing package-owned API documentation. Valid formatted fixtures are now
  restricted to opcode 04 with schema mutation tests, and both package READMEs
  document the options, bounds, defaults and non-inference rule.

Changes remain local and uncommitted on `audit/ftms-1-0-1`; no new remote CI,
package release or physical-device evidence is claimed.

After recovering the annotated comparison, the historical full TypeScript and
native commands above were rerun: 551 TypeScript tests and all native checks
passed; all three simulation traces/identities matched at 38 scenarios / 79
steps. The later C.7 capacity follow-up supersedes this as current verification;
see `docs/coverage.md`. This recovery changes audit/provenance and unit
documentation, not runtime code or existing fixture bytes. No archive document
is shipped in a package.
