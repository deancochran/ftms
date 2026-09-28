# Verification record

## Historical intermediate Control Point milestone (2026-09-28)

The following intermediate limitations were subsequently resolved; see the
[final bidirectional verification record](verification-bidirectional.md).
In particular, controls are now fuzzed, all 97
codec-v1 cases execute, and four bidirectional corpora exist.

`make -C packages/c test && make -C packages/c check-embedded` passed at
`41023a60cff6efdeef5e36730c3d7356a91d26b6` in a dirty checkout. The new strict
C99 control unit suite checks literal request bytes for all 21 opcodes (including
ESR11's signed, 0.1 resistance), request decode, response encode/decode, unknown
response diagnostics, malformed lengths, invalid action values, UINT24 overflow,
and encoder capacity/output atomicity. The sanitizer suite and 10,000 existing
bounded fuzz iterations passed; the fuzz harness is linked with `control.c` but
does not yet generate Control Point-specific input mutations. The isolated archive
matrix passed: GCC and Clang C consumers plus G++ and Clang++ C++11 consumers
against both archives. Cortex-M0 compile-only included `control.c` successfully.

The immutable codec-v1 runner remains deliberately incomplete: 42 passed and 55
unsupported (all 21 requests and all 12 responses remain reported unsupported by
its pre-existing adapter, plus measurements/statuses/diagnostics). This is an
adapter-accounting gap, not a claim that the new Control Point code conforms to
v1. No shared `controls/v1` fixture corpus was added in this bounded change; its
schema/vector identity and independent runner are outstanding review work.

This is local evidence for the unreleased first C slice, not device, PTS, BLE
qualification, full v1 conformance, or a release claim. Build output is ignored
under `packages/c/build/`; `/tmp/opencode` was root-owned in this environment and
could not be used.

## Chronological commands and results (2026-09-27)

1. `gcc ... -c src/ftms.c; ar ...; gcc smoke.c ...; g++ -std=c++11
   -fno-exceptions -fno-rtti smoke.cpp ...` initially attempted output under
   `/tmp/opencode/ftms-c-stage`; it **failed** before compilation: `mkdir:
   Permission denied`. Re-ran the same header/C-object/C++-link smoke sequence
   under ignored `packages/c/build/`: **passed**. This confirms a self-contained,
   double-includable header and actual C object linked by a C++ driver.
2. `gcc ... src/ftms.c tests/test_codec.c ... && test-codec`: first assertion
   **failed** because the test's purported unaligned byte pointer was incorrectly
   offset; corrected the test fixture (not codec), then re-ran: **passed**.
   The final rerun also covers zero/all-known feature words, each of 17 machine
   and target one-hot bits, reserved bit 31 preservation, unaligned payload, all
   five ranges, signed extrema, reversed bounds, zero increment, every short/long
   length including `SIZE_MAX`, nulls, invalid kind priority, and unchanged outputs
   on failures.
3. `clang ... -fsanitize=address,undefined ... fuzz.c && fuzz`: **passed**.
   The deterministic 10,000-input bounded fuzz loop checks failure output
   preservation and length invariants.
4. `gcc ... corpus_driver.c && python3 tests/corpus_adapter.py ...`: **passed**
   after correcting the adapter's corpus key from `controlRequests` to actual
   `controls`; `jsonschema 4.26.0` validated the canonical schema. Results:
   97 total, feature 35 + range 7 passed = 42, failed 0, unsupported 55,
   skipped 0, `complete=false`. The adapter prints each unsupported ID/reason.
   Identity: schema `e6d976172a32e3124602d17e46ed5fbab337f4f1d6535aec85a83069637268e0`,
   vectors `70125aa46a9272e3a0be7daf07fcf32161cab276f30d056ab64caca24b38fdc7`,
   contract `dbde466a8792c44083f164abd0ea97fda0ca2d69ddc98ec6e73252e8421885bd`;
   checkout `41023a60cff6efdeef5e36730c3d7356a91d26b6`, dirty true.
5. Isolated-prefix check: copied only header/archive into `build/prefix`, then
   compiled, linked, and ran `consumer.c` with GCC and Clang and `consumer.cpp`
   with both G++ and Clang++ against each separately GCC- and Clang-compiled C
   archive (`-std=c++11 -fno-exceptions -fno-rtti`), with source includes absent
   from the consumer include path: **all six combinations passed**. Compilers:
   GCC/G++ 16.2.1; Clang/Clang++ 22.1.8.
6. `clang --target=arm-none-eabi -mcpu=cortex-m0 -mthumb -std=c99
   -ffreestanding ... -c src/ftms.c`: **passed**. `nm -u` produced no undefined
   symbols; `size` reported text 600, data 0, bss 0 (object, not linked image).
   This is a compile-only Cortex-M0 indication; no link, board, runtime, or
   universal helper-runtime guarantee was tested.

7. An initial `make clean && make test` from repository root **failed** because
   the Makefile is intentionally port-local; it was rerun with `make -C packages/c`.
   A later final test run first **failed** on a stale test expectation after added
   zero/one-hot feature checks; the codec had not changed, the test correctly saved
   its pre-failure output instead, and the next run passed. Final native rerun:
   `make -C packages/c test`: **passed** (strict C99 unit, ASan+UBSan fuzz,
   schema-validated corpus adapter). The strict GCC/Clang C archive and C/C++
   isolated consumer matrix in step 5 was then rerun: **passed**.
8. `TMPDIR=/tmp/opencode pnpm verify`: **failed before TS tests ran** because the
   root-owned temporary directory rejected Vitest's mkdir (`EACCES .../ssr`).
   Lint and TypeScript typecheck passed before that environmental failure. This is
   TypeScript-only evidence and does not affect the native result.

## Review correction (2026-09-27)

A critical review found that the original adapter counted a Feature driver success
without comparing words to the vector expectation, ignored range kind/unit/divisor,
accepted either range error, and printed hard-coded category/pass counts. Therefore
the earlier `42 passed` report was a false-positive-prone result, not sufficient
comparison evidence. The corpus files were not changed.

The corrected adapter dynamically enumerates all categories and IDs, rejects
duplicate IDs, compares all 17 machine fields and all 17 target fields plus the
three v1 compatibility aliases, applies exact `expected` or exact true-field-set
comparison as required, and compares range kind, scaled normalized values, divisor,
unit, and the exact expected error. It now emits failure IDs/reasons and derives all
summary counts from the loaded corpus. `tests/test_corpus_adapter.py` has four
stdlib regression tests that deliberately reject zero/swapped feature output, wrong
range divisor/unit, and a wrong error.

Chronological correction commands/results:

1. `python3 -m unittest packages/c/tests/test_corpus_adapter.py` initially failed
   to import `corpus_adapter` when run from repository root. The test now inserts
   its own directory without changing the adapter's main guard; rerun: **4 tests
   passed**.
2. After the adapter/driver correction, `make -C packages/c test`: **passed**. The
   corrected direct-corpus summary is 97 total, 42 passed, 0 failed, 55 explicit
   unsupported, 0 skipped, `complete=false`; the same schema/vector/contract hashes
   above apply.
3. That target now runs `scripts/verify-consumers.py`, which compiles actual C99
   archives with GCC and Clang and from an isolated copied header/archive prefix
   runs two C consumers and four C++11 consumers (both G++ and Clang++ per C
   archive, with `-fno-exceptions -fno-rtti`): **all six passed**. `make all`
   remains C/archive-only and has no Python or C++ requirement.
4. `env -u TMPDIR pnpm verify`: **passed** with the default writable `/tmp`
   fallback. Root lint passed; TypeScript typecheck passed; Vitest ran 350 tests
   across 8 files with 350 passed; the TypeScript v1 runner reported 97/97;
   package verification, packed allowlist/export checks, and browser resolution
   passed. This supersedes the earlier `/tmp/opencode` permission failure only for
    the TypeScript verification environment; it is still not native/device evidence.

## Capability-evidence slice (2026-09-27)

1. `make build/test-codec` was attempted while adding the new C99 source and
   **failed** because that is not a Makefile target. `make test` then initially
   **failed** under strict GCC because a one-line capability diagnostic branch
   triggered `-Wmisleading-indentation`; braces/line structure were corrected
   before rerunning.
2. `make clean && make test`: **passed**. This built both `ftms.c` and
   `capabilities.c` with strict C99, ran the existing codec adapter, validated the
   separate capability corpus schema/unique IDs (34 fixture IDs), executed the C
   capability unit test, and ran the ASan+UBSan 10,000-iteration bounded evidence
   fuzz loop. The existing codec runner remains 42/97 implemented and 55 explicitly
   unsupported; that result is not capability-corpus conformance.
3. The same command ran the isolated-prefix archive matrix after adding
   `capabilities.c`: GCC and Clang C archives were consumed by C and C++11 callers;
   both consumers call `ftms_capability_requirements`. All six combinations passed.

At this stage the capability fixture JSON recorded scenario inventory and schema
identity. A complete JSON-to-C capability driver with exact normalized report
comparison remains required before these fixtures can be reported as executable C
conformance; no such pass claim is made here.

## Capability driver correction (2026-09-27)

The capability corpus now has a host-only `capability_driver.c` and
`capability_adapter.py`. The driver accepts bounded textual snapshots, calls both
requirements and `ftms_evaluate_capabilities`, and emits the complete report plus
ordered observations and diagnostics. The adapter validates the strict JSON schema,
enforces unique IDs, invokes that driver, and compares every JSON value exactly.
At that stage this was an executable seed fixture, not a completed capability
corpus. `make build/test-codec` was again attempted and failed because no such
target exists; direct strict compilation of the driver and its empty complete-scope
fixture passed. The legacy codec corpus remains separate and unchanged.

## Completed capability milestone (2026-09-27)

The earlier inventory/seed checks did not satisfy this milestone. Review found
incorrect power/heart-rate range mapping, unknown Feature declarations falling
through to satisfied prerequisites, and incomplete discovery hiding relevant
contradictions. The interpreter was rewritten with explicit target-to-range
mapping, separate declaration/prerequisite/reason fields, conservative scope and
discovery handling, duplicate ambiguity, and preflighted output atomicity.
These supersede the earlier provisional capability evidence, not the codec v1
corpus or its immutable expected values.

Incremental commands/results, in order:

1. `make -C packages/c test` after the rewrite **failed** at the stale native
   `operations[4].opcode == 2` expectation. Operations now use wire-opcode order,
   and the assertion was corrected to index 2. This is explicitly part of the
   new, unreleased capability contract; no published codec API changed.
2. Replaced the inventory/seed with literal snapshot/report templates and exact
   per-case edits, a strict schema, an actual compiled C bridge and a complete
   report comparator. The bridge emits actual decoded range kinds and every
   operation/observation/diagnostic field, not input echoes. Native sentinel
   indices normalize to JSON null instead of a host-dependent `SIZE_MAX` number.
3. `python3 -m unittest tests/test_capability_corpus.py` first **failed** schema
   validation because a manually authored expected UUID omitted two zero bytes.
   Corrected that literal to the canonical full Machine Status UUID; schema and
   driver rerun **passed 40/40**. Expected reports were not replaced with driver
   output to obtain a pass.
4. Direct strict C99 compilation of `test_codec.c` + `test_capabilities.c`, then
   execution: **passed**. The four capability suites isolate all 17 target bits,
   all 21 opcode positions and optional markers, five range relationships,
   unread/failed/security/malformed states, unknown raw bits, all six observed
   measurement families, contradictory/duplicate/scope evidence, nulls, invalid
   enums, count overflow, exact capacity/canaries, and untouched error outputs.
5. Added the remaining scope/duplicate/multiple-family/range cases and comparator
   mutations. `python3 -m unittest tests/test_capability_corpus.py`: **14 passed**;
   direct capability adapter: **49/49 passed**, zero failed/unsupported/skipped.
   Mutations reject wrong feature words, range kind/divisor/unit, operation fields,
   UUIDs, omitted evidence, wrong diagnostics, JSON type coercion, malformed
   fixtures, duplicate IDs and false success accounting. This corpus is separate
   from the 97 codec cases.
6. `make test` from `packages/c`: **passed**, including strict GCC units, Clang
   ASan+UBSan units, 10,000 deterministic bounded codec/capability snapshots
   (exact requirements, input preservation, capacity failures and buffer canaries),
   both corpus runners, and six isolated-prefix C archive/C or C++11 consumers.
   Both consumers now call the evaluator and assert meaningful returned fields,
   not only requirements or symbol/header compilation.
7. Initial `clang --target=arm-none-eabi ... -ffreestanding -c src/capabilities.c`
   **failed** because this environment has no target `string.h` sysroot. Removed
   the hosted header dependency using byte operations in the actual source (no
   fake header/sysroot). Recompiled and re-ran sanitized native units: **passed**.
8. Final `make -C packages/c test`: **passed again** after that source correction.
   Final `make -C packages/c check-embedded`: **passed compile-only** with Clang
   22.1.8, `--target=arm-none-eabi -mcpu=cortex-m0 -mthumb -std=c99 -Oz
   -ffreestanding -fstack-usage` and strict warnings. Object sizes were:

   | Object | text | data | bss |
   | --- | ---: | ---: | ---: |
   | Feature/range codecs | 258 | 0 | 0 |
   | Capabilities | 2242 | 0 | 0 |

   `nm -u` reports no codec undefined symbols, and capability references to
   `ftms_decode_features`, `ftms_decode_range`, and **`__aeabi_memclr4`**. The first
   two resolve from the codec object; the compiler runtime must provide the last.
   Stack reports show 648-byte frames for each public capability function and
   200 bytes for its internal evaluator; these are individual compiler estimates,
   **not** complete call-chain, interrupt, or whole-firmware stack bounds. These
   optimized sizes should not be conflated with the older 600-byte codec build
   using different flags. No embedded executable was linked or run.
9. Final `env -u TMPDIR pnpm verify`: **passed**: root lint, TypeScript checking,
   350 tests across 8 files, 97/97 TypeScript codec vectors, linked and packed
   consumers, unchanged 42-file tarball allowlist, exports, runtime neutrality,
   browser resolution and declarations. TypeScript source bytes are unchanged
   from their pre-migration `HEAD:src/*` counterparts; only its roadmap README
   was updated during this milestone. No npm version/export/release change was
   made for capabilities.
10. `git diff --check`: **passed**. Schema/vector bytes in `shared/conformance/v1`
    were compared directly to `HEAD:conformance/v1/*`: **identical**. All changes
    remain local/unstaged/uncommitted on `scaffold/native-capabilities`; the main
    checkout is clean at the original base. No commit, merge, push, publish,
    install of a toolchain, remote mutation, or hardware/control action occurred.

Final test environment: GCC/G++ 16.2.1, Clang/Clang++ 22.1.8, Python 3.14.7,
jsonschema 4.26.0. Source HEAD is
`41023a60cff6efdeef5e36730c3d7356a91d26b6`, **dirty true**. Reports enumerate each
capability case/outcome and all unsupported codec IDs; category counts are derived
from the loaded corpus. Final capability counts are discovery 12, duplicates 3,
features 5, forward-compatibility 2, measurements 7, operations 4, properties 8,
ranges 8. The codec runner still reports 42 passed, 55 unsupported, 0 failed,
0 skipped, `complete=false`; capability `complete=true` does not alter that.

Final SHA-256 identity (recorded from the actual final runners):

| Asset/contract | SHA-256 |
| --- | --- |
| Capability schema | `7df65ac9f26acde97974d8b81a91e6ce7046d8ba5ddc9125438aa4fd23d1ae4e` |
| Capability vectors | `83f748575534a252ebb7ecf5f658073628e16f3224f832d9e7e7b7568a1465db` |
| Capability corpus README | `736ad7619d05efc38b870b4f22c2e3e1a2bfee6c7ad1e0326f4be9787aeadacc` |
| Capability protocol contract | `6da7107ff8cb49ef54b549377098463664ee8ceb5547df9d654658604a78b9fa` |
| Codec schema (unchanged) | `e6d976172a32e3124602d17e46ed5fbab337f4f1d6535aec85a83069637268e0` |
| Codec vectors (unchanged) | `70125aa46a9272e3a0be7daf07fcf32161cab276f30d056ab64caca24b38fdc7` |
| Codec corpus README (new capability link only) | `a2c67ddf007502de19aac88aafef345f6741d15c83e53dd6652e35a753ad706e` |

Residual gates: remaining measurement/status/control and equipment-side codecs,
native release/install tooling, complete embedded link/runtime and resource
validation, real equipment/mobile interoperability, PTS and qualification. The
interpreter itself never performs I/O or authorizes a control procedure.
