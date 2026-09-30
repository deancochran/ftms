import 'dart:typed_data';

/// Supported FTMS range characteristic family.
enum RangeKind { speed, inclination, resistance, heartRate, power }

enum RangeUnit { kilometresPerHour, percent, level, beatsPerMinute, watts }

enum ResistanceRangeFormat { uint8Whole, signed16Tenths }

enum RangeProfile {
  uint16Hundredths,
  signed16Tenths,
  uint8Whole,
  uint8Bpm,
  signed16Watts,
}

enum RangeStatus { valid, length, range }

/// Two unsigned 32-bit FTMS feature words, represented web-safely as Dart ints.
final class Features {
  const Features(this.machine, this.target)
    : assert(machine >= 0 && machine <= 0xffffffff),
      assert(target >= 0 && target <= 0xffffffff);
  final int machine;
  final int target;
  Map<String, Object> toJson() => {'machine': machine, 'target': target};
}

/// Raw supported-range numerators and fixed wire metadata.
final class SupportedRange {
  const SupportedRange(
    this.kind,
    this.minimum,
    this.maximum,
    this.increment,
    this.scaleDivisor,
    this.unit,
  );
  final RangeKind kind;
  final int minimum, maximum, increment, scaleDivisor;
  final RangeUnit unit;
  Map<String, Object> toJson() => {
    'kind': kind.name,
    'minimum': minimum,
    'maximum': maximum,
    'increment': increment,
    'scaleDivisor': scaleDivisor,
    'unit': unit.index,
  };
}

/// One structural range-layout candidate; it does not select a profile.
final class RangeCandidate {
  const RangeCandidate(
    this.profile,
    this.expectedLength,
    this.status,
    this.value,
  );
  final RangeProfile profile;
  final int expectedLength;
  final RangeStatus status;
  final SupportedRange? value;
  Map<String, Object?> toJson() => {
    'profile': profile.name,
    'expectedLength': expectedLength,
    'status': status.name,
    'value': value?.toJson(),
  };
}

/// Selected range result and all bounded candidate layouts.
final class RangeInspection {
  RangeInspection(
    this.selectedProfile,
    this.actualLength,
    this.expectedLength,
    this.status,
    this.value,
    List<RangeCandidate> candidates,
  ) : candidates = List.unmodifiable(candidates);
  final RangeProfile selectedProfile;
  final int actualLength, expectedLength;
  final RangeStatus status;
  final SupportedRange? value;
  final List<RangeCandidate> candidates;
  Map<String, Object?> toJson() => {
    'selectedProfile': selectedProfile.name,
    'actualLength': actualLength,
    'expectedLength': expectedLength,
    'status': status.name,
    'value': value?.toJson(),
    'candidates': candidates.map((x) => x.toJson()).toList(),
  };
}

int _u16(Uint8List b, int i) => b[i] | (b[i + 1] << 8);
int _s16(Uint8List b, int i) {
  final n = _u16(b, i);
  return n < 32768 ? n : n - 65536;
}

void _check(int n, int low, int high, String name) {
  if (n < low || n > high) throw RangeError.range(n, low, high, name);
}

void _put16(Uint8List b, int i, int n) {
  b[i] = n & 255;
  b[i + 1] = (n >> 8) & 255;
}

Features decodeFeatures(Uint8List bytes) {
  if (bytes.length != 8) {
    throw ArgumentError.value(bytes.length, 'bytes.length', 'must be 8');
  }
  return Features(
    _u16(bytes, 0) | (_u16(bytes, 2) << 16),
    _u16(bytes, 4) | (_u16(bytes, 6) << 16),
  );
}

Uint8List encodeFeatures(Features value) {
  _check(value.machine, 0, 0xffffffff, 'machine');
  _check(value.target, 0, 0xffffffff, 'target');
  final b = Uint8List(8);
  _put16(b, 0, value.machine);
  _put16(b, 2, value.machine >> 16);
  _put16(b, 4, value.target);
  _put16(b, 6, value.target >> 16);
  return b;
}

