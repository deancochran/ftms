import 'dart:convert';
import 'dart:typed_data';

import 'package:deancochran_ftms/deancochran_ftms.dart';
import 'package:test/test.dart';

import 'support/corpus.dart';

Map<String, Object?> _object(Object? value) => value! as Map<String, Object?>;
List<Object?> _list(Object? value) => value! as List<Object?>;
int _integer(Object? value) => value! as int;

MeasurementRaw _expected(Map<String, Object?> value) => MeasurementRaw(
  kind: MeasurementKind.values[_integer(value['kind'])],
  flags: _integer(value['flags']),
  present: _integer(value['present']),
  unavailable: _integer(value['unavailable']),
  values: _list(value['values']).map(_integer).toList(growable: false),
  moreData: _integer(value['moreData']) == 1,
  backward: _integer(value['backward']) == 1,
  truncated: _integer(value['truncated']) == 1,
  trailingBytes: _integer(value['trailingBytes']) == 1,
  reservedFlags: _integer(value['reservedFlags']) == 1,
  bytesRead: _integer(value['bytesRead']),
);

void main() {
  final Map<String, Object?> document = _object(
    jsonDecode(
      readCorpus('../../shared/conformance/compatibility/v1/vectors.json'),
    ),
  );
  final Iterable<Map<String, Object?>> cases = _list(document['cases'])
      .map(_object)
      .where((Map<String, Object?> item) => item['area'] == 'measurement');
  for (final Map<String, Object?> item in cases) {
    final String id = item['id']! as String;
    test('[compatibility/$id]', () {
      final Map<String, Object?> optionMap = _object(item['options']);
      final MeasurementFormatOptions options = MeasurementFormatOptions(
        resistance: optionMap['resistanceFormat'] == 'signed16Tenths'
            ? MeasurementResistanceFormat.signed16Tenths
            : MeasurementResistanceFormat.uint8Whole,
        treadmillPace: optionMap['treadmillPaceFormat'] == 'uint8Legacy'
            ? MeasurementTreadmillPaceFormat.uint8Legacy
            : MeasurementTreadmillPaceFormat.uint16,
      );
      final Uint8List bytes = Uint8List.fromList(
        _list(item['bytes']).map(_integer).toList(growable: false),
      );
      final MeasurementRaw expected = _expected(_object(item['expected']));
      final MeasurementRaw actual = decodeMeasurement(
        expected.kind,
        bytes,
        options: options,
      );
      expect(actual.toJson(), equals(item['expected']));
      // The encode input is the literal compatibility expectation, never decoder output.
      expect(
        encodeMeasurement(expected, options: options),
        orderedEquals(bytes),
      );
    });
  }
  test('compatibility measurement count', () => expect(cases, hasLength(6)));
}
