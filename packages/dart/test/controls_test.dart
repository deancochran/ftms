import 'package:deancochran_ftms/deancochran_ftms.dart';
import 'package:test/test.dart';

import 'support/value_helpers.dart';

void main() {
  final Map<String, Object?> corpus = fixture('controls');
  for (final Object? raw in [
    ...objects(corpus['requests']),
    ...objects(corpus['invalid']),
  ]) {
    final Map<String, Object?> c = object(raw);
    final String id = c['id']! as String;
    test('[controls/$id]', () {
      final ResistanceControlFormat format = c['format'] == 'uint8Tenths'
          ? ResistanceControlFormat.uint8Tenths
          : ResistanceControlFormat.signed16Tenths;
      if (c.containsKey('error')) {
        final ControlErrorCode expected = ControlErrorCode.values.byName(
          c['error']! as String,
        );
        final Object Function() decode = c['operation'] == 'response'
            ? () => decodeControlResponse(wire(c['bytes']))
            : () => decodeControlRequest(
                wire(c['bytes']),
                resistanceFormat: format,
              );
        expect(
          decode,
          throwsA(
            isA<ControlCodecException>().having(
              (ControlCodecException e) => e.code,
              'code',
              expected,
            ),
          ),
        );
      } else {
        final Map<String, Object?> decoded = object(c['decoded']);
        final ControlRequest input = ControlRequest(
          decoded['opcode']! as int,
          objects(decoded['operands']).cast<int>(),
        );
        expect(
          encodeControlRequest(input, resistanceFormat: format),
          wire(c['bytes']),
        );
        expect(
          decodeControlRequest(
            wire(c['bytes']),
            resistanceFormat: format,
          ).toJson(),
          decoded,
        );
      }
    });
  }
  for (final Object? raw in objects(corpus['responses'])) {
    final Map<String, Object?> c = object(raw);
    final String id = c['id']! as String;
    test('[controls/$id]', () {
      final Map<String, Object?> decoded = object(c['decoded']);
      final ControlResponse input = ControlResponse(
        decoded['requestOpcode']! as int,
        decoded['resultCode']! as int,
        parameter: decoded['parameter']! as int,
        low: decoded['low']! as int,
        high: decoded['high']! as int,
        unknownRequest: decoded['unknownRequest'] == 1,
        unknownResult: decoded['unknownResult'] == 1,
        unexpectedParameters: decoded['unexpectedParameters'] == 1,
      );
      if (c['encode'] != false) {
        expect(encodeControlResponse(input), wire(c['bytes']));
      }
      expect(decodeControlResponse(wire(c['bytes'])).toJson(), decoded);
    });
  }
}
