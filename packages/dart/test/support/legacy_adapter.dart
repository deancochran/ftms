// Test-only mapping to the historical codec-v1 interface. Expected values never
// flow into these functions; all values come from actual public Dart results.
import 'dart:convert';
import 'dart:typed_data';

import 'package:deancochran_ftms/deancochran_ftms.dart';

const _machineNames = [
  'averageSpeedSupported',
  'cadenceSupported',
  'totalDistanceSupported',
  'inclinationSupported',
  'elevationGainSupported',
  'paceSupported',
  'stepCountSupported',
  'resistanceLevelSupported',
  'strideCountSupported',
  'expendedEnergySupported',
  'heartRateMeasurementSupported',
  'metabolicEquivalentSupported',
  'elapsedTimeSupported',
  'remainingTimeSupported',
  'powerMeasurementSupported',
  'forceOnBeltSupported',
  'userDataRetentionSupported',
];
const _targetNames = [
  'speedTargetSettingSupported',
  'inclinationTargetSettingSupported',
  'resistanceTargetSettingSupported',
  'powerTargetSettingSupported',
  'heartRateTargetSettingSupported',
  'targetedExpendedEnergySupported',
  'targetedStepNumberSupported',
  'targetedStrideNumberSupported',
  'targetedDistanceSupported',
  'targetedTrainingTimeSupported',
  'targetedTimeTwoHRZonesSupported',
  'targetedTimeThreeHRZonesSupported',
  'targetedTimeFiveHRZonesSupported',
  'indoorBikeSimulationSupported',
  'wheelCircumferenceSupported',
  'spinDownControlSupported',
  'targetedCadenceSupported',
];

Map<String, bool> legacyFeatures(Uint8List bytes) {
  final raw = decodeFeatures(bytes);
  return {
    for (var i = 0; i < _machineNames.length; i++)
      _machineNames[i]: raw.machine & (1 << i) != 0,
    for (var i = 0; i < _targetNames.length; i++)
      _targetNames[i]: raw.target & (1 << i) != 0,
    'supportsERG': raw.target & (1 << 3) != 0,
    'supportsSIM': raw.target & (1 << 13) != 0,
    'supportsResistance': raw.target & (1 << 2) != 0,
  };
}

Map<String, Object?> legacyRange(String kind, Uint8List bytes) {
  try {
    final raw = decodeSupportedRange(RangeKind.values.byName(kind), bytes);
    return {
      'kind': raw.kind.name,
      'min': raw.minimum / raw.scaleDivisor,
      'max': raw.maximum / raw.scaleDivisor,
      'increment': raw.increment / raw.scaleDivisor,
      'unit': switch (raw.unit) {
        RangeUnit.kilometresPerHour => 'km/h',
        RangeUnit.percent => 'percent',
        RangeUnit.level => 'level',
        RangeUnit.beatsPerMinute => 'bpm',
        RangeUnit.watts => 'watts',
      },
    };
  } on RangeError {
    return {
      'ok': false,
      'error': {'code': 'range'},
    };
  } on ArgumentError {
    return {
      'ok': false,
      'error': {'code': 'length'},
    };
  }
}

const _operations = [
  'requestControl',
  'reset',
  'setTargetSpeed',
  'setTargetInclination',
  'setTargetResistance',
  'setTargetPower',
  'setTargetHeartRate',
  'startResume',
  'stopPause',
  'setTargetedExpendedEnergy',
  'setTargetedSteps',
  'setTargetedStrides',
  'setTargetedDistance',
  'setTargetedTrainingTime',
  'setTargetedTimeTwoHrZones',
  'setTargetedTimeThreeHrZones',
  'setTargetedTimeFiveHrZones',
  'setIndoorBikeSimulation',
  'setWheelCircumference',
  'spinDown',
  'setTargetedCadence',
];

