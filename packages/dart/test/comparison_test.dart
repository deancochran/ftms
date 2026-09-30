import 'package:test/test.dart';

import 'support/conformance.dart';

void main() {
  test(
    'codec-v1 comparisons reject missing nulls, array prefixes and bools',
    () {
      expect(
        () => expectSubset(<String, Object?>{}, {'x': null}),
        throwsA(anything),
      );
      expect(() => expectSubset([1, 2], [1]), throwsA(anything));
      expect(() => expectExact(true, 1), throwsA(anything));
      expect(
        () => expectExact({'x': 1, 'extra': 2}, {'x': 1}),
        throwsA(anything),
      );
      expectSubset({'x': null, 'extra': 2}, {'x': null});
    },
  );
  test('codec-v1 metric tolerance is strict and rejects nonfinite values', () {
    expectMetrics({'x': 0.0049}, {'x': 0});
    expect(() => expectMetrics({'x': 0.005}, {'x': 0}), throwsA(anything));
    expect(() => expectMetrics({'x': double.nan}, {'x': 0}), throwsA(anything));
    expect(
      () => expectMetrics({'x': double.infinity}, {'x': 0}),
      throwsA(anything),
    );
  });
}
