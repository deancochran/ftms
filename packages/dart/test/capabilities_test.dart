import 'dart:convert';
import 'dart:typed_data';

import 'package:deancochran_ftms/deancochran_ftms.dart';
import 'package:test/test.dart';

import 'support/capability_helpers.dart';
import 'support/corpus.dart';

final _ids = <String>{
  'all-static-prerequisites',
  'multiple-measurement-families',
  'measurement-missing-notify',
  'duplicate-feature-no-first-win',
  'wrong-service-scope-no-derived-support',
  'absent-service-with-observations',
  'partial-empty-does-not-prove-absence',
  'resistance-reversed-range',
  'speed-range-security-required',
  'base-controls-only-with-zero-targets',
  'zero-features-telemetry',
  'mandatory-feature-absent',
  'discovery-not-attempted',
  'discovery-failed',
  'scope-ambiguous',
  'service-confirmed-absent',
  'absent-with-partial-discovery',
  'partial-with-all-observed-prerequisites',
  'new-generation-no-cache',
  'treadmill-data',
  'cross-trainer-data',
  'step-climber-data',
  'stair-climber-data',
  'rower-data',
  'indoor-bike-data',
  'unknown-uuid-lookalike',
  'unknown-feature-bits-retained',
  'measurement-support-not-control',
  'feature-unread-base-procedures-independent',
  'feature-security-failure',
  'feature-malformed',
  'feature-without-read',
  'control-point-missing-indicate',
  'partial-does-not-hide-contradiction',
  'control-point-extra-properties',
  'status-without-notify',
  'machine-status-absent',
  'control-point-absent-with-targets',
  'speed-range-unread',
  'inclination-range-malformed',
  'resistance-read-failed',
  'power-range-absent-not-heart-rate',
  'heart-rate-without-read-not-power',
  'ranges-do-not-grant-support',
  'wheel-no-range-required',
  'duplicate-control-point',
  'duplicate-power-range',
  'optional-training-status-invalid',
  'optional-training-status-valid',
  'c7-true-true-requires-indicate',
  'c7-true-true-indicate-accepted',
  'c7-known-false-excludes-indicate',
  'c7-unknown-does-not-reject-indicate',
  'c7-true-unknown-insufficient',
  'c7-false-unknown-excludes-indicate',
  'c7-unknown-true-insufficient-missing-read',
  'c7-true-false-excludes-indicate',
  'c7-false-true-excludes-indicate',
  'c7-unknown-false-excludes-indicate',
  'c7-unknown-unknown-read-insufficient',
  'c7-unknown-read-write-invalid-and-insufficient',
  'c7-unknown-read-notify-invalid-and-insufficient',
  'c7-omitted-evidence-is-unknown',
};

void main() {
  final corpus =
      jsonDecode(
            readCorpus('../../shared/conformance/capabilities/v1/vectors.json'),
          )
          as Map<String, Object?>;
  final inputs = corpus['snapshots'] as Map<String, Object?>,
      reports = corpus['reports'] as Map<String, Object?>;
  final cases = corpus['cases'] as List<Object?>;
  test('capability corpus has all 63 explicit case IDs', () {
    expect(cases, hasLength(63));
    expect(cases.map((x) => (x as Map<String, Object?>)['id']).toSet(), _ids);
  });
  for (final raw in cases) {
    final c = raw as Map<String, Object?>;
    test('[capabilities/${c['id'] as String}]', () {
      final input =
          expand(inputs, c['input'] as Map<String, Object?>)
              as Map<String, Object?>;
      final expected = expand(reports, c['expected'] as Map<String, Object?>);
      expect(
        evaluateCapabilities(snapshotFromJson(input)).toJson(),
        expected,
        reason: '[capabilities/${c['id'] as String}]',
      );
    });
  }
  test('input models are immutable and reject invalid caller evidence', () {
    final bytes = Uint8List.fromList([0]);
    final c = CapabilityCharacteristic(
      uuid: '00002acc00001000800000805f9b34fb',
      properties: 2,
      readState: CapabilityReadState.success,
      bytes: bytes,
    );
    bytes[0] = 99;
    expect(c.bytes.single, 0);
    expect(
      () => CapabilityCharacteristic(
        uuid: '00002acc000010008000805f9b34fb',
        properties: 2,
        readState: CapabilityReadState.success,
      ),
      throwsArgumentError,
    );
    expect(
      () => CapabilityCharacteristic(
        uuid: '00002acc00001000800000805f9b34fb',
        properties: 2,
        readState: CapabilityReadState.success,
        reason: CapabilityReadReason.timeout,
      ),
      throwsArgumentError,
    );
  });
  test('zero words and reserved feature bits remain distinct facts', () {
    final base = {
      'discovery': 2,
      'scope': 1,
      'generation': 1,
      'characteristics': [
        {
          'uuid': '00002acc00001000800000805f9b34fb',
          'properties': 2,
          'readState': 1,
          'reason': 0,
          'bytes': '0000000000000000',
        },
      ],
    };
    expect(evaluateCapabilities(snapshotFromJson(base)).feature.toJson(), [
      2,
      1,
      0,
      0,
      0,
      0,
      0,
    ]);
    (base['characteristics'] as List<Object?>)
            .cast<Map<String, Object?>>()
            .single['bytes'] =
        '00000080ffff0180';
    expect(evaluateCapabilities(snapshotFromJson(base)).feature.toJson(), [
      2,
      1,
      0,
      2147483648,
      2147614719,
      2147483648,
      2147483648,
    ]);
  });
  test(
    'resistance format is explicit rather than inferred from byte length',
    () {
      final snapshot = snapshotFromJson({
        'discovery': 2,
        'scope': 1,
        'generation': 1,
        'characteristics': [
          {
            'uuid': '00002ad600001000800000805f9b34fb',
            'properties': 2,
            'readState': 1,
            'reason': 0,
            'bytes': 'f6ff14000500',
          },
        ],
      });
      expect(evaluateCapabilities(snapshot).ranges[2].decode.index, 2);
      expect(
        evaluateCapabilities(
          snapshot,
          resistanceRangeFormat: CapabilityResistanceRangeFormat.signed16Tenths,
        ).ranges[2].toJson(),
        [
          2,
          1,
          0,
          [2, -10, 20, 5, 10, 2],
        ],
      );
    },
  );
  test(
    'template expansion rejects malformed edits instead of reducing coverage',
    () {
      expect(
        () => expand(inputs, {'template': 'missing', 'edits': []}),
        throwsFormatException,
      );
      expect(
        () => expand(inputs, {
          'template': 'full',
          'edits': [
            {
              'path': ['absent'],
              'value': 1,
            },
          ],
        }),
        throwsFormatException,
      );
      expect(
        () => expand(inputs, {
          'template': 'full',
          'edits': [
            {
              'path': ['characteristics'],
              'op': 'append',
            },
          ],
        }),
        throwsFormatException,
      );
    },
  );
}
