import 'dart:typed_data';

/// The six FTMS machine-data characteristic layouts.
enum MeasurementKind {
  treadmill,
  crossTrainer,
  stepClimber,
  stairClimber,
  rower,
  indoorBike,
}

/// The explicitly selected resistance layout; this is never inferred from bytes.
enum MeasurementResistanceFormat { uint8Whole, signed16Tenths }

/// The explicitly selected treadmill pace layout; this is never inferred from bytes.
enum MeasurementTreadmillPaceFormat { uint16, uint8Legacy }

/// Caller-selected wire layouts. Selections are independent and never inferred.
final class MeasurementFormatOptions {
  final MeasurementResistanceFormat resistance;
  final MeasurementTreadmillPaceFormat treadmillPace;
  const MeasurementFormatOptions({
    this.resistance = MeasurementResistanceFormat.uint8Whole,
    this.treadmillPace = MeasurementTreadmillPaceFormat.uint16,
  });

  @override
  bool operator ==(Object other) =>
      other is MeasurementFormatOptions &&
      other.resistance == resistance &&
      other.treadmillPace == treadmillPace;
  @override
  int get hashCode => Object.hash(resistance, treadmillPace);
}

/// Stable indexes of the 30 raw slots defined by measurements/v1.
/// Indexes into [MeasurementRaw.values]; each value remains in its raw wire unit.
enum MeasurementField {
  speed,
  averageSpeed,
  distance,
  inclination,
  rampAngle,
  positiveElevation,
  negativeElevation,
  instantaneousPace,
  averagePace,
  energy,
  energyPerHour,
  energyPerMinute,
  heartRate,
  met,
  elapsed,
  remaining,
  force,
  power,
  stepRate,
  averageStepRate,
  strideCount,
  resistance,
  averagePower,
  floorCount,
  stepCount,
  strokeRate,
  strokeCount,
  averageStrokeRate,
  cadence,
  averageCadence,
}

/// Stable categories reported by [MeasurementCodecException].
enum MeasurementCodecErrorCode { length, kind, range }

/// Thrown for short flag words, invalid typed input, or non-encodable raw evidence.
final class MeasurementCodecException implements Exception {
  final MeasurementCodecErrorCode code;
  final String message;
  const MeasurementCodecException(this.code, this.message);
  @override
  String toString() => 'MeasurementCodecException($code): $message';
}

/// Immutable raw measurement evidence. Values always contain all 30 wire slots.
final class MeasurementRaw {
  final MeasurementKind kind;
  final int flags;
  final int present;
  final int unavailable;
  final List<int> values;
  final bool moreData;
  final bool backward;
  final bool truncated;
  final bool trailingBytes;
  final bool reservedFlags;
  final int bytesRead;

  MeasurementRaw({
    required this.kind,
    required this.flags,
    required this.present,
    required this.unavailable,
    required List<int> values,
    this.moreData = false,
    this.backward = false,
    this.truncated = false,
    this.trailingBytes = false,
    this.reservedFlags = false,
    this.bytesRead = 0,
  }) : values = List<int>.unmodifiable(values) {
    if (values.length != MeasurementField.values.length ||
        flags < 0 ||
        flags > (kind == MeasurementKind.crossTrainer ? 0xffffff : 0xffff) ||
        present < 0 ||
        present > 0x3fffffff ||
        unavailable < 0 ||
        unavailable > 0x3fffffff ||
        unavailable & ~present != 0 ||
        bytesRead < 0) {
      throw const MeasurementCodecException(
        MeasurementCodecErrorCode.range,
        'invalid raw measurement',
      );
    }
  }

  int valueAt(MeasurementField field) => values[field.index];

  /// Exact corpus-facing raw representation, including absent slots and diagnostics.
  Map<String, Object> toJson() => <String, Object>{
    'kind': kind.index,
    'flags': flags,
    'present': present,
    'unavailable': unavailable,
    'values': values,
    'moreData': moreData ? 1 : 0,
    'backward': backward ? 1 : 0,
    'truncated': truncated ? 1 : 0,
    'trailingBytes': trailingBytes ? 1 : 0,
    'reservedFlags': reservedFlags ? 1 : 0,
    'bytesRead': bytesRead,
  };
}