RangeProfile _profile(RangeKind k, ResistanceRangeFormat f) => switch (k) {
  RangeKind.speed => RangeProfile.uint16Hundredths,
  RangeKind.inclination => RangeProfile.signed16Tenths,
  RangeKind.resistance =>
    f == ResistanceRangeFormat.signed16Tenths
        ? RangeProfile.signed16Tenths
        : RangeProfile.uint8Whole,
  RangeKind.heartRate => RangeProfile.uint8Bpm,
  RangeKind.power => RangeProfile.signed16Watts,
};
({int divisor, RangeUnit unit}) _metadata(
  RangeKind k,
  ResistanceRangeFormat f,
) => switch (k) {
  RangeKind.speed => (divisor: 100, unit: RangeUnit.kilometresPerHour),
  RangeKind.inclination => (divisor: 10, unit: RangeUnit.percent),
  RangeKind.resistance => (
    divisor: f == ResistanceRangeFormat.signed16Tenths ? 10 : 1,
    unit: RangeUnit.level,
  ),
  RangeKind.heartRate => (divisor: 1, unit: RangeUnit.beatsPerMinute),
  RangeKind.power => (divisor: 1, unit: RangeUnit.watts),
};
int _length(RangeProfile p) =>
    (p == RangeProfile.uint8Whole || p == RangeProfile.uint8Bpm) ? 3 : 6;
void _format(RangeKind k, ResistanceRangeFormat f) {
  if (f == ResistanceRangeFormat.signed16Tenths && k != RangeKind.resistance) {
    throw ArgumentError.value(f, 'format', 'only applies to resistance');
  }
}

SupportedRange decodeSupportedRange(
  RangeKind kind,
  Uint8List bytes, {
  ResistanceRangeFormat resistanceFormat = ResistanceRangeFormat.uint8Whole,
}) {
  _format(kind, resistanceFormat);
  final p = _profile(kind, resistanceFormat);
  final n = _length(p);
  if (bytes.length != n) {
    throw ArgumentError.value(bytes.length, 'bytes.length', 'must be $n');
  }
  final signed =
      p == RangeProfile.signed16Tenths || p == RangeProfile.signed16Watts;
  final min = n == 3 ? bytes[0] : (signed ? _s16(bytes, 0) : _u16(bytes, 0));
  final max = n == 3 ? bytes[1] : (signed ? _s16(bytes, 2) : _u16(bytes, 2));
  final inc = n == 3 ? bytes[2] : _u16(bytes, 4);
  if (min > max || inc == 0) {
    throw RangeError('minimum, maximum, or increment is invalid');
  }
  final m = _metadata(kind, resistanceFormat);
  return SupportedRange(kind, min, max, inc, m.divisor, m.unit);
}

Uint8List encodeSupportedRange(
  SupportedRange value, {
  ResistanceRangeFormat resistanceFormat = ResistanceRangeFormat.uint8Whole,
}) {
  _format(value.kind, resistanceFormat);
  final p = _profile(value.kind, resistanceFormat);
  final n = _length(p);
  final m = _metadata(value.kind, resistanceFormat);
  if (value.minimum > value.maximum ||
      value.increment <= 0 ||
      value.scaleDivisor != m.divisor ||
      value.unit != m.unit) {
    throw ArgumentError('invalid range metadata or bounds');
  }
  final signed =
      p == RangeProfile.signed16Tenths || p == RangeProfile.signed16Watts;
  final max = n == 3 ? 255 : 65535;
  _check(value.increment, 1, max, 'increment');
  _check(value.minimum, signed ? -32768 : 0, signed ? 32767 : max, 'minimum');
  _check(value.maximum, signed ? -32768 : 0, signed ? 32767 : max, 'maximum');
  final b = Uint8List(n);
  if (n == 3) {
    b[0] = value.minimum;
    b[1] = value.maximum;
    b[2] = value.increment;
  } else {
    _put16(b, 0, value.minimum);
    _put16(b, 2, value.maximum);
    _put16(b, 4, value.increment);
  }
  return b;
}

RangeInspection inspectSupportedRange(
  RangeKind kind,
  Uint8List bytes, {
  ResistanceRangeFormat resistanceFormat = ResistanceRangeFormat.uint8Whole,
}) {
  _format(kind, resistanceFormat);
  RangeCandidate candidate(ResistanceRangeFormat f) {
    final p = _profile(kind, f);
    try {
      return RangeCandidate(
        p,
        _length(p),
        RangeStatus.valid,
        decodeSupportedRange(kind, bytes, resistanceFormat: f),
      );
    } on RangeError {
      return RangeCandidate(p, _length(p), RangeStatus.range, null);
    } on ArgumentError {
      return RangeCandidate(p, _length(p), RangeStatus.length, null);
    }
  }

  final candidates = kind == RangeKind.resistance
      ? [
          candidate(ResistanceRangeFormat.uint8Whole),
          candidate(ResistanceRangeFormat.signed16Tenths),
        ]
      : [candidate(resistanceFormat)];
  final selected = candidates.firstWhere(
    (x) => x.profile == _profile(kind, resistanceFormat),
  );
  return RangeInspection(
    selected.profile,
    bytes.length,
    selected.expectedLength,
    selected.status,
    selected.value,
    candidates,
  );
}
