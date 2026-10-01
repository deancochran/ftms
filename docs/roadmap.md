# Roadmap and non-goals

This is direction, not a dated delivery promise. The [release matrix](released-packages.md)
is authoritative for what is available from this source tree.

## Available

- TypeScript, C, Swift and Kotlin `FullWire` protocol codecs with static capability
  evidence; Python 0.1.0a2 provides a published alpha `FullWire` raw-codec surface
  with static capability evaluation verified against the shared corpus;
  Rust 0.1.1 is a released
  `no_std` `FullWire` crate with range inspection, evaluator, normalized
  Feature/measurement/range/control/status views and record modules, with all
  97 normalized codec-v1 cases accounted for.
- Installed-consumer examples, versioned fixtures and host verification.
- Explicit malformed-input diagnostics and caller-selected format options.
- Role-based [support profiles](support-profiles.md) that separate wire directions
  from optional package modules and Bluetooth/application responsibilities.

## Adoption focus

- Consistent installation and release guidance.
- Runnable current-release examples and a task-oriented API reference.
- Tested byte-boundary recipes and actionable contributor reports.
- Ecosystem-specific [consumer-adapter recipes](architecture.md#consumer-adapter-seam)
  that leave transport and session dependencies outside the protocol packages.
- Executable profile-aware directional accounting in package conformance reports,
  without changing immutable codec-v1 assets.

## Separate future proposals

- Offline packet playground.
- Reviewed external application integrations and additional equipment evidence.
- Granular package entry points or artifact splits only after measured consumer
  size/startup evidence justifies the additional public surface.
- Public native package-manager registration.
- Additional native ports only after a named adopter selects a justified profile
  and supplies implementation, compiler and consumer evidence.
- Any package namespace migration, with an explicit compatibility plan.

These proposals do not establish availability, release dates or commitments.
Other development branches are not releases from this checkout.

## Non-goals of the protocol core

BLE connections, OS permissions, UI frameworks, session timers, reconnect policy,
automatic device-format inference, workout scheduling and actuator authorization.
A cross-language transport/session adapter interface is also a non-goal; consumer
adapters remain ecosystem- and application-owned.
Fixture coverage is not Bluetooth qualification. Broad “works with every device”
or “best implementation” claims require evidence not established by these libraries.
