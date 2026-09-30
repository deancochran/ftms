import 'dart:math';
import 'dart:typed_data';

import 'package:deancochran_ftms/deancochran_ftms.dart';
import 'package:test/test.dart';

void main() {
  test('measurement encoder rejects contradictory raw evidence', () {
    MeasurementRaw raw({
      bool more = false,
      bool backward = false,
      int count = 0,
      int absentValue = 0,
    }) => MeasurementRaw(
      kind: MeasurementKind.treadmill,
      flags: 0,
      present: 1,
      unavailable: 0,
      values: [100, absentValue, ...List<int>.filled(28, 0)],
      moreData: more,
      backward: backward,
      bytesRead: count,
    );
    for (final value in [
      raw(more: true),
      raw(backward: true),
      raw(count: 99),
      raw(absentValue: 77),
    ]) {
      expect(
        () => encodeMeasurement(value),
        throwsA(isA<MeasurementCodecException>()),
      );
    }
    expect(encodeMeasurement(raw()), [0, 0, 100, 0]);
    final slots = List<int>.filled(30, 0)..[9] = 1;
    expect(
      () => encodeMeasurement(
        MeasurementRaw(
          kind: MeasurementKind.treadmill,
          flags: 0x81,
          present: (1 << 9) | (1 << 10) | (1 << 11),
          unavailable: 1 << 9,
          values: slots,
          moreData: true,
        ),
      ),
      throwsA(isA<MeasurementCodecException>()),
    );
  });

  test('measurement words reject bits outside wire widths on VM and JS', () {
    for (final mask in [0x40000000, 0x100000000]) {
      expect(
        () => MeasurementRaw(
          kind: MeasurementKind.treadmill,
          flags: 0,
          present: mask,
          unavailable: 0,
          values: List<int>.filled(30, 0),
        ),
        throwsA(isA<MeasurementCodecException>()),
      );
      expect(
        () => MeasurementRaw(
          kind: MeasurementKind.treadmill,
          flags: mask,
          present: 0,
          unavailable: 0,
          values: List<int>.filled(30, 0),
        ),
        throwsA(isA<MeasurementCodecException>()),
      );
    }
  });

  test('training encoder preserves owned text and validates its offset', () {
    final status = TrainingStatus.fromText(13, 'manual');
    expect(
      decodeTrainingStatus(encodeTrainingStatus(status)).toJson(),
      status.toJson(),
    );
    final bytes = Uint8List.fromList([97]);
    final invalid = TrainingStatus(
      1,
      1,
      bytes,
      textPresent: true,
      textOffset: 999,
    );
    expect(() => encodeTrainingStatus(invalid), throwsArgumentError);
    bytes[0] = 98;
    expect(invalid.text, [97]);
    invalid.text[0] = 99;
    expect(invalid.text, [97]);
  });

  test('all spin-down actions and actionless statuses encode explicitly', () {
    for (var action = 1; action <= 4; action++) {
      expect(encodeMachineStatus(MachineStatus(20, action: action)), [
        20,
        action,
      ]);
    }
    expect(
      () => encodeMachineStatus(const MachineStatus(1, action: 1)),
      throwsArgumentError,
    );
  });

  test(
    'deterministic arbitrary bytes never cause accidental index failures',
    () {
      final random = Random(23224);
      for (var iteration = 0; iteration < 2000; iteration++) {
        final storage = Uint8List.fromList(
          List.generate(random.nextInt(70) + 2, (_) => random.nextInt(256)),
        );
        final bytes = Uint8List.sublistView(storage, 1, storage.length - 1);
        for (final kind in MeasurementKind.values) {
          try {
            decodeMeasurement(kind, bytes);
          } on MeasurementCodecException catch (error) {
            expect(error.code, MeasurementCodecErrorCode.length);
            expect(
              bytes.length,
              lessThan(kind == MeasurementKind.crossTrainer ? 3 : 2),
            );
          }
        }
        decodeMachineStatus(bytes);
        decodeTrainingStatus(bytes);
        for (final operation in [decodeControlRequest, decodeControlResponse]) {
          try {
            operation(bytes);
          } on ControlCodecException catch (error) {
            expect(ControlErrorCode.values, contains(error.code));
          }
        }
      }
    },
  );
}
