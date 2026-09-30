import 'dart:typed_data';

import 'package:deancochran_ftms/deancochran_ftms.dart';
import 'package:test/test.dart';

void main() {
  test(
    'normalization preserves raw evidence and projects selected physical units',
    () {
      final raw = decodeMeasurement(
        MeasurementKind.indoorBike,
        Uint8List.fromList([
          0x60,
          0x08,
          0x68,
          0x01,
          0xf4,
          0xff,
          0x9c,
          0xff,
          0x85,
          0x03,
        ]),
        options: const MeasurementFormatOptions(
          resistance: MeasurementResistanceFormat.signed16Tenths,
        ),
      );
      final normalized = normalizeMeasurement(
        raw,
        options: const MeasurementFormatOptions(
          resistance: MeasurementResistanceFormat.signed16Tenths,
        ),
      );
      expect(identical(normalized.raw, raw), isTrue);
      expect(normalized.speedMps, closeTo(1, .000001));
      expect(normalized.resistanceLevel, closeTo(-1.2, .000001));
      expect(normalized.powerWatts, -100);
      expect(normalized.elapsedTimeSeconds, 901);
      expect(normalized.averagePaceSecondsPer500m, isNull);
    },
  );

  test('legacy treadmill pace remains raw but has no normalized unit', () {
    final raw = decodeMeasurement(
      MeasurementKind.treadmill,
      Uint8List.fromList([0x60, 0x04, 0xe8, 0x03, 42, 43, 0x85, 0x03]),
      options: const MeasurementFormatOptions(
        treadmillPace: MeasurementTreadmillPaceFormat.uint8Legacy,
      ),
    );
    final normalized = normalizeMeasurement(
      raw,
      options: const MeasurementFormatOptions(
        treadmillPace: MeasurementTreadmillPaceFormat.uint8Legacy,
      ),
    );
    expect(raw.valueAt(MeasurementField.instantaneousPace), 42);
    expect(normalized.instantaneousPaceSecondsPer500m, isNull);
    expect(normalized.averagePaceSecondsPer500m, isNull);
  });
}
