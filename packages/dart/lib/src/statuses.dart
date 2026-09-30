import 'dart:convert';
import 'dart:typed_data';

/// Raw parameter associated with a machine-status opcode.
final class MachineStatusParameter {
  MachineStatusParameter(this.requestOpcode, List<int> operands)
    : operands = List.unmodifiable(operands);
  final int requestOpcode;
  final List<int> operands;
  Map<String, Object> toJson() => {
    'opcode': requestOpcode,
    'operands': operands,
  };
}

/// Machine-status value plus retained malformed-wire evidence.
final class MachineStatus {
  const MachineStatus(
    this.opcode, {
    this.action = 0,
    this.parameter,
    this.unknownOpcode = false,
    this.reservedValue = false,
    this.truncated = false,
    this.trailingBytes = false,
  });
  final int opcode, action;
  final MachineStatusParameter? parameter;
  final bool unknownOpcode, reservedValue, truncated, trailingBytes;
  Map<String, Object?> toJson() => {
    'opcode': opcode,
    'action': action,
    'parameter': parameter?.toJson(),
    'unknownOpcode': unknownOpcode ? 1 : 0,
    'reservedValue': reservedValue ? 1 : 0,
    'truncated': truncated ? 1 : 0,
    'trailingBytes': trailingBytes ? 1 : 0,
  };
}

/// Training-status value whose UTF-8 text bytes are owned and immutable.
final class TrainingStatus {
  /// Constructs text-present status with coherent flags and byte offset.
  factory TrainingStatus.fromText(
    int code,
    String text, {
    bool extended = false,
  }) => TrainingStatus(
    extended ? 3 : 1,
    code,
    Uint8List.fromList(utf8.encode(text)),
    textOffset: 2,
    textPresent: true,
    extendedString: extended,
  );

