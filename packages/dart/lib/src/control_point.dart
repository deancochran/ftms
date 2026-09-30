import 'dart:typed_data';

enum ResistanceControlFormat { signed16Tenths, uint8Tenths }

/// Classifies malformed incoming Control Point evidence.
enum ControlErrorCode { length, kind, range }

/// An incoming Control Point payload failed structural validation.
final class ControlCodecException extends ArgumentError {
  ControlCodecException(
    this.code, [
    String message = 'invalid Control Point payload',
  ]) : super(message);
  final ControlErrorCode code;
}

/// Raw Control Point request; operands retain documented wire numerators.
final class ControlRequest {
  ControlRequest(this.opcode, List<int> operands)
    : operands = List.unmodifiable(operands) {
    if (opcode < 0 || opcode > 20) {
      throw RangeError.range(opcode, 0, 20, 'opcode');
    }
  }
  final int opcode;
  final List<int> operands;
  Map<String, Object> toJson() => {'opcode': opcode, 'operands': operands};
}

/// Raw Control Point response and retained diagnostic evidence.
final class ControlResponse {
  const ControlResponse(
    this.requestOpcode,
    this.resultCode, {
    this.parameter = 0,
    this.low = 0,
    this.high = 0,
    this.unknownRequest = false,
    this.unknownResult = false,
    this.unexpectedParameters = false,
  });
  final int requestOpcode, resultCode, parameter, low, high;
  final bool unknownRequest, unknownResult, unexpectedParameters;
  Map<String, Object> toJson() => {
    'requestOpcode': requestOpcode,
    'resultCode': resultCode,
    'parameter': parameter,
    'low': low,
    'high': high,
    'unknownRequest': unknownRequest ? 1 : 0,
    'unknownResult': unknownResult ? 1 : 0,
    'unexpectedParameters': unexpectedParameters ? 1 : 0,
  };
}

int _u16(Uint8List b, int i) => b[i] | b[i + 1] << 8;
int _s16(Uint8List b, int i) {
  final n = _u16(b, i);
  return n < 32768 ? n : n - 65536;
}

void _put16(Uint8List b, int i, int n) {
  b[i] = n & 255;
  b[i + 1] = n >> 8 & 255;
}

void _check(int n, int lo, int hi) {
  if (n < lo || n > hi) throw RangeError.range(n, lo, hi);
}

const _counts = [0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 2, 3, 5, 4, 1, 1, 1];
int _length(int op, ResistanceControlFormat f) => switch (op) {
  0 || 1 || 7 => 1,
  6 || 8 || 19 => 2,
  12 => 4,
  14 => 5,
  15 || 17 => 7,
  16 => 11,
  4 => f == ResistanceControlFormat.uint8Tenths ? 2 : 3,
  _ => 3,
};
({int lo, int hi}) _bounds(int op, int i, ResistanceControlFormat f) =>
    switch (op) {
      3 || 5 => (lo: -32768, hi: 32767),
      4 =>
        f == ResistanceControlFormat.uint8Tenths
            ? (lo: 0, hi: 255)
            : (lo: -32768, hi: 32767),
      6 || 8 || 19 => (lo: 0, hi: 255),
      12 => (lo: 0, hi: 0xffffff),
      17 => i < 2 ? (lo: -32768, hi: 32767) : (lo: 0, hi: 255),
      _ => (lo: 0, hi: 65535),
    };

/// Decodes a request; malformed input throws [ControlCodecException].
ControlRequest decodeControlRequest(
  Uint8List bytes, {
  ResistanceControlFormat resistanceFormat =
      ResistanceControlFormat.signed16Tenths,
}) {
  if (bytes.isEmpty) throw ControlCodecException(ControlErrorCode.length);
  final op = bytes[0];
  if (op > 20) throw ControlCodecException(ControlErrorCode.kind);
  if (bytes.length != _length(op, resistanceFormat)) {
    throw ControlCodecException(ControlErrorCode.length);
  }
  final a = <int>[];
  var at = 1;
  for (var i = 0; i < _counts[op]; i++) {
    final one =
        op == 6 ||
        op == 8 ||
        op == 19 ||
        (op == 4 && resistanceFormat == ResistanceControlFormat.uint8Tenths) ||
        (op == 17 && i >= 2);
    a.add(
      op == 12
          ? bytes[at] | bytes[at + 1] << 8 | bytes[at + 2] << 16
          : one
          ? bytes[at]
          : (op == 3 || op == 5 || op == 4 || (op == 17 && i < 2))
          ? _s16(bytes, at)
          : _u16(bytes, at),
    );
    at += op == 12
        ? 3
        : one
        ? 1
        : 2;
  }
  if ((op == 8 || op == 19) && (a[0] < 1 || a[0] > 2)) {
    throw ControlCodecException(ControlErrorCode.range);
  }
  return ControlRequest(op, a);
}

