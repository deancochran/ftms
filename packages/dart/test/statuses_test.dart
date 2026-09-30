import 'dart:typed_data';

import 'package:deancochran_ftms/deancochran_ftms.dart';
import 'package:test/test.dart';

import 'support/value_helpers.dart';

Uint8List _hex(String value) => Uint8List.fromList(
  List<int>.generate(
    value.length ~/ 2,
    (int i) => int.parse(value.substring(i * 2, i * 2 + 2), radix: 16),
  ),
);

void main() {
  final Map<String, Object?> corpus = fixture('statuses');
  for (final Object? raw in objects(corpus['machine'])) {
    final Map<String, Object?> c = object(raw);
    final String id = c['id']! as String;
    test('[statuses/$id]', () {
      final Map<String, Object?> d = object(c['decoded']);
      final Map<String, Object?>? p = d['parameter'] == null
          ? null
          : object(d['parameter']);
      final MachineStatus input = MachineStatus(
        d['opcode']! as int,
        action: d['action']! as int,
        parameter: p == null
            ? null
            : MachineStatusParameter(
                p['opcode']! as int,
                objects(p['operands']).cast<int>(),
              ),
      );
      if (c['encode'] == true) {
        expect(encodeMachineStatus(input), wire(c['bytes']));
      }
      expect(decodeMachineStatus(wire(c['bytes'])).toJson(), d);
    });
  }
  for (final Object? raw in objects(corpus['training'])) {
    final Map<String, Object?> c = object(raw);
    final String id = c['id']! as String;
    test('[statuses/$id]', () {
      final Map<String, Object?> d = object(c['decoded']);
      final TrainingStatus input = TrainingStatus(
        d['flags']! as int,
        d['code']! as int,
        _hex(d['textHex']! as String),
        textOffset: d['textOffset']! as int,
        textPresent: d['textPresent'] == 1,
        extendedString: d['extendedString'] == 1,
      );
      if (c['encode'] == true) {
        expect(encodeTrainingStatus(input), wire(c['bytes']));
      }
      expect(decodeTrainingStatus(wire(c['bytes'])).toJson(), d);
    });
  }
}
