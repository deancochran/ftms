import 'dart:typed_data';

import 'package:deancochran_ftms/deancochran_ftms.dart';
import 'package:test/test.dart';

import 'support/value_helpers.dart';

void main() {
  final Map<String, Object?> corpus = fixture('values');
  for (final Object? raw in objects(corpus['cases'])) {
    final Map<String, Object?> c = object(raw);
    final String id = c['id']! as String;
    test('[values/$id]', () {
      if (c['operation'] == 'features') {
        final Features input = Features(
          c['machine']! as int,
          c['target']! as int,
        );
        expect(encodeFeatures(input), wire(c['expectedBytes']));
        expect(
          decodeFeatures(wire(c['expectedBytes'])).toJson(),
          input.toJson(),
        );
      } else {
        final RangeKind kind = RangeKind.values.byName(c['kind']! as String);
        final SupportedRange input = SupportedRange(
          kind,
          c['minimum']! as int,
          c['maximum']! as int,
          c['increment']! as int,
          c['scaleDivisor']! as int,
          RangeUnit.values[c['unit']! as int],
        );
        expect(encodeSupportedRange(input), wire(c['expectedBytes']));
        expect(
          decodeSupportedRange(kind, wire(c['expectedBytes'])).toJson(),
          input.toJson(),
        );
      }
    });
  }
  test('values/input-view-and-output-mutation', () {
    final Uint8List source = Uint8List.fromList(<int>[
      9,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      0,
      9,
    ]);
    expect(decodeFeatures(Uint8List.sublistView(source, 1, 9)).machine, 0);
    final Uint8List encoded = encodeFeatures(const Features(1, 2));
    encoded[0] = 99;
    expect(encodeFeatures(const Features(1, 2))[0], 1);
  });
}
