# Flutter integration

This is a pure Dart dependency, not a plugin. No Android manifest entry, iOS
entitlement, native build hook or Flutter SDK dependency is introduced by FTMS.
Your BLE plugin and application still require their own platform setup.

Pass a plugin's byte notification to `decodeMeasurement`. If the plugin returns
`List<int>`, validate any non-byte source before conversion: `Uint8List.fromList`
truncates out-of-range elements. BLE-provided bytes should already be 0–255.

```dart
final raw = decodeMeasurement(
  MeasurementKind.indoorBike,
  Uint8List.fromList(notification),
);
final view = normalizeMeasurement(raw);
```

Do not fabricate absent metrics as zero. Check raw diagnostics and presence masks
before aggregating. `More Data` is protocol evidence, not an instruction to own a
timer or merge notifications without a caller-defined fragment policy.

Construct `CapabilitySnapshot` from the selected service's discovery and read
results. UUIDs in this evidence interface are 32 lowercase hex digits in display
order, without hyphens. Preserve read failures and duplicate observations rather
than discarding them. A complete static report is still not current permission
to send Control Point commands.

CI consumer builds are compilation/package evidence. Actual phone/browser BLE
operation and safe equipment control require separately authorized device tests.
