# Deterministic FTMS simulation

## Design and research

This is a standalone protocol/session test harness. It simulates **behavioral
profiles**, not verified product models, and neither scans for nor controls BLE
equipment. Open Trainer, virtual peripherals and physical devices are explicitly
optional future work.

The design follows three researched principles:

1. [Deterministic simulation testing](https://antithesis.com/docs/resources/deterministic_simulation_testing/):
   replace external time and nondeterministic inputs with controllable events so
   failures can be replayed. Here, time is a supplied integer and all faults are
   explicit scenario steps. A full virtual machine/platform is unnecessary for
   these already-pure codecs.
2. [Model-based testing](https://fast-check.dev/docs/advanced/model-based-testing/):
   keep the test model simpler than the implementation and avoid comparing code
   to a copy of itself. Literal bytes/results are the oracle. C's production
   assembler mutates a bounded aggregate; the TS test harness collects decoded
   fragments and reduces them only at finalization. Existing encoders never
   generate expected measurement fixtures; control encoding takes literal values.
3. [Stable event ordering](https://docs.python.org/3/library/heapq.html#priority-queue-implementation-notes):
   use insertion order to break equal-time ties. Bounded static scripts use a sort
   by `(relative tick, source index)` instead of a heap: there are no dynamically
   scheduled callbacks. A priority queue would add complexity without changing
   this contract.

These sources informed the design; no external simulation service, framework or
new runtime dependency is required. Existing Vitest/Ajv and Python/jsonschema
validate the test artifacts. Seeded property-based exploration and shrinking can
be added later, but the current suite uses completely specified scripts rather
than claiming randomized coverage.

## Structure

| Path | Responsibility |
| --- | --- |
| `shared/simulation/README.md` | Language-neutral lifecycle, oracle and reporting contract |
| `shared/simulation/v1/schema.json` | Closed, bounded schema with discriminated event/result shapes |
| `shared/simulation/v1/scenarios.json` | Profiles, independent literal messages/results and canonical case references |
| `packages/typescript/test/simulation/` | Test-only session, reference adapter, typed reports and deterministic runner |
| `packages/typescript/test/simulation.test.ts` | Runner execution, determinism and mutation tests |
| `packages/c/tests/simulation_driver.c` | Bounded host-only stdin bridge to the actual C record API; no expected values accepted |
| `packages/c/tests/simulation_adapter.py` | Schema validation, event orchestration, exact comparisons and reporting |
| `packages/c/tests/test_simulation_adapter.py` | Harness/bridge rejection and mutation tests |

No production API, npm export, package dependency, existing conformance fixture,
release workflow or native-port scaffold is changed. Canonical capabilities and
control cases are referenced by ID, not copied into a second fixture collection.
Port-local runners do not depend on the other language's implementation.

## Coverage

The shared suite currently contains **10 profiles / 37 scenarios / 75 scheduled
steps**. Coverage includes:

- All six measurement families, standalone records and split records.
- Signed resistance for bike/cross-trainer/rower; one-byte treadmill pace.
- Exact raw values, signedness, masks and subsequent-field offsets.
- Stable same-tick ordering, out-of-order delivery, dropped packets, duplicates,
  malformed/empty/truncated/trailing inputs and Cross Trainer direction changes.
- Fixed expiry, unsigned tick wrap, stale generations, disconnect and reconnect.
- Complete/partial/contradictory capability observations and scripted control
  request/response codecs, including unsupported and unknown-result responses.
- Metatests that deliberately corrupt expectations and schema/reference inputs,
  fail bridge execution, and verify that failures cannot be counted as passes.

An FTMS record has no universal sequence number: completion does not prove that
all optional fragments arrived. The suite does not invent a loss detector.
Likewise, unknown legacy pace units remain raw values; no device interpretation
is inferred from packet length, manufacturer, or model name.

## Running and replaying

From the repository root:

```sh
# TypeScript only; no C compiler or Python process is invoked by this runner.
pnpm --filter @deancochran/ftms exec vitest run test/simulation.test.ts

# Full TypeScript verification, including simulation and unchanged package exports.
env -u TMPDIR pnpm verify

# Native simulation, bridge metatests, ASan/UBSan replay and the existing native suite.
make -C packages/c BUILD=build/simulationtest test

# Replay C scenarios after the native test command has built the three drivers.
python3 packages/c/tests/simulation_adapter.py packages/c/build/simulationtest/simulation-driver
```

The C runner expects `capability-driver` and `control-driver` beside the record
driver. All are built before simulation execution, including in a fresh build
directory. Existing CI invokes Vitest and `make test`, so the simulation is a real
gate, not an optional/manual-only check. No new CI job or passing placeholder is
needed. Normal and sanitized C runs each consume the full scenario corpus.

Both runners emit a JSON `simulation` report. A failure identifies its scenario,
source step index and logical time. Keep the exact input files and reported hashes
to replay it. Normal reports contain all traces, not just failures; corpus
identity includes every referenced schema/vector/comparison contract.

## Evidence boundary

TypeScript uses its **production codecs and capability evaluator inside a test
session harness**. C uses its **production record assembler, codecs and capability
evaluator**. Matching traces do not establish a production TypeScript assembler,
Bluetooth transport reliability, device interoperability or qualification.
Host tests, installed-consumer checks and embedded compilation remain separate
evidence streams.

### Implementation verification

Verified locally against base `77d2c6f4e2ebcb374ddbbd43e5b807d1e2e61f5b`:

- `env -u TMPDIR pnpm verify`: **536 tests / 13 files**, lint, types, build and
  packed-package checks passed, with unchanged published API/export boundaries.
- `make BUILD=build/simulation-clean-final test`: a fresh native build passed the
  existing corpora, strict/sanitized suites, installed consumers and source-bundle
  checks. Normal and ASan/UBSan simulation replay each passed **37/37 scenarios,
  75/75 steps**, with no unsupported/skipped outcomes or runner errors.
- TypeScript and native simulation report traces and per-file identities matched
  exactly. This comparison supplements each runner's independently specified
  expected values.
- Independent review found no blocking defect. Its null-input validation gap
  was corrected by distinguishing omitted Python input from explicit JSON null.

Simulation schema SHA-256:
`6b9bad8d085a93b439fd6d6d89be63f913004932908aaad8700a70a942fe1072`.
Scenario content SHA-256:
`ca1eb8867dc65853f03178b420ac9bc2b7b93a034db2f00771ef84103cb19662`.
Comparison contract SHA-256:
`352982b78454110b204b15065179d38c66185ff8de1dd818e519b1eba5732384`.
The report also includes exact referenced capability/control identities. No
canonical conformance vectors or schemas were altered.

Optional future extensions: seeded fault exploration with shrinkable replay
traces; stateful command ownership/queue policies; an Open Trainer adapter; virtual
BLE; physical-device validation; and Swift/Kotlin ports. None is required to run
or pass this standalone suite.
