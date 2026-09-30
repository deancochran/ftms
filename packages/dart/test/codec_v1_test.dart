import 'dart:typed_data';

import 'package:test/test.dart';

import 'support/conformance.dart';
import 'support/legacy_adapter.dart';

void main() {
  final corpus = corpusObject('../../shared/conformance/v1/vectors.json');
  const categories = [
    'features',
    'ranges',
    'controls',
    'controlResponses',
    'measurements',
    'statuses',
    'diagnostics',
  ];
  final ids = <String>{};
  for (final category in categories) {
    final cases = corpus[category]! as List<Object?>;
    for (final entry in cases) {
      final c = entry! as Map<String, Object?>;
      final id = c['id']! as String;
      if (!ids.add(id)) throw StateError('Duplicate corpus ID: $id');
      conformanceCase('codec', id, () {
        final bytes = Uint8List.fromList(
          (c['bytes'] as List<Object?>? ?? []).cast<int>(),
        );
        switch (category) {
          case 'features':
            final actual = legacyFeatures(bytes);
            if (c.containsKey('expected')) {
              expectExact(actual, c['expected']);
            } else {
              expect(
                actual.entries.where((e) => e.value).map((e) => e.key).toSet(),
                (c['expectedTrue']! as List<Object?>).toSet(),
              );
            }
          case 'ranges':
            final actual = legacyRange(c['kind']! as String, bytes);
            if (c.containsKey('expectedError')) {
              expectSubset(actual, {
                'ok': false,
                'error': {'code': c['expectedError']},
              });
            } else {
              expectExact(actual, {
                ...c['expected']! as Map<String, Object?>,
                'kind': c['kind'],
              });
            }
          case 'controls':
            expectExact(
              legacyRequest(c['request']! as Map<String, Object?>),
              c['expectedBytes'],
            );
          case 'controlResponses':
            final actual = legacyResponse(bytes);
            if (c.containsKey('expectedError')) {
              expectSubset(actual, {
                'ok': false,
                'error': {'code': c['expectedError']},
              });
            } else {
              expectExact(actual, c['expected']);
            }
          case 'measurements' || 'statuses' || 'diagnostics':
            final parsed = legacyParse(
              c['characteristicUuid']! as String,
              bytes,
            );
            if (c.containsKey('expectedMetrics')) {
              expectMetrics(
                parsed.metrics,
                c['expectedMetrics']! as Map<String, Object?>,
              );
            }
            if (c.containsKey('expectedStatus')) {
              expectSubset(parsed.status, c['expectedStatus']);
            }
            if (category == 'diagnostics') {
              expectExact(parsed.truncated, c['expectedTruncated']);
              for (final issue in c['expectedIssues']! as List<Object?>) {
                expect(parsed.issues, contains(issue));
              }
              if (c.containsKey('expectedStatusCode')) {
                expect(parsed.status.containsKey('code'), isTrue);
                expectExact(parsed.status['code'], c['expectedStatusCode']);
              }
            }
          default:
            fail('Unhandled corpus category $category');
        }
      });
    }
  }
  test('codec-v1 category accounting', () {
    expect(
      categories.map((c) => (corpus[c]! as List<Object?>).length).toList(),
      [35, 7, 21, 12, 8, 4, 10],
    );
    expect(ids.length, 97);
  });
}
