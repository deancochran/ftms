# Historical audits and evidence

This index separates recorded observations from current installation and support
guidance. Each linked record retains its original commit, date, scope and limits;
its package versions and test counts do not automatically describe today's source.
Use [current releases](released-packages.md), [coverage](coverage.md) and
[support profiles](support-profiles.md) for current claims.

## Publication evidence

The [release ledger](released-packages.md#release-evidence-ledger) retains exact
published identities, hashes and verification URLs. Package changelogs explain
what changed; the ledger establishes which artifacts were actually checked.

## Historical implementation and documentation checks

- [Adoption verification](adoption-verification.md)
- [Compatibility verification](compatibility-verification.md)
- [Boundary hardening](hardening-verification.md)
- [Cross-port parity review](parity.md)
- [Page-by-page implementation audit](page-implementation-audit.md)
- [Site verification before publication](site-verification.md)
- [Dated device-compatibility gap ledger](device-compatibility.md)
- [C candidate release-readiness](../packages/c/docs/release-readiness.md)
- [C verification record](../packages/c/docs/verification.md)
- [Rust verification record](../packages/rust/docs/verification.md)
- [Dart historical candidate verification](../packages/dart/doc/verification.md)

These are evidence records, not alternative release runbooks. Follow the
[release procedure](releasing.md) for new artifacts.

## Protocol authority and reproducible checks

The [specification audit](specification-audit.md) records protocol/errata reasoning
and its evidence limits; it is not obsolete merely because it is called an audit.
[Shared conformance contracts](../shared/conformance/README.md) remain authoritative
for comparisons. Do not rewrite hash-pinned contracts as documentation cleanup.

## Physical equipment

Follow the [equipment-testing procedure](equipment-testing.md). The
[passive KICKR CORE pilot](equipment-results/2026-09-29-kickr-core-linux.md) describes
one bounded observation, not universal compatibility. [Simulation](simulation.md),
host tests, compile-only checks, public consumers, device execution and Bluetooth
qualification are separate evidence categories.
