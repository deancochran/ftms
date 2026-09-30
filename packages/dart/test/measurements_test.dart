import 'dart:convert';
import 'dart:typed_data';

import 'package:deancochran_ftms/deancochran_ftms.dart';
import 'package:test/test.dart';

import 'support/corpus.dart';

Map<String, Object?> _object(Object? value) => value! as Map<String, Object?>;
List<Object?> _list(Object? value) => value! as List<Object?>;
int _integer(Object? value) => value! as int;
bool _boolean(Object? value) => value! as bool;

MeasurementRaw _expected(Map<String, Object?> decoded) => MeasurementRaw(
  kind: MeasurementKind.values[_integer(decoded['kind'])],
  flags: _integer(decoded['flags']),
  present: _integer(decoded['present']),
  unavailable: _integer(decoded['unavailable']),
  values: _list(decoded['values']).map(_integer).toList(growable: false),
  moreData: _integer(decoded['moreData']) == 1,
  backward: _integer(decoded['backward']) == 1,
  truncated: _integer(decoded['truncated']) == 1,
  trailingBytes: _integer(decoded['trailingBytes']) == 1,
  reservedFlags: _integer(decoded['reservedFlags']) == 1,
  bytesRead: _integer(decoded['bytesRead']),
);

void main() {
  final Map<String, Object?> corpus = _object(
    jsonDecode(
      readCorpus('../../shared/conformance/measurements/v1/vectors.json'),
    ),
  );
  final List<Object?> cases = _list(corpus['cases']);

  test('measurement corpus identity', () {
    final Map<String, Object?> schema = _object(
      jsonDecode(
        readCorpus('../../shared/conformance/measurements/v1/schema.json'),
      ),
    );
    expect(schema[r'$id'], 'urn:ftms:measurements:conformance:v1');
    expect(_list(corpus['fieldOrder']), hasLength(30));
    expect(cases, hasLength(26));
  });

  for (final Object? entry in cases) {
    final Map<String, Object?> item = _object(entry);
    final String id = item['id']! as String;
    test('[measurements/$id]', () {
      final Map<String, Object?> decoded = _object(item['decoded']);
      final Uint8List bytes = Uint8List.fromList(
        _list(item['bytes']).map(_integer).toList(growable: false),
      );
      final int kindValue = _integer(item['kind']);
      if (decoded.containsKey('error')) {
        if (kindValue < 0 || kindValue >= MeasurementKind.values.length) {
          // The typed public boundary makes an invalid enum unrepresentable.
          expect(_integer(decoded['error']), 3);
        } else {
          expect(
            () => decodeMeasurement(MeasurementKind.values[kindValue], bytes),
            throwsA(isA<MeasurementCodecException>()),
          );
        }
        return;
      }
      final MeasurementRaw expected = _expected(decoded);
      final MeasurementRaw actual = decodeMeasurement(expected.kind, bytes);
      expect(actual.toJson(), equals(decoded));
      if (_boolean(item['encode'])) {
        // The encode input is the literal corpus object, never decode output.
        expect(encodeMeasurement(expected), orderedEquals(bytes));
      }
    });
  }

  test('measurement mutation and partial evidence', () {
    final Uint8List bytes = Uint8List.fromList(<int>[0x02, 0x00, 0x34]);
    final MeasurementRaw raw = decodeMeasurement(
      MeasurementKind.indoorBike,
      bytes,
    );
    expect(raw.truncated, isTrue);
    expect(raw.present, 0);
    expect(raw.bytesRead, 2);
    expect(() => raw.values[0] = 42, throwsUnsupportedError);
    bytes[0] = 0;
    expect(raw.flags, 2);
  });
}