Uint8List legacyRequest(Map<String, Object?> request) {
  final opcode = _operations.indexOf(request['op']! as String);
  if (opcode < 0) throw StateError('Unknown v1 control operation');
  int scaled(String key, [int scale = 1]) {
    final value = (request[key]! as num) * scale;
    final rounded = value.round();
    if ((value - rounded).abs() > 1e-9) {
      throw StateError(
        'Fixture is not representable at the specified resolution',
      );
    }
    return rounded;
  }

  final List<int> operands = switch (opcode) {
    0 || 1 || 7 => [],
    2 => [scaled('speedKph', 100)],
    3 => [scaled('inclinationPercent', 10)],
    4 => [scaled('resistanceLevel', 10)],
    5 => [scaled('powerWatts')],
    6 => [scaled('heartRateBpm')],
    8 || 19 => [
      switch (request['action']) {
        'stop' || 'start' => 1,
        'pause' || 'ignore' => 2,
        _ => throw StateError('Unknown action'),
      },
    ],
    9 => [scaled('energyKcal')],
    10 => [scaled('steps')],
    11 => [scaled('strides')],
    12 => [scaled('distanceMeters')],
    13 => [scaled('seconds')],
    14 || 15 || 16 => (request['seconds']! as List<Object?>).cast<int>(),
    17 => [
      scaled('windSpeedMps', 1000),
      scaled('gradePercent', 100),
      scaled('crr', 10000),
      scaled('cwKgPerM', 100),
    ],
    18 => [scaled('circumferenceMm', 10)],
    20 => [scaled('cadenceRpm', 2)],
    _ => throw StateError('Unhandled control operation'),
  };
  return encodeControlRequest(ControlRequest(opcode, operands));
}

Map<String, Object?> legacyResponse(Uint8List bytes) {
  try {
    final raw = decodeControlResponse(bytes);
    if (raw.unknownRequest || raw.unexpectedParameters) {
      return {
        'ok': false,
        'error': {'code': 'malformed_response'},
      };
    }
    return {
      'requestOpCode': raw.requestOpcode,
      'resultCode': raw.resultCode,
      'resultCodeName': switch (raw.resultCode) {
        1 => 'success',
        2 => 'not_supported',
        3 => 'invalid_parameter',
        4 => 'operation_failed',
        5 => 'control_not_permitted',
        _ => 'unknown_0x${raw.resultCode.toRadixString(16).padLeft(2, '0')}',
      },
      'success': raw.resultCode == 1,
      'parameter': raw.parameter == 1
          ? {
              'kind': 'spin_down_speeds',
              'targetSpeedLowKph': raw.low / 100,
              'targetSpeedHighKph': raw.high / 100,
            }
          : {'kind': 'none'},
      'issues': [if (raw.unknownResult) 'reserved_value'],
    };
  } on ControlCodecException {
    return {
      'ok': false,
      'error': {'code': 'malformed_response'},
    };
  }
}

final class LegacyParsed {
  const LegacyParsed({
    this.metrics = const {},
    this.status = const {},
    required this.truncated,
    required this.issues,
  });
  final Map<String, Object?> metrics, status;
  final bool truncated;
  final Set<String> issues;
}

