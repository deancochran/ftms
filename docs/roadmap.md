# Roadmap and non-goals

This is direction, not a dated delivery promise. The [release matrix](released-packages.md)
is authoritative for what is available from this source tree.

## Available

- TypeScript and C bidirectional protocol codecs and static capability evidence.
- Installed-consumer examples, versioned fixtures and host verification.
- Explicit malformed-input diagnostics and caller-selected format options.

## Adoption focus

- Consistent installation and release guidance.
- Runnable current-release examples and a task-oriented API reference.
- Tested byte-boundary recipes and actionable contributor reports.

## Separate future proposals

- Offline packet playground.
- Reviewed external application integrations and additional equipment evidence.
- Public native package-manager registration.
- Additional native ports after implementation, compiler and consumer evidence.
- Any package namespace migration, with an explicit compatibility plan.

These proposals do not establish availability, release dates or commitments.
Other development branches are not releases from this checkout.

## Non-goals of the protocol core

BLE connections, OS permissions, UI frameworks, session timers, reconnect policy,
automatic device-format inference, workout scheduling and actuator authorization.
Fixture coverage is not Bluetooth qualification. Broad “works with every device”
or “best implementation” claims require evidence not established by these libraries.
