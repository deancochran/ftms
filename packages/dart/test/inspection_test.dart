import 'package:deancochran_ftms/deancochran_ftms.dart';
import 'package:test/test.dart';

import 'support/value_helpers.dart';

void main() {
  final Map<String, Object?> corpus = fixture('inspection');
  for (final Object? raw in objects(corpus['cases'])) {
    final Map<String, Object?> c = object(raw);
    final String id = c['id']! as String;
    test('[inspection/$id]', () {
      final Map<String, Object?>? options = c['options'] == null
          ? null
          : object(c['options']);
      final ResistanceRangeFormat format =
          options?['resistanceFormat'] == 'signed16Tenths'
          ? ResistanceRangeFormat.signed16Tenths
          : ResistanceRangeFormat.uint8Whole;
      expect(
        inspectSupportedRange(
          RangeKind.values.byName(c['kind']! as String),
          wire(c['bytes']),
          resistanceFormat: format,
        ).toJson(),
        c['expected'],
      );
    });
  }
}
