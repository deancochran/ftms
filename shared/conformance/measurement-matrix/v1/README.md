# Measurement structural matrix v1

Contract identity: `ftms-measurement-matrix-v1`. This is a separate structural
test contract, not an FTMS version, package version or replacement for any
existing literal measurement corpus. `layouts.json` is a test-only declaration
of field groups in wire order; runners do not import production layout tables.
Raw field indices refer to the established measurement comparison contract.

Source basis: FTMS 1.0.1 §§4.4–4.9 flag/group/sentinel definitions and the GATT
Specification Supplement characteristic definitions, as reconciled in
`docs/specification-audit.md`. Formats are the explicitly documented selections
in `shared/protocol/wire-compatibility.md`. The existing literal all-field
fixtures remain independent anchors; this generated matrix supplements them.
Agreement with this table alone is not independent proof of protocol correctness.

## Complete accounting

- Optional-group subsets: 4,096 / 16,384 / 256 / 512 / 4,096 / 4,096 for
  Treadmill / Cross Trainer / Step Climber / Stair Climber / Rower / Indoor Bike.
- Both More Data states; both Cross Trainer direction states.
- Default and legacy pace for Treadmill; default and signed resistance for Cross
  Trainer, Rower and Indoor Bike; one format each for Step and Stair Climber.
- Total **181,760** structural cases per port, each checked in decode and encode
  directions. Values distinguish field positions and exercise negative signed
  operands. Expected bytes, masks and all 30 values are independently constructed.
- **46** individual sentinel-field cases across those ten layout configurations.
  Unavailable values are zero in the comparison model, with mask bits retaining
  sentinel meaning. They are not zero physical measurements.
- **47** individual RFU-bit cases; decoding diagnoses them and encoding rejects.
- Every incomplete prefix of all ten complete layout configurations.
- C additionally supplies **10** complete snapshots and checks every planner
  budget from **0 through 64**, for **650** budget cases. Expected minimum feasible
  budget is flag bytes plus the largest indivisible group. Successful plans are
  decoded/reassembled and compared to the original snapshot; insufficient budgets
  must fail explicitly. Query count must agree with actual output count.

The C driver consumes **181,863** generated records (structural + sentinel + RFU
+ complete snapshots), both normally and under ASan/UBSan. TypeScript performs
the structural/sentinel/RFU checks inside one test, not 181,853 separate Vitest
test registrations. Do not conflate test-runner totals with generated cases.

## Runners and limits

- `packages/typescript/test/measurement-matrix.test.ts`
- `packages/c/tests/test_measurement_matrix.py` and its streaming native driver

Both are wired into the ordinary package verification commands. This is an
enumeration of field-presence structures, not every possible numeric value,
every combination of formats across unrelated characteristics, every fragment
loss sequence or real-device qualification. Existing numeric, fuzz, simulation
and literal conformance suites remain necessary. No private capture is included.
