import 'package:deancochran_ftms/deancochran_ftms.dart';
import 'package:test/test.dart';

import 'support/value_helpers.dart';

void main() {
  final Map<String, Object?> corpus = fixture('compatibility');
  for (final Object? raw in objects(corpus['cases'])) {
    final Map<String, Object?> c = object(raw);
    if (c['area'] != 'range') continue;
    final String id = c['id']! as String;
    test('[compatibility/$id]', () {
      final Map<String, Object?> options = object(c['options']);
      final ResistanceRangeFormat format =
          options['resistanceFormat'] == 'signed16Tenths'
          ? ResistanceRangeFormat.signed16Tenths
          : ResistanceRangeFormat.uint8Whole;
      final Map<String, Object?> expected = object(c['expected']);
      final SupportedRange input = SupportedRange(
        RangeKind.resistance,
        expected['minimum']! as int,
        expected['maximum']! as int,
        expected['increment']! as int,
        expected['scaleDivisor']! as int,
        RangeUnit.values[expected['unit']! as int],
      );
      expect(
        encodeSupportedRange(input, resistanceFormat: format),
        wire(c['bytes']),
      );
      expect(
        decodeSupportedRange(
          RangeKind.resistance,
          wire(c['bytes']),
          resistanceFormat: format,
        ).toJson(),
        expected,
      );
    });
  }
}