class _MeasurementFieldLayout {
  final int bit, width, index;
  final bool signed, unavailable;
  const _MeasurementFieldLayout(
    this.bit,
    this.width,
    this.index,
    this.signed,
    this.unavailable,
  );
  _MeasurementFieldLayout withFormat(
    MeasurementKind kind,
    MeasurementFormatOptions options,
  ) {
    if (index == MeasurementField.resistance.index &&
        (kind == MeasurementKind.crossTrainer ||
            kind == MeasurementKind.rower ||
            kind == MeasurementKind.indoorBike) &&
        options.resistance == MeasurementResistanceFormat.signed16Tenths) {
      return _MeasurementFieldLayout(bit, 2, index, true, unavailable);
    }
    if (kind == MeasurementKind.treadmill &&
        (index == MeasurementField.instantaneousPace.index ||
            index == MeasurementField.averagePace.index) &&
        options.treadmillPace == MeasurementTreadmillPaceFormat.uint8Legacy) {
      return _MeasurementFieldLayout(bit, 1, index, signed, unavailable);
    }
    return this;
  }
}

class _MeasurementLayout {
  final int flagBytes, validFlags;
  final List<_MeasurementFieldLayout> fields;
  const _MeasurementLayout(this.flagBytes, this.validFlags, this.fields);
}

const _layouts = <_MeasurementLayout>[
  _MeasurementLayout(2, 0x1fff, [
    _MeasurementFieldLayout(0, 2, 0, false, false),
    _MeasurementFieldLayout(1, 2, 1, false, false),
    _MeasurementFieldLayout(2, 3, 2, false, false),
    _MeasurementFieldLayout(3, 2, 3, true, true),
    _MeasurementFieldLayout(3, 2, 4, true, true),
    _MeasurementFieldLayout(4, 2, 5, false, false),
    _MeasurementFieldLayout(4, 2, 6, false, false),
    _MeasurementFieldLayout(5, 2, 7, false, false),
    _MeasurementFieldLayout(6, 2, 8, false, false),
    _MeasurementFieldLayout(7, 2, 9, false, true),
    _MeasurementFieldLayout(7, 2, 10, false, true),
    _MeasurementFieldLayout(7, 1, 11, false, true),
    _MeasurementFieldLayout(8, 1, 12, false, false),
    _MeasurementFieldLayout(9, 1, 13, false, false),
    _MeasurementFieldLayout(10, 2, 14, false, false),
    _MeasurementFieldLayout(11, 2, 15, false, false),
    _MeasurementFieldLayout(12, 2, 16, true, true),
    _MeasurementFieldLayout(12, 2, 17, true, true),
  ]),
  _MeasurementLayout(3, 0xffff, [
    _MeasurementFieldLayout(0, 2, 0, false, false),
    _MeasurementFieldLayout(1, 2, 1, false, false),
    _MeasurementFieldLayout(2, 3, 2, false, false),
    _MeasurementFieldLayout(3, 2, 18, false, true),
    _MeasurementFieldLayout(3, 2, 19, false, true),
    _MeasurementFieldLayout(4, 2, 20, false, false),
    _MeasurementFieldLayout(5, 2, 5, false, false),
    _MeasurementFieldLayout(5, 2, 6, false, false),
    _MeasurementFieldLayout(6, 2, 3, true, true),
    _MeasurementFieldLayout(6, 2, 4, true, true),
    _MeasurementFieldLayout(7, 1, 21, false, false),
    _MeasurementFieldLayout(8, 2, 17, true, false),
    _MeasurementFieldLayout(9, 2, 22, true, false),
    _MeasurementFieldLayout(10, 2, 9, false, true),
    _MeasurementFieldLayout(10, 2, 10, false, true),
    _MeasurementFieldLayout(10, 1, 11, false, true),
    _MeasurementFieldLayout(11, 1, 12, false, false),
    _MeasurementFieldLayout(12, 1, 13, false, false),
    _MeasurementFieldLayout(13, 2, 14, false, false),
    _MeasurementFieldLayout(14, 2, 15, false, false),
  ]),
  _MeasurementLayout(2, 0x01ff, [
    _MeasurementFieldLayout(0, 2, 23, false, false),
    _MeasurementFieldLayout(0, 2, 24, false, false),
    _MeasurementFieldLayout(1, 2, 18, false, false),
    _MeasurementFieldLayout(2, 2, 19, false, false),
    _MeasurementFieldLayout(3, 2, 5, false, false),
    _MeasurementFieldLayout(4, 2, 9, false, true),
    _MeasurementFieldLayout(4, 2, 10, false, true),
    _MeasurementFieldLayout(4, 1, 11, false, true),
    _MeasurementFieldLayout(5, 1, 12, false, false),
    _MeasurementFieldLayout(6, 1, 13, false, false),
    _MeasurementFieldLayout(7, 2, 14, false, false),
    _MeasurementFieldLayout(8, 2, 15, false, false),
  ]),
  _MeasurementLayout(2, 0x03ff, [
    _MeasurementFieldLayout(0, 2, 23, false, false),
    _MeasurementFieldLayout(1, 2, 18, false, false),
    _MeasurementFieldLayout(2, 2, 19, false, false),
    _MeasurementFieldLayout(3, 2, 5, false, false),
    _MeasurementFieldLayout(4, 2, 20, false, false),
    _MeasurementFieldLayout(5, 2, 9, false, true),
    _MeasurementFieldLayout(5, 2, 10, false, true),
    _MeasurementFieldLayout(5, 1, 11, false, true),
    _MeasurementFieldLayout(6, 1, 12, false, false),
    _MeasurementFieldLayout(7, 1, 13, false, false),
    _MeasurementFieldLayout(8, 2, 14, false, false),
    _MeasurementFieldLayout(9, 2, 15, false, false),
  ]),
  _MeasurementLayout(2, 0x1fff, [
    _MeasurementFieldLayout(0, 1, 25, false, false),
    _MeasurementFieldLayout(0, 2, 26, false, false),
    _MeasurementFieldLayout(1, 1, 27, false, false),
    _MeasurementFieldLayout(2, 3, 2, false, false),
    _MeasurementFieldLayout(3, 2, 7, false, false),
    _MeasurementFieldLayout(4, 2, 8, false, false),
    _MeasurementFieldLayout(5, 2, 17, true, false),
    _MeasurementFieldLayout(6, 2, 22, true, false),
    _MeasurementFieldLayout(7, 1, 21, false, false),
    _MeasurementFieldLayout(8, 2, 9, false, true),
    _MeasurementFieldLayout(8, 2, 10, false, true),
    _MeasurementFieldLayout(8, 1, 11, false, true),
    _MeasurementFieldLayout(9, 1, 12, false, false),
    _MeasurementFieldLayout(10, 1, 13, false, false),
    _MeasurementFieldLayout(11, 2, 14, false, false),
    _MeasurementFieldLayout(12, 2, 15, false, false),
  ]),
  _MeasurementLayout(2, 0x1fff, [
    _MeasurementFieldLayout(0, 2, 0, false, false),
    _MeasurementFieldLayout(1, 2, 1, false, false),
    _MeasurementFieldLayout(2, 2, 28, false, false),
    _MeasurementFieldLayout(3, 2, 29, false, false),
    _MeasurementFieldLayout(4, 3, 2, false, false),
    _MeasurementFieldLayout(5, 1, 21, false, false),
    _MeasurementFieldLayout(6, 2, 17, true, false),
    _MeasurementFieldLayout(7, 2, 22, true, false),
    _MeasurementFieldLayout(8, 2, 9, false, true),
    _MeasurementFieldLayout(8, 2, 10, false, true),
    _MeasurementFieldLayout(8, 1, 11, false, true),
    _MeasurementFieldLayout(9, 1, 12, false, false),
    _MeasurementFieldLayout(10, 1, 13, false, false),
    _MeasurementFieldLayout(11, 2, 14, false, false),
    _MeasurementFieldLayout(12, 2, 15, false, false),
  ]),
];