/// Encodes a canonical request; invalid values throw [RangeError] or [ArgumentError].
Uint8List encodeControlRequest(
  ControlRequest value, {
  ResistanceControlFormat resistanceFormat =
      ResistanceControlFormat.signed16Tenths,
}) {
  if (value.operands.length != _counts[value.opcode]) {
    throw ArgumentError('length');
  }
  if ((value.opcode == 8 || value.opcode == 19) &&
      (value.operands[0] < 1 || value.operands[0] > 2)) {
    throw RangeError('action');
  }
  final b = Uint8List(_length(value.opcode, resistanceFormat));
  b[0] = value.opcode;
  var at = 1;
  for (var i = 0; i < value.operands.length; i++) {
    final x = value.operands[i];
    final r = _bounds(value.opcode, i, resistanceFormat);
    _check(x, r.lo, r.hi);
    final one =
        value.opcode == 6 ||
        value.opcode == 8 ||
        value.opcode == 19 ||
        (value.opcode == 4 &&
            resistanceFormat == ResistanceControlFormat.uint8Tenths) ||
        (value.opcode == 17 && i >= 2);
    if (value.opcode == 12) {
      b[at++] = x;
      b[at++] = x >> 8;
      b[at++] = x >> 16;
    } else if (one) {
      b[at++] = x;
    } else {
      _put16(b, at, x);
      at += 2;
    }
  }
  return b;
}

/// Decodes a response, preserving unknown and trailing evidence diagnostics.
ControlResponse decodeControlResponse(Uint8List bytes) {
  if (bytes.length < 3) throw ControlCodecException(ControlErrorCode.length);
  if (bytes[0] != 0x80) throw ControlCodecException(ControlErrorCode.kind);
  final spin = bytes[1] == 19 && bytes[2] == 1;
  if (spin && bytes.length != 3 && bytes.length != 7) {
    throw ControlCodecException(ControlErrorCode.length);
  }
  return ControlResponse(
    bytes[1],
    bytes[2],
    parameter: spin && bytes.length == 7 ? 1 : 0,
    low: spin && bytes.length == 7 ? _u16(bytes, 3) : 0,
    high: spin && bytes.length == 7 ? _u16(bytes, 5) : 0,
    unknownRequest: bytes[1] > 20,
    unknownResult: bytes[2] < 1 || bytes[2] > 5,
    unexpectedParameters: !spin && bytes.length > 3,
  );
}

/// Encodes a canonical response; diagnostic-only values are rejected.
Uint8List encodeControlResponse(ControlResponse v) {
  _check(v.requestOpcode, 0, 255);
  _check(v.resultCode, 1, 5);
  _check(v.parameter, 0, 1);
  _check(v.low, 0, 65535);
  _check(v.high, 0, 65535);
  if (v.unknownResult ||
      v.unexpectedParameters ||
      v.unknownRequest != (v.requestOpcode > 20) ||
      (v.requestOpcode > 20 && v.resultCode != 2) ||
      (v.parameter == 1 && (v.requestOpcode != 19 || v.resultCode != 1)) ||
      (v.parameter == 0 && (v.low != 0 || v.high != 0))) {
    throw ArgumentError('non-canonical response');
  }
  final b = Uint8List(v.parameter == 1 ? 7 : 3);
  b[0] = 0x80;
  b[1] = v.requestOpcode;
  b[2] = v.resultCode;
  if (v.parameter == 1) {
    _put16(b, 3, v.low);
    _put16(b, 5, v.high);
  }
  return b;
}
