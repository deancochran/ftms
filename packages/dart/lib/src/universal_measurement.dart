import 'dart:typed_data';

import 'measurements.dart';
import 'normalized.dart';

/// Whether a UUID identifies one of the six FTMS machine-data characteristics.
enum MeasurementUuidDecodeStatus { known, unsupported }

/// UUID-selected measurement evidence. A known result retains the existing raw
/// record, normalized view, and diagnostics; an unsupported UUID never guesses
/// a layout from packet bytes.
final class MeasurementUuidDecodeResult {
  final MeasurementUuidDecodeStatus status;
  final String characteristicUuid;
  final MeasurementKind? kind;
  final MeasurementRaw? raw;
  final MeasurementNormalized? normalized;

  const MeasurementUuidDecodeResult._unsupported(this.characteristicUuid)
    : status = MeasurementUuidDecodeStatus.unsupported,
      kind = null,
      raw = null,
      normalized = null;

  const MeasurementUuidDecodeResult._known(
    this.characteristicUuid,
    this.kind,
    this.raw,
    this.normalized,
  ) : status = MeasurementUuidDecodeStatus.known;
}

const _uuidSuffix = '00001000800000805f9b34fb';
const _measurementUuids = <int, MeasurementKind>{
  0x2acd: MeasurementKind.treadmill,
  0x2ace: MeasurementKind.crossTrainer,
  0x2acf: MeasurementKind.stepClimber,
  0x2ad0: MeasurementKind.stairClimber,
  0x2ad1: MeasurementKind.rower,
  0x2ad2: MeasurementKind.indoorBike,
};

String _normalizeMeasurementUuid(String uuid) {
  final value = uuid.trim().toLowerCase();
  final short = value.startsWith('0x') ? value.substring(2) : value;
  if (RegExp(r'^[0-9a-f]{4}$').hasMatch(short)) {
    return '0000$short$_uuidSuffix';
  }
  if (RegExp(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
  ).hasMatch(value)) {
    return value.replaceAll('-', '');
  }
  return value;
}

/// Decodes any specified FTMS machine-data characteristic selected by UUID.
///
/// Standard 16-bit (`2ad2` and `0x2ad2`) aliases are accepted. Full UUIDs must
/// have the Bluetooth base UUID; vendor UUIDs and non-measurement FTMS UUIDs are
/// explicitly unsupported. Short flag words remain known truncated evidence,
/// rather than becoming an unsupported layout.
MeasurementUuidDecodeResult decodeFtmsMeasurement(
  String characteristicUuid,
  Uint8List bytes, {
  MeasurementFormatOptions options = const MeasurementFormatOptions(),
}) {
  final uuid = _normalizeMeasurementUuid(characteristicUuid);
  if (uuid.length != 32 ||
      !RegExp(r'^[0-9a-f]{32}$').hasMatch(uuid) ||
      !uuid.startsWith('0000') ||
      !uuid.endsWith(_uuidSuffix)) {
    return MeasurementUuidDecodeResult._unsupported(uuid);
  }
  final kind = _measurementUuids[int.tryParse(uuid.substring(4, 8), radix: 16)];
  if (kind == null) return MeasurementUuidDecodeResult._unsupported(uuid);
  MeasurementRaw raw;
  try {
    raw = decodeMeasurement(kind, bytes, options: options);
  } on MeasurementCodecException catch (error) {
    if (error.code != MeasurementCodecErrorCode.length) rethrow;
    raw = MeasurementRaw(
      kind: kind,
      flags: 0,
      present: 0,
      unavailable: 0,
      values: List<int>.filled(MeasurementField.values.length, 0),
      truncated: true,
      format: options,
    );
  }
  return MeasurementUuidDecodeResult._known(
    uuid,
    kind,
    raw,
    normalizeMeasurement(raw),
  );
}