bool _selected(int flags, int bit) =>
    bit == 0 ? flags & 1 == 0 : flags & (1 << bit) != 0;
int _read(Uint8List bytes, int offset, int width) {
  var value = 0;
  for (var i = 0; i < width; i++) {
    value |= bytes[offset + i] << (i * 8);
  }
  return value;
}

int _sentinel(_MeasurementFieldLayout field) => field.signed
    ? 0x7fff
    : field.width == 1
    ? 0xff
    : 0xffff;

/// Decodes caller-owned FTMS bytes without retaining [bytes].
///
/// Values retain their integer wire units. A short flag word throws a length
/// error; a later incomplete selected field is returned as truncated evidence.
MeasurementRaw decodeMeasurement(
  MeasurementKind kind,
  Uint8List bytes, {
  MeasurementFormatOptions options = const MeasurementFormatOptions(),
}) {
  final layout = _layouts[kind.index];
  if (bytes.length < layout.flagBytes) {
    throw const MeasurementCodecException(
      MeasurementCodecErrorCode.length,
      'measurement flags truncated',
    );
  }
  final flags = _read(bytes, 0, layout.flagBytes);
  final values = List<int>.filled(MeasurementField.values.length, 0);
  var present = 0, unavailable = 0, offset = layout.flagBytes;
  for (final original in layout.fields) {
    final field = original.withFormat(kind, options);
    if (!_selected(flags, field.bit)) {
      continue;
    }
    if (offset + field.width > bytes.length) {
      return MeasurementRaw(
        kind: kind,
        flags: flags,
        present: present,
        unavailable: unavailable,
        values: values,
        moreData: flags & 1 != 0,
        backward: kind == MeasurementKind.crossTrainer && flags & 0x8000 != 0,
        truncated: true,
        reservedFlags: flags & ~layout.validFlags != 0,
        bytesRead: offset,
      );
    }
    final raw = _read(bytes, offset, field.width);
    offset += field.width;
    present |= 1 << field.index;
    if (field.unavailable && raw == _sentinel(field)) {
      unavailable |= 1 << field.index;
    } else {
      values[field.index] = field.signed && raw >= (1 << (field.width * 8 - 1))
          ? raw - (1 << (field.width * 8))
          : raw;
    }
  }
  return MeasurementRaw(
    kind: kind,
    flags: flags,
    present: present,
    unavailable: unavailable,
    values: values,
    moreData: flags & 1 != 0,
    backward: kind == MeasurementKind.crossTrainer && flags & 0x8000 != 0,
    trailingBytes: offset < bytes.length,
    reservedFlags: flags & ~layout.validFlags != 0,
    bytesRead: offset,
  );
}

