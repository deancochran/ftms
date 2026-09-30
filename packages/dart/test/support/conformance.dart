import 'dart:convert';

import 'package:test/test.dart';

import 'corpus.dart';

Map<String, Object?> corpusObject(String path) =>
    jsonDecode(readCorpus(path)) as Map<String, Object?>;

/// A stable name lets the external verifier account for actual test outcomes.
void conformanceCase(String corpus, String id, void Function() body) {
  test('[$corpus/$id]', body);
}

/// Recursive comparison preserving JSON types, including bool versus integer.
void expectExact(Object? actual, Object? expected, [String path = r'$']) {
  if (expected is Map<String, Object?>) {
    expect(actual, isA<Map<String, Object?>>(), reason: path);
    final object = actual! as Map<String, Object?>;
    expect(object.keys.toSet(), expected.keys.toSet(), reason: path);
    for (final key in expected.keys) {
      expectExact(object[key], expected[key], '$path.$key');
    }
  } else if (expected is List<Object?>) {
    expect(actual, isA<List<Object?>>(), reason: path);
    final values = actual! as List<Object?>;
    expect(values.length, expected.length, reason: path);
    for (var i = 0; i < expected.length; i++) {
      expectExact(values[i], expected[i], '$path[$i]');
    }
  } else {
    if (expected is bool) expect(actual, isA<bool>(), reason: path);
    if (expected is num) expect(actual, isA<num>(), reason: path);
    if (expected is String) expect(actual, isA<String>(), reason: path);
    expect(actual, expected, reason: path);
  }
}

void expectSubset(Object? actual, Object? expected, [String path = r'$']) {
  if (expected is Map<String, Object?>) {
    expect(actual, isA<Map<String, Object?>>(), reason: path);
    final object = actual! as Map<String, Object?>;
    for (final key in expected.keys) {
      expect(object.containsKey(key), isTrue, reason: '$path.$key is missing');
      expectSubset(object[key], expected[key], '$path.$key');
    }
  } else if (expected is List<Object?>) {
    expect(actual, isA<List<Object?>>(), reason: path);
    final values = actual! as List<Object?>;
    expect(values.length, expected.length, reason: path);
    for (var i = 0; i < expected.length; i++) {
      expectSubset(values[i], expected[i], '$path[$i]');
    }
  } else {
    expectExact(actual, expected, path);
  }
}

void expectMetrics(Map<String, Object?> actual, Map<String, Object?> expected) {
  for (final entry in expected.entries) {
    expect(actual.containsKey(entry.key), isTrue, reason: entry.key);
    final value = actual[entry.key];
    if (entry.value is num) {
      expect(value, isA<num>(), reason: entry.key);
      final number = value! as num;
      expect(number.isFinite, isTrue, reason: entry.key);
      expect(
        (number - (entry.value! as num)).abs(),
        lessThan(0.005),
        reason: entry.key,
      );
    } else {
      expectExact(value, entry.value, entry.key);
    }
  }
}
