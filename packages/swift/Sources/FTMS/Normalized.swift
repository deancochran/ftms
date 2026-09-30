/// Corpus-facing normalized values. Raw `Measurement.values` always retain wire integers.
public enum NormalizedMetricValue: Equatable, Sendable {
  case number(Double?)
  case direction(MeasurementDirection)
}
public enum MeasurementDirection: String, Equatable, Sendable { case forward, backward }
public typealias NormalizedMetrics = [String: NormalizedMetricValue]

public func normalizeMeasurement(_ measurement: Measurement) -> NormalizedMetrics {
  func value(_ field: MeasurementField, _ scale: Double = 1) -> Double? {
    if measurement.unavailable.contains(field) { return nil }
    return measurement.values[field].map { Double($0) * scale }
  }

  var metrics: NormalizedMetrics = [:]
  let selectedFields = Set(
    fields(measurement.kind, measurement.format).2.filter {
      $0.bit == 0 ? measurement.flags & 1 == 0 : measurement.flags & (1 << UInt32($0.bit)) != 0
    }.map(\.field))
  func put(_ name: String, _ field: MeasurementField, _ scale: Double = 1) {
    if measurement.values[field] != nil || measurement.unavailable.contains(field)
      || (measurement.diagnostics.truncated && selectedFields.contains(field))
    {
      metrics[name] = .number(value(field, scale))
    }
  }
  put("speedMps", .speed, 1.0 / 360)
  put("averageSpeedMps", .averageSpeed, 1.0 / 360)
  put("distanceMeters", .distance)
  put("inclinationPercent", .inclination, 0.1)
  put("rampAngleDegrees", .rampAngle, 0.1)
  put("positiveElevationGainMeters", .positiveElevation, measurement.kind == .treadmill ? 0.1 : 1)
  put("negativeElevationGainMeters", .negativeElevation, measurement.kind == .treadmill ? 0.1 : 1)
  // The legacy treadmill uint8 pace profile has no documented normalized unit.
  let treadmillLegacy =
    measurement.kind == .treadmill && measurement.format.treadmillPace == .uint8Legacy
  put("instantaneousPaceSecondsPer500m", .instantaneousPace, treadmillLegacy ? 0 : 1)
  put("averagePaceSecondsPer500m", .averagePace, treadmillLegacy ? 0 : 1)
  if treadmillLegacy {
    if measurement.values[.instantaneousPace] != nil {
      metrics["instantaneousPaceSecondsPer500m"] = .number(nil)
    }
    if measurement.values[.averagePace] != nil {
      metrics["averagePaceSecondsPer500m"] = .number(nil)
    }
  }
  put("energyKcal", .totalEnergy)
  put("energyPerHourKcal", .energyPerHour)
  put("energyPerMinuteKcal", .energyPerMinute)
  put("hrBpm", .heartRate)
  put("metabolicEquivalent", .metabolicEquivalent, 0.1)
  put("elapsedTimeSeconds", .elapsedTime)
  put("remainingTimeSeconds", .remainingTime)
  put("forceOnBeltNewtons", .forceOnBelt)
  put("powerWatts", .power)
  put("averagePowerWatts", .averagePower)
  put("stepRateSpm", .stepRate)
  put("averageStepRateSpm", .averageStepRate)
  put("strideCount", .strideCount, measurement.kind == .crossTrainer ? 0.1 : 1)
  put("resistanceLevel", .resistance, measurement.format.resistance == .sint16Tenths ? 0.1 : 1)
  put("floorCount", .floorCount)
  put("stepCount", .stepCount)
  put("strokeRateSpm", .strokeRate, 0.5)
  put("strokeCount", .strokeCount)
  put("averageStrokeRateSpm", .averageStrokeRate, 0.5)
  put("cadenceRpm", .cadence, 0.5)
  put("averageCadenceRpm", .averageCadence, 0.5)
  if measurement.kind == .crossTrainer {
    metrics["movementDirection"] = .direction(measurement.backward ? .backward : .forward)
  }
  return metrics
}
