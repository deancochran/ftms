import 'dart:convert';
import 'dart:typed_data';

import 'package:deancochran_ftms/deancochran_ftms.dart';
import 'package:test/test.dart';

import 'support/corpus.dart';

bool _selected(int flags, int bit) =>
    bit == 0 ? flags & 1 == 0 : flags & (1 << bit) != 0;

void main() {
  test('[matrix/all]', () {
    final document =
        jsonDecode(
              readCorpus(
                '../../shared/conformance/measurement-matrix/v1/layouts.json',
              ),
            )
            as Map<String, dynamic>;
    expect(document['contract'], 'ftms-measurement-matrix-v1');
    var directions = 0;
    var sentinels = 0;
    var reserved = 0;
    var prefixes = 0;
    for (final layout
        in (document['layouts'] as List<dynamic>)
            .cast<Map<String, dynamic>>()) {
      final kind = MeasurementKind.values[layout['kind'] as int];
      final flagBytes = layout['flagBytes'] as int;
      final groups = layout['optionalGroups'] as int;
      final baseFields = (layout['fields'] as List<dynamic>)
          .cast<List<dynamic>>();
      final variants =
          (kind == MeasurementKind.treadmill ||
              kind == MeasurementKind.crossTrainer ||
              kind == MeasurementKind.rower ||
              kind == MeasurementKind.indoorBike)
          ? 2
          : 1;
      for (var variant = 0; variant < variants; variant++) {
        final options = MeasurementFormatOptions(
          resistance: variant == 1 && kind != MeasurementKind.treadmill
              ? MeasurementResistanceFormat.signed16Tenths
              : MeasurementResistanceFormat.uint8Whole,
          treadmillPace: variant == 1 && kind == MeasurementKind.treadmill
              ? MeasurementTreadmillPaceFormat.uint8Legacy
              : MeasurementTreadmillPaceFormat.uint16,
        );
        for (var subset = 0; subset < 1 << groups; subset++) {
          for (var more = 0; more <= 1; more++) {
            for (
              var backward = 0;
              backward < (kind == MeasurementKind.crossTrainer ? 2 : 1);
              backward++
            ) {
              final flags = (subset << 1) | more | (backward << 15);
              final values = List<int>.filled(30, 0);
              var present = 0;
              final wire = BytesBuilder(copy: false);
              for (var i = 0; i < flagBytes; i++) {
                wire.addByte((flags >> (i * 8)) & 0xff);
              }
              for (final base in baseFields) {
                final bit = base[0] as int;
                var width = base[1] as int;
                final index = base[2] as int;
                var signed = base[3] == 1;
                if (variant == 1 &&
                    index == MeasurementField.resistance.index) {
                  width = 2;
                  signed = true;
                }
                if (variant == 1 &&
                    kind == MeasurementKind.treadmill &&
                    (index == MeasurementField.instantaneousPace.index ||
                        index == MeasurementField.averagePace.index)) {
                  width = 1;
                }
                if (!_selected(flags, bit)) {
                  continue;
                }
                final value = (index + 1) * (signed ? -1 : 1);
                values[index] = value;
                present |= 1 << index;
                for (var i = 0; i < width; i++) {
                  wire.addByte((value >> (i * 8)) & 0xff);
                }
              }
              final expected = wire.toBytes();
              final raw = MeasurementRaw(
                kind: kind,
                flags: flags,
                present: present,
                unavailable: 0,
                values: values,
                moreData: more == 1,
                backward: backward == 1,
                bytesRead: expected.length,
              );
              final decoded = decodeMeasurement(
                kind,
                expected,
                options: options,
              );
              expect(decoded.toJson(), equals(raw.toJson()));
              expect(
                encodeMeasurement(raw, options: options),
                orderedEquals(expected),
              );
              directions += 2;
            }
          }
        }

        Uint8List matrixWire(int flags, {int? sentinelIndex}) {
          final wire = BytesBuilder(copy: false);
          for (var i = 0; i < flagBytes; i++) {
            wire.addByte((flags >> (i * 8)) & 0xff);
          }
          for (final base in baseFields) {
            final bit = base[0] as int;
            var width = base[1] as int;
            final index = base[2] as int;
            var signed = base[3] == 1;
            final unavailable = base[4] == 1;
            if (variant == 1 && index == MeasurementField.resistance.index) {
              width = 2;
              signed = true;
            }
            if (variant == 1 &&
                kind == MeasurementKind.treadmill &&
                (index == MeasurementField.instantaneousPace.index ||
                    index == MeasurementField.averagePace.index)) {
              width = 1;
            }
            if (!_selected(flags, bit)) {
              continue;
            }
            final value = index == sentinelIndex
                ? (signed ? 0x7fff : (1 << (width * 8)) - 1)
                : (index + 1) * (signed ? -1 : 1);
            for (var i = 0; i < width; i++) {
              wire.addByte((value >> (i * 8)) & 0xff);
            }
            // A sentinel selection is asserted below through the decoded mask.
            assert(!unavailable || index != sentinelIndex || value >= 0);
          }
          return wire.toBytes();
        }

        MeasurementRaw matrixExpected(int flags, {int? sentinelIndex}) {
          final List<int> values = List<int>.filled(30, 0);
          var present = 0;
          var unavailable = 0;
          for (final List<Object?> base in baseFields) {
            final int bit = base[0]! as int;
            final int index = base[2]! as int;
            var signed = base[3] == 1;
            if (variant == 1 && index == MeasurementField.resistance.index) {
              signed = true;
            }
            if (!_selected(flags, bit)) {
              continue;
            }
            present |= 1 << index;
            if (index == sentinelIndex) {
              unavailable |= 1 << index;
            } else {
              values[index] = (index + 1) * (signed ? -1 : 1);
            }
          }
          return MeasurementRaw(
            kind: kind,
            flags: flags,
            present: present,
            unavailable: unavailable,
            values: values,
            moreData: flags & 1 != 0,
            backward:
                kind == MeasurementKind.crossTrainer && flags & 0x8000 != 0,
            reservedFlags: flags & ~((1 << (groups + 1)) - 1) != 0,
            bytesRead: matrixWire(flags, sentinelIndex: sentinelIndex).length,
          );
        }

        final all = ((1 << groups) - 1) << 1;
        for (final field in baseFields.where((field) => field[4] == 1)) {
          final wire = matrixWire(all, sentinelIndex: field[2] as int);
          final expected = matrixExpected(all, sentinelIndex: field[2] as int);
          final raw = decodeMeasurement(kind, wire, options: options);
          expect(raw.toJson(), equals(expected.toJson()));
          expect(
            encodeMeasurement(expected, options: options),
            orderedEquals(wire),
          );
          sentinels++;
        }
        final complete = matrixWire(all);
        for (var length = 0; length < complete.length; length++) {
          final prefix = Uint8List.sublistView(complete, 0, length);
          if (length < flagBytes) {
            expect(
              () => decodeMeasurement(kind, prefix, options: options),
              throwsA(isA<MeasurementCodecException>()),
            );
          } else {
            expect(
              decodeMeasurement(kind, prefix, options: options).truncated,
              isTrue,
            );
          }
          prefixes++;
        }
        final firstReserved = kind == MeasurementKind.crossTrainer
            ? 16
            : groups + 1;
        for (var bit = firstReserved; bit < flagBytes * 8; bit++) {
          final flags = all | (1 << bit);
          final raw = decodeMeasurement(
            kind,
            matrixWire(flags),
            options: options,
          );
          expect(raw.reservedFlags, isTrue);
          expect(
            () => encodeMeasurement(matrixExpected(flags), options: options),
            throwsA(isA<MeasurementCodecException>()),
          );
          reserved++;
        }
      }
    }
    expect(directions, 363520);
    expect(sentinels, 46);
    expect(reserved, 47);
    expect(prefixes, 315);
    // ignore: avoid_print
    print(
      'FTMS_MATRIX:{"structural":${directions ~/ 2},"directions":$directions,"sentinels":$sentinels,"rfu":$reserved,"prefixes":$prefixes}',
    );
  });
}
