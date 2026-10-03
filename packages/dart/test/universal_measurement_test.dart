import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:deancochran_ftms/deancochran_ftms.dart';
import 'package:test/test.dart';

void main() {
  test('canonical all-field packets pass through all six UUID routes', () {
    final corpus =
        jsonDecode(
              File(
                '../../shared/conformance/measurements/v1/vectors.json',
              ).readAsStringSync(),
            )
            as Map<String, dynamic>;
    var count = 0;
    for (final item in corpus['cases'] as List<dynamic>) {
      final fixture = item as Map<String, dynamic>;
      if (!(fixture['id'] as String).startsWith('equipment-') ||
          !(fixture['id'] as String).endsWith('-all-fields')) {
        continue;
      }
      final kind = fixture['kind'] as int;
      final expected = fixture['decoded'] as Map<String, dynamic>;
      final bytes = Uint8List.fromList(
        (fixture['bytes'] as List<dynamic>).cast<int>(),
      );
      final short = (0x2acd + kind).toRadixString(16);
      for (final uuid in [short, '0000$short-0000-1000-8000-00805f9b34fb']) {
        final result = decodeFtmsMeasurement(uuid, bytes);
        expect(result.status, MeasurementUuidDecodeStatus.known);
        expect(result.kind, MeasurementKind.values[kind]);
        expect(result.raw!.values, expected['values']);
        expect(result.raw!.present, expected['present']);
        expect(result.raw!.unavailable, expected['unavailable']);
        expect(result.raw!.bytesRead, expected['bytesRead']);
        expect(encodeMeasurement(result.raw!), bytes);
      }
      count++;
    }
    expect(count, 6);
  });
  test('UUID dispatch recognizes all six measurement families and aliases', () {
    for (final entry in <String, MeasurementKind>{
      '2acd': MeasurementKind.treadmill,
      '0x2ace': MeasurementKind.crossTrainer,
      '2acf': MeasurementKind.stepClimber,
      '2ad0': MeasurementKind.stairClimber,
      '2ad1': MeasurementKind.rower,
      '00002ad2-0000-1000-8000-00805f9b34fb': MeasurementKind.indoorBike,
    }.entries) {
      final result = decodeFtmsMeasurement(
        entry.key,
        Uint8List.fromList([0, 0]),
      );
      expect(result.status, MeasurementUuidDecodeStatus.known);
      expect(result.kind, entry.value);
      expect(result.raw, isNotNull);
    }
  });

  test('UUID dispatch keeps existing normalized and diagnostic evidence', () {
    final bike = decodeFtmsMeasurement(
      '2ad2',
      Uint8List.fromList([0x44, 0, 0x10, 0x0e, 0xb4, 0, 0xfa, 0]),
    );
    expect(bike.normalized!.speedMps, 10);
    expect(bike.normalized!.cadenceRpm, 90);
    expect(bike.normalized!.powerWatts, 250);

    final truncated = decodeFtmsMeasurement('2ad2', Uint8List.fromList([0]));
    expect(truncated.status, MeasurementUuidDecodeStatus.known);
    expect(truncated.raw!.truncated, isTrue);
    expect(truncated.normalized!.speedMps, isNull);
  });

  test(
    'UUID dispatch preserves unavailable, zero, legacy format and rejection',
    () {
      final unavailable = decodeFtmsMeasurement(
        '2ad2',
        Uint8List.fromList([0, 1, 0, 0, 0xff, 0xff, 0xff]),
      );
      expect(unavailable.raw!.valueAt(MeasurementField.speed), 0);
      expect(unavailable.normalized!.speedMps, 0);
      expect(unavailable.raw!.unavailable, isNot(0));
      expect(unavailable.normalized!.energyKcal, isNull);

      final legacy = decodeFtmsMeasurement(
        '2acd',
        Uint8List.fromList([0x20, 0, 0, 0, 120]),
        options: const MeasurementFormatOptions(
          treadmillPace: MeasurementTreadmillPaceFormat.uint8Legacy,
        ),
      );
      expect(legacy.raw!.valueAt(MeasurementField.instantaneousPace), 120);
      expect(legacy.normalized!.instantaneousPaceSecondsPer500m, isNull);
      expect(encodeMeasurement(legacy.raw!), [0x20, 0, 0, 0, 120]);
      expect(
        normalizeMeasurement(legacy.raw!).instantaneousPaceSecondsPer500m,
        isNull,
      );

      final signedResistance = decodeFtmsMeasurement(
        '2ad2',
        Uint8List.fromList([0x21, 0, 0xf6, 0xff]),
        options: const MeasurementFormatOptions(
          resistance: MeasurementResistanceFormat.signed16Tenths,
        ),
      );
      expect(signedResistance.normalized!.resistanceLevel, -1);
      expect(normalizeMeasurement(signedResistance.raw!).resistanceLevel, -1);
      expect(encodeMeasurement(signedResistance.raw!), [0x21, 0, 0xf6, 0xff]);

      for (final uuid in [
        '2ad3',
        '12342ad2-0000-1000-8000-00805f9b34fb',
        '00002ad20000-1000800000805f9b34fb',
      ]) {
        expect(
          decodeFtmsMeasurement(uuid, Uint8List(0)).status,
          MeasurementUuidDecodeStatus.unsupported,
        );
      }
    },
  );
}
