import 'measurements.dart';

/// Cross-trainer motion direction retained by the normalized projection.
enum MeasurementDirection { forward, backward }

/// Immutable physical-unit projection. [raw] retains the authoritative wire evidence.
final class MeasurementNormalized {
  final MeasurementRaw raw;
  final double? speedMps,
      averageSpeedMps,
      distanceMeters,
      inclinationPercent,
      rampAngleDegrees,
      positiveElevationGainMeters,
      negativeElevationGainMeters,
      instantaneousPaceSecondsPer500m,
      averagePaceSecondsPer500m,
      energyKcal,
      energyPerHourKcal,
      energyPerMinuteKcal,
      hrBpm,
      metabolicEquivalent,
      elapsedTimeSeconds,
      remainingTimeSeconds,
      forceOnBeltNewtons,
      powerWatts,
      averagePowerWatts,
      stepRateSpm,
      averageStepRateSpm,
      strideCount,
      resistanceLevel,
      floorCount,
      stepCount,
      strokeRateSpm,
      strokeCount,
      averageStrokeRateSpm,
      cadenceRpm,
      averageCadenceRpm;
  final MeasurementDirection? movementDirection;
  const MeasurementNormalized({
    required this.raw,
    this.speedMps,
    this.averageSpeedMps,
    this.distanceMeters,
    this.inclinationPercent,
    this.rampAngleDegrees,
    this.positiveElevationGainMeters,
    this.negativeElevationGainMeters,
    this.instantaneousPaceSecondsPer500m,
    this.averagePaceSecondsPer500m,
    this.energyKcal,
    this.energyPerHourKcal,
    this.energyPerMinuteKcal,
    this.hrBpm,
    this.metabolicEquivalent,
    this.elapsedTimeSeconds,
    this.remainingTimeSeconds,
    this.forceOnBeltNewtons,
    this.powerWatts,
    this.averagePowerWatts,
    this.stepRateSpm,
    this.averageStepRateSpm,
    this.strideCount,
    this.resistanceLevel,
    this.floorCount,
    this.stepCount,
    this.strokeRateSpm,
    this.strokeCount,
    this.averageStrokeRateSpm,
    this.cadenceRpm,
    this.averageCadenceRpm,
    this.movementDirection,
  });
}

/// Projects raw wire values into documented physical units without changing raw evidence.
///
/// Undefined legacy treadmill-pace units and unavailable or unread selected
/// fields are represented as null. The returned view retains [raw] by reference.
MeasurementNormalized normalizeMeasurement(
  MeasurementRaw raw, {
  MeasurementFormatOptions options = const MeasurementFormatOptions(),
}) {
  double? value(MeasurementField field, [double scale = 1]) =>
      raw.present & (1 << field.index) == 0 ||
          raw.unavailable & (1 << field.index) != 0
      ? null
      : raw.valueAt(field) * scale;
  final legacyPace =
      raw.kind == MeasurementKind.treadmill &&
      options.treadmillPace == MeasurementTreadmillPaceFormat.uint8Legacy;
  return MeasurementNormalized(
    raw: raw,
    speedMps: value(MeasurementField.speed, 1 / 360),
    averageSpeedMps: value(MeasurementField.averageSpeed, 1 / 360),
    distanceMeters: value(MeasurementField.distance),
    inclinationPercent: value(MeasurementField.inclination, .1),
    rampAngleDegrees: value(MeasurementField.rampAngle, .1),
    positiveElevationGainMeters: value(
      MeasurementField.positiveElevation,
      raw.kind == MeasurementKind.treadmill ? .1 : 1,
    ),
    negativeElevationGainMeters: value(
      MeasurementField.negativeElevation,
      raw.kind == MeasurementKind.treadmill ? .1 : 1,
    ),
    instantaneousPaceSecondsPer500m: legacyPace
        ? null
        : value(MeasurementField.instantaneousPace),
    averagePaceSecondsPer500m: legacyPace
        ? null
        : value(MeasurementField.averagePace),
    energyKcal: value(MeasurementField.energy),
    energyPerHourKcal: value(MeasurementField.energyPerHour),
    energyPerMinuteKcal: value(MeasurementField.energyPerMinute),
    hrBpm: value(MeasurementField.heartRate),
    metabolicEquivalent: value(MeasurementField.met, .1),
    elapsedTimeSeconds: value(MeasurementField.elapsed),
    remainingTimeSeconds: value(MeasurementField.remaining),
    forceOnBeltNewtons: value(MeasurementField.force),
    powerWatts: value(MeasurementField.power),
    averagePowerWatts: value(MeasurementField.averagePower),
    stepRateSpm: value(MeasurementField.stepRate),
    averageStepRateSpm: value(MeasurementField.averageStepRate),
    strideCount: value(
      MeasurementField.strideCount,
      raw.kind == MeasurementKind.crossTrainer ? .1 : 1,
    ),
    resistanceLevel: value(
      MeasurementField.resistance,
      options.resistance == MeasurementResistanceFormat.signed16Tenths ? .1 : 1,
    ),
    floorCount: value(MeasurementField.floorCount),
    stepCount: value(MeasurementField.stepCount),
    strokeRateSpm: value(MeasurementField.strokeRate, .5),
    strokeCount: value(MeasurementField.strokeCount),
    averageStrokeRateSpm: value(MeasurementField.averageStrokeRate, .5),
    cadenceRpm: value(MeasurementField.cadence, .5),
    averageCadenceRpm: value(MeasurementField.averageCadence, .5),
    movementDirection: raw.kind == MeasurementKind.crossTrainer
        ? (raw.backward
              ? MeasurementDirection.backward
              : MeasurementDirection.forward)
        : null,
  );
}
