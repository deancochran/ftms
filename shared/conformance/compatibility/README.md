# Compatibility vectors

This additive corpus is separate from immutable `../v1`. Its literals describe
explicit caller-selected wire formats, never automatic device detection. Every
case has independently reviewed raw expectations and runs in both directions.

`schemaVersion: 1` identifies this compatibility fixture format. Runners validate
the exact schema, require globally unique IDs, and report every decode and encode
outcome. Measurement expectations are complete raw objects (all 30 field slots);
range expectations use raw minimum, maximum, increment, divisor, unit, and kind.

The `captured-characteristic` resistance profile records raw bytes and the selected
format only. Its divisor describes that selected layout and is not device-verification
or a display-unit claim. This corpus is host regression evidence, not Bluetooth
qualification.