  TrainingStatus(
    this.flags,
    this.code,
    Uint8List text, {
    this.textOffset = 0,
    this.textPresent = false,
    this.extendedString = false,
    this.reservedFlags = 0,
    this.reservedValue = false,
    this.invalidFlags = false,
    this.invalidUtf8 = false,
    this.truncated = false,
    this.trailingBytes = false,
  }) : _text = Uint8List.fromList(text);
  final int flags, code, textOffset, reservedFlags;
  final bool textPresent,
      extendedString,
      reservedValue,
      invalidFlags,
      invalidUtf8,
      truncated,
      trailingBytes;
  final Uint8List _text;
  Uint8List get text => Uint8List.fromList(_text);
  int get textSize => _text.length;
  Map<String, Object> toJson() => {
    'flags': flags,
    'code': code,
    'textOffset': textOffset,
    'textSize': textSize,
    'textPresent': textPresent ? 1 : 0,
    'extendedString': extendedString ? 1 : 0,
    'reservedFlags': reservedFlags,
    'reservedValue': reservedValue ? 1 : 0,
    'invalidFlags': invalidFlags ? 1 : 0,
    'invalidUtf8': invalidUtf8 ? 1 : 0,
    'truncated': truncated ? 1 : 0,
    'trailingBytes': trailingBytes ? 1 : 0,
    'textHex': _text.map((x) => x.toRadixString(16).padLeft(2, '0')).join(),
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

int _length(int c) => switch (c) {
  1 || 3 || 4 || 255 => 1,
  2 || 9 || 20 => 2,
  13 => 4,
  15 => 5,
  16 || 18 => 7,
  17 => 11,
  5 || 6 || 7 || 8 || 10 || 11 || 12 || 14 || 19 || 21 => 3,
  _ => 0,
};
int _mapped(int c) => c >= 5 && c <= 9
    ? c - 3
    : (c >= 10 && c <= 19 || c == 21)
    ? c - 1
    : -1;

/// Decodes machine-status bytes without retaining the caller's buffer.
MachineStatus decodeMachineStatus(Uint8List bytes) {
  if (bytes.isEmpty) {
    return const MachineStatus(0, unknownOpcode: true, truncated: true);
  }
  final c = bytes[0];
  final n = _length(c);
  if (n == 0) return MachineStatus(c, unknownOpcode: true);
  if (bytes.length < n) return MachineStatus(c, truncated: true);
  final action = c == 2 || c == 20 ? bytes[1] : 0;
  final reserved =
      (c == 2 && (action < 1 || action > 2)) ||
      (c == 20 && (action < 1 || action > 4));
  List<int> a = switch (c) {
    5 => [_u16(bytes, 1)],
    6 || 7 || 8 => [_s16(bytes, 1)],
    9 => [bytes[1]],
    10 || 11 || 12 || 14 || 19 || 21 => [_u16(bytes, 1)],
    13 => [bytes[1] | bytes[2] << 8 | bytes[3] << 16],
    15 ||
    16 ||
    17 => List.generate((n - 1) ~/ 2, (i) => _u16(bytes, 1 + i * 2)),
    18 => [_s16(bytes, 1), _s16(bytes, 3), bytes[5], bytes[6]],
    _ => const [],
  };
  final mapped = _mapped(c);
  return MachineStatus(
    c,
    action: action,
    parameter: mapped >= 0 && c != 20
        ? MachineStatusParameter(mapped, a)
        : null,
    reservedValue: reserved,
    trailingBytes: bytes.length > n,
  );
}

/// Encodes only canonical machine statuses; diagnostics cannot be emitted.
Uint8List encodeMachineStatus(MachineStatus v) {
  final n = _length(v.opcode);
  if (n == 0 ||
      v.unknownOpcode ||
      v.reservedValue ||
      v.truncated ||
      v.trailingBytes ||
      (v.opcode != 2 && v.opcode != 20 && v.action != 0)) {
    throw ArgumentError('non-canonical machine status');
  }
  if ((v.opcode == 2 && (v.action < 1 || v.action > 2)) ||
      (v.opcode == 20 && (v.action < 1 || v.action > 4))) {
    throw RangeError('action');
  }
  final expected = _mapped(v.opcode);
  if ((expected < 0) != (v.parameter == null) ||
      (expected >= 0 && v.parameter!.requestOpcode != expected)) {
    throw ArgumentError('parameter mismatch');
  }
  final b = Uint8List(n);
  b[0] = v.opcode;
  if (v.opcode == 2 || v.opcode == 20) {
    b[1] = v.action;
    return b;
  }
  final a = v.parameter?.operands ?? const <int>[];
  final count = switch (v.opcode) {
    15 => 2,
    16 => 3,
    17 => 5,
    18 => 4,
    _ => expected >= 0 ? 1 : 0,
  };
  if (a.length != count) throw ArgumentError('operand count');
  if (v.opcode == 18) {
    if (a[0] < -32768 ||
        a[0] > 32767 ||
        a[1] < -32768 ||
        a[1] > 32767 ||
        a[2] < 0 ||
        a[2] > 255 ||
        a[3] < 0 ||
        a[3] > 255) {
      throw RangeError('operand');
    }
    _put16(b, 1, a[0]);
    _put16(b, 3, a[1]);
    b[5] = a[2];
    b[6] = a[3];
    return b;
  }
  for (var i = 0; i < a.length; i++) {
    final x = a[i];
    final signed = v.opcode >= 6 && v.opcode <= 8 || (v.opcode == 18 && i < 2);
    final byte = v.opcode == 9 || (v.opcode == 18 && i >= 2);
    if (v.opcode == 13) {
      if (x < 0 || x > 0xffffff) throw RangeError('operand');
      b[1] = x;
      b[2] = x >> 8;
      b[3] = x >> 16;
    } else if (byte) {
      if (x < 0 || x > 255) throw RangeError('operand');
      b[1 + i] = x;
    } else {
      if (x < (signed ? -32768 : 0) || x > (signed ? 32767 : 65535)) {
        throw RangeError('operand');
      }
      _put16(b, 1 + i * 2, x);
    }
  }
  return b;
}

bool _utf8(Uint8List b) {
  try {
    utf8.decode(b, allowMalformed: false);
    return true;
  } catch (_) {
    return false;
  }
}

/// Decodes training-status bytes and retains copied raw UTF-8 text evidence.
TrainingStatus decodeTrainingStatus(Uint8List bytes) {
  if (bytes.length < 2) {
    return TrainingStatus(
      bytes.isEmpty ? 0 : bytes[0],
      0,
      Uint8List(0),
      truncated: true,
    );
  }
  final flags = bytes[0], code = bytes[1];
  final has = flags & 1 != 0;
  final text = has ? Uint8List.fromList(bytes.sublist(2)) : Uint8List(0);
  final reserved = flags & 0xfc;
  return TrainingStatus(
    flags,
    code,
    text,
    textOffset: has ? 2 : 0,
    textPresent: has,
    extendedString: flags & 2 != 0,
    reservedFlags: reserved,
    reservedValue: code > 15,
    invalidFlags: flags & 2 != 0 && !has,
    invalidUtf8: has && !_utf8(text),
    trailingBytes: !has && bytes.length > 2,
  );
}

/// Encodes the [TrainingStatus.text] owned bytes; it never silently substitutes text.
Uint8List encodeTrainingStatus(TrainingStatus v) {
  if (v.textOffset != (v.textPresent ? 2 : 0)) {
    throw ArgumentError('textOffset contradicts text presence');
  }
  if (v.flags < 0 ||
      v.flags > 255 ||
      v.code < 0 ||
      v.code > 15 ||
      v.flags & 0xfc != 0 ||
      (v.flags & 2 != 0 && v.flags & 1 == 0) ||
      v.reservedFlags != 0 ||
      v.reservedValue ||
      v.invalidFlags ||
      v.invalidUtf8 ||
      v.truncated ||
      v.trailingBytes) {
    throw ArgumentError('non-canonical training status');
  }
  final raw = v.text;
  if (!_utf8(raw)) throw ArgumentError('invalid UTF-8 text');
  if (v.textPresent != (v.flags & 1 != 0) ||
      v.extendedString != (v.flags & 2 != 0)) {
    throw ArgumentError('text metadata mismatch');
  }
  if (v.flags & 1 == 0 && raw.isNotEmpty) {
    throw ArgumentError('text without text-present');
  }
  return Uint8List.fromList([v.flags, v.code, if (v.flags & 1 != 0) ...raw]);
}
