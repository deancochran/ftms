# Roadmap and non-goals

This is direction, not a dated delivery promise. The [release matrix](released-packages.md)
is authoritative for what is available from this source tree.

## Available

- TypeScript, C, Swift and Kotlin `FullWire` protocol codecs with static capability
  evidence; Python provides a partial-alpha `FullWire` raw-codec surface without
  capability evaluation in the published artifact, plus an unreleased source
  evaluator verified against the shared capability corpus; Rust provides an unpublished `no_std` `FullWire` raw-codec
  source candidate with range inspection and no capability evaluator.
- Installed-consumer examples, versioned fixtures and host verification.
- Explicit malformed-input diagnostics and caller-selected format options.
- Role-based [support profiles](support-profiles.md) that separate wire directions
  from optional package modules and Bluetooth/application responsibilities.

## Adoption focus

- Consistent installation and release guidance.
- Runnable current-release examples and a task-oriented API reference.
- Tested byte-boundary recipes and actionable contributor reports.
- Executable profile-aware directional accounting in package conformance reports,
  without changing immutable codec-v1 assets.

## Separate future proposals

- Offline packet playground.
- Reviewed external application integrations and additional equipment evidence.
- Public native package-manager registration.
- Additional native ports only after a named adopter selects a justified profile
  and supplies implementation, compiler and consumer evidence.
- Any package namespace migration, with an explicit compatibility plan.

These proposals do not establish availability, release dates or commitments.
Other development branches are not releases from this checkout.

## Non-goals of the protocol core

BLE connections, OS permissions, UI frameworks, session timers, reconnect policy,
automatic device-format inference, workout scheduling and actuator authorization.
Fixture coverage is not Bluetooth qualification. Broad “works with every device”
or “best implementation” claims require evidence not established by these libraries.