LegacyParsed legacyParse(String uuid, Uint8List bytes) {
  final uuids = [
    '2acd',
    '2ace',
    '2acf',
    '2ad0',
    '2ad1',
    '2ad2',
  ].map((short) => '0000$short-0000-1000-8000-00805f9b34fb').toList();
  final index = uuids.indexOf(uuid);
  if (index >= 0) {
    final raw = decodeMeasurement(MeasurementKind.values[index], bytes);
    final view = normalizeMeasurement(raw);
    return LegacyParsed(
      truncated: raw.truncated,
      issues: {
        if (raw.moreData) 'more_data',
        if (raw.truncated) 'truncated',
        if (raw.trailingBytes) 'trailing_bytes',
        if (raw.reservedFlags) 'reserved_flags',
        if (raw.unavailable != 0) 'unavailable',
      },
      metrics: {
        'speedMps': view.speedMps,
        'averageSpeedMps': view.averageSpeedMps,
        'distanceMeters': view.distanceMeters,
        'inclinationPercent': view.inclinationPercent,
        'rampAngleDegrees': view.rampAngleDegrees,
        'positiveElevationGainMeters': view.positiveElevationGainMeters,
        'negativeElevationGainMeters': view.negativeElevationGainMeters,
        'instantaneousPaceSecondsPer500m': view.instantaneousPaceSecondsPer500m,
        'averagePaceSecondsPer500m': view.averagePaceSecondsPer500m,
        'energyKcal': view.energyKcal,
        'energyPerHourKcal': view.energyPerHourKcal,
        'energyPerMinuteKcal': view.energyPerMinuteKcal,
        'hrBpm': view.hrBpm,
        'metabolicEquivalent': view.metabolicEquivalent,
        'elapsedTimeSeconds': view.elapsedTimeSeconds,
        'remainingTimeSeconds': view.remainingTimeSeconds,
        'forceOnBeltNewtons': view.forceOnBeltNewtons,
        'powerWatts': view.powerWatts,
        'stepRateSpm': view.stepRateSpm,
        'averageStepRateSpm': view.averageStepRateSpm,
        'strideCount': view.strideCount,
        'resistanceLevel': view.resistanceLevel,
        'averagePowerWatts': view.averagePowerWatts,
        'floorCount': view.floorCount,
        'stepCount': view.stepCount,
        'strokeRateSpm': view.strokeRateSpm,
        'strokeCount': view.strokeCount,
        'averageStrokeRateSpm': view.averageStrokeRateSpm,
        'cadenceRpm': view.cadenceRpm,
        'averageCadenceRpm': view.averageCadenceRpm,
        if (view.movementDirection != null)
          'movementDirection': view.movementDirection!.name,
      },
    );
  }
  if (uuid == '00002ad3-0000-1000-8000-00805f9b34fb') {
    final raw = decodeTrainingStatus(bytes);
    return LegacyParsed(
      truncated: raw.truncated,
      issues: {
        if (raw.truncated) 'truncated',
        if (raw.trailingBytes) 'trailing_bytes',
        if (raw.reservedFlags != 0) 'reserved_flags',
        if (raw.reservedValue) 'reserved_value',
        if (raw.invalidFlags) 'invalid_flags',
        if (raw.invalidUtf8) 'invalid_utf8',
      },
      status: {
        'code': raw.truncated ? null : raw.code,
        'label': raw.code == 13 ? 'manual_mode' : 'unmapped_${raw.code}',
        'details': {
          'kind': 'training_status',
          'flags': raw.flags,
          'stringPresent': raw.textPresent,
          'extendedStringPresent': raw.extendedString,
          'trainingStatusString': raw.textPresent
              ? utf8.decode(raw.text, allowMalformed: true)
              : null,
        },
      },
    );
  }
  if (uuid != '00002ada-0000-1000-8000-00805f9b34fb') {
    throw StateError('Unhandled characteristic UUID');
  }
  final raw = decodeMachineStatus(bytes);
  final parameter = raw.parameter;
  final (label, details) = switch ((raw.opcode, parameter?.requestOpcode)) {
    (5, 2) => (
      'target_speed_changed',
      <String, Object?>{
        'kind': 'speed',
        'speedKph': parameter!.operands[0] / 100,
      },
    ),
    (18, 17) => (
      'indoor_bike_simulation_parameters_changed',
      <String, Object?>{
        'kind': 'simulation',
        'windSpeedMps': parameter!.operands[0] / 1000,
        'gradePercent': parameter.operands[1] / 100,
        'crr': parameter.operands[2] / 10000,
        'cwKgPerM': parameter.operands[3] / 100,
      },
    ),
    (255, null) => (
      'control_permission_lost',
      <String, Object?>{'kind': 'none'},
    ),
    _ => ('unmapped_${raw.opcode}', <String, Object?>{'kind': 'unmapped'}),
  };
  return LegacyParsed(
    truncated: raw.truncated,
    issues: {
      if (raw.truncated) 'truncated',
      if (raw.trailingBytes) 'trailing_bytes',
      if (raw.unknownOpcode) 'unknown_opcode',
      if (raw.reservedValue) 'reserved_value',
    },
    status: {
      'code': raw.truncated && raw.unknownOpcode && raw.opcode == 0
          ? null
          : raw.opcode,
      'label': label,
      'details': details,
    },
  );
}