/// Encodes complete, non-diagnostic raw evidence into a new [Uint8List].
///
/// Throws a range error when masks, sentinels, RFU flags, or raw wire bounds do
/// not describe one complete selected layout.
/// Absent/unavailable slots must be zero. [MeasurementRaw.bytesRead] may be zero
/// for a newly constructed value, otherwise it must match the encoded length.
Uint8List encodeMeasurement(
  MeasurementRaw measurement, {
  MeasurementFormatOptions options = const MeasurementFormatOptions(),
}) {
  final layout = _layouts[measurement.kind.index];
  if (measurement.truncated ||
      measurement.trailingBytes ||
      measurement.reservedFlags ||
      measurement.moreData != (measurement.flags & 1 != 0) ||
      measurement.backward !=
          (measurement.kind == MeasurementKind.crossTrainer &&
              measurement.flags & 0x8000 != 0) ||
      measurement.flags & ~layout.validFlags != 0 ||
      measurement.unavailable & ~measurement.present != 0) {
    throw const MeasurementCodecException(
      MeasurementCodecErrorCode.range,
      'diagnostic or reserved measurement cannot encode',
    );
  }
  var required = 0, length = layout.flagBytes;
  for (final original in layout.fields) {
    final field = original.withFormat(measurement.kind, options);
    if (_selected(measurement.flags, field.bit)) {
      required |= 1 << field.index;
      length += field.width;
    }
  }
  if (measurement.present != required ||
      (measurement.bytesRead != 0 && measurement.bytesRead != length)) {
    throw const MeasurementCodecException(
      MeasurementCodecErrorCode.range,
      'present mask or byte count does not match selected layout',
    );
  }
  for (var index = 0; index < measurement.values.length; index++) {
    final bit = 1 << index;
    if ((measurement.present & bit == 0 ||
            measurement.unavailable & bit != 0) &&
        measurement.values[index] != 0) {
      throw const MeasurementCodecException(
        MeasurementCodecErrorCode.range,
        'absent and unavailable slots must contain zero',
      );
    }
  }
  final out = BytesBuilder(copy: false);
  for (var i = 0; i < layout.flagBytes; i++) {
    out.addByte((measurement.flags >> (8 * i)) & 0xff);
  }
  for (final original in layout.fields) {
    final field = original.withFormat(measurement.kind, options);
    if (!_selected(measurement.flags, field.bit)) {
      continue;
    }
    final unavailable = measurement.unavailable & (1 << field.index) != 0;
    var value = measurement.values[field.index];
    if (unavailable) {
      if (!field.unavailable) {
        throw const MeasurementCodecException(
          MeasurementCodecErrorCode.range,
          'field has no unavailable sentinel',
        );
      }
      value = _sentinel(field);
    } else {
      final minimum = field.signed ? -(1 << (field.width * 8 - 1)) : 0;
      final maximum = field.signed
          ? (1 << (field.width * 8 - 1)) - 1
          : (1 << (field.width * 8)) - 1;
      if (value < minimum ||
          value > maximum ||
          (field.unavailable && value == _sentinel(field))) {
        throw const MeasurementCodecException(
          MeasurementCodecErrorCode.range,
          'value outside wire range',
        );
      }
    }
    for (var i = 0; i < field.width; i++) {
      out.addByte((value >> (8 * i)) & 0xff);
    }
  }
  return out.toBytes();
}
