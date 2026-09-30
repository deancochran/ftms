import Foundation

public struct Features: Equatable, Sendable {
  public let machineRaw, targetRaw, machineUnknown, targetUnknown: UInt32
  public init(machineRaw: UInt32, targetRaw: UInt32) {
    self.machineRaw = machineRaw
    self.targetRaw = targetRaw
    machineUnknown = machineRaw & ~0x1ffff
    targetUnknown = targetRaw & ~0x1ffff
  }
  /// Returns false for indices outside the 32-bit feature word.
  public func machine(_ bit: Int) -> Bool {
    guard (0..<32).contains(bit) else { return false }
    return machineRaw & (1 << UInt32(bit)) != 0
  }
  /// Returns false for indices outside the 32-bit target word.
  public func target(_ bit: Int) -> Bool {
    guard (0..<32).contains(bit) else { return false }
    return targetRaw & (1 << UInt32(bit)) != 0
  }
}
public func decodeFeatures(_ bytes: [UInt8]) throws -> Features {
  guard bytes.count == 8 else { throw FTMSCodecError.length }
  let a = UInt32(u16(bytes, 0)) | UInt32(u16(bytes, 2)) << 16
  let b = UInt32(u16(bytes, 4)) | UInt32(u16(bytes, 6)) << 16
  return Features(machineRaw: a, targetRaw: b)
}
public func encodeFeatures(_ f: Features) -> [UInt8] {
  bytes16(UInt16(truncatingIfNeeded: f.machineRaw))
    + bytes16(UInt16(truncatingIfNeeded: f.machineRaw >> 16))
    + bytes16(UInt16(truncatingIfNeeded: f.targetRaw))
    + bytes16(UInt16(truncatingIfNeeded: f.targetRaw >> 16))
}
public enum RangeKind: CaseIterable, Sendable {
  case speed, inclination, resistance, heartRate, power
}
public enum RangeResistanceFormat: Sendable, Equatable { case uint8Whole, sint16Tenths }
public struct RangeFormatOptions: Sendable, Equatable {
  public var resistance: RangeResistanceFormat
  public init(resistance: RangeResistanceFormat = .uint8Whole) { self.resistance = resistance }
}
public struct SupportedRange: Equatable, Sendable {
  public var kind: RangeKind
  public var minimum: Int32
  public var maximum: Int32
  public var increment: Int32
  public var format: RangeFormatOptions
  public init(
    kind: RangeKind, minimum: Int32, maximum: Int32, increment: Int32,
    format: RangeFormatOptions = .init()
  ) {
    self.kind = kind
    self.minimum = minimum
    self.maximum = maximum
    self.increment = increment
    self.format = format
  }
}
public func decodeRange(_ kind: RangeKind, bytes: [UInt8], options: RangeFormatOptions = .init())
  throws -> SupportedRange
{
  let resistanceSigned = kind == .resistance && options.resistance == .sint16Tenths
  let endpointSigned = kind == .inclination || kind == .power || resistanceSigned
  let width = kind == .heartRate || (kind == .resistance && !resistanceSigned) ? 1 : 2
  guard bytes.count == width * 3 else { throw FTMSCodecError.length }
  func endpoint(_ offset: Int) -> Int32 {
    width == 1
      ? Int32(bytes[offset])
      : endpointSigned ? Int32(i16(bytes, offset)) : Int32(u16(bytes, offset))
  }
  // FTMS uses unsigned increments even for signed inclination and power endpoints.
  func increment(_ offset: Int) -> Int32 {
    width == 1 ? Int32(bytes[offset]) : Int32(u16(bytes, offset))
  }
  let result = SupportedRange(
    kind: kind, minimum: endpoint(0), maximum: endpoint(width), increment: increment(width * 2),
    format: options)
  guard result.increment > 0, result.minimum <= result.maximum else { throw FTMSCodecError.range }
  return result
}
public func encodeRange(_ range: SupportedRange, options: RangeFormatOptions = .init()) throws
  -> [UInt8]
{
  guard range.format == options else { throw FTMSCodecError.kind }
  let resistanceSigned = range.kind == .resistance && options.resistance == .sint16Tenths
  let endpointSigned = range.kind == .inclination || range.kind == .power || resistanceSigned
  let width = range.kind == .heartRate || (range.kind == .resistance && !resistanceSigned) ? 1 : 2
  guard range.increment > 0, range.minimum <= range.maximum else { throw FTMSCodecError.range }
  func endpoint(_ value: Int32) throws -> [UInt8] {
    if width == 1 {
      guard value >= 0 && value <= 255 else { throw FTMSCodecError.range }
      return [UInt8(value)]
    }
    if endpointSigned {
      guard value >= -32768 && value <= 32767 else { throw FTMSCodecError.range }
      return bytes16(UInt16(bitPattern: Int16(truncatingIfNeeded: value)))
    }
    guard value >= 0 && value <= 65535 else { throw FTMSCodecError.range }
    return bytes16(UInt16(value))
  }
  func increment(_ value: Int32) throws -> [UInt8] {
    guard value > 0 else { throw FTMSCodecError.range }
    if width == 1 {
      guard value <= 255 else { throw FTMSCodecError.range }
      return [UInt8(value)]
    }
    guard value <= 65535 else { throw FTMSCodecError.range }
    return bytes16(UInt16(value))
  }
  return try endpoint(range.minimum) + endpoint(range.maximum) + increment(range.increment)
}

public func normalizedFeatures(_ features: Features) -> [String: Bool] {
  let machineNames = [
    "averageSpeedSupported", "cadenceSupported", "totalDistanceSupported", "inclinationSupported",
    "elevationGainSupported", "paceSupported", "stepCountSupported", "resistanceLevelSupported",
    "strideCountSupported", "expendedEnergySupported", "heartRateMeasurementSupported",
    "metabolicEquivalentSupported", "elapsedTimeSupported", "remainingTimeSupported",
    "powerMeasurementSupported", "forceOnBeltSupported", "userDataRetentionSupported",
  ]
  let targetNames = [
    "speedTargetSettingSupported", "inclinationTargetSettingSupported",
    "resistanceTargetSettingSupported", "powerTargetSettingSupported",
    "heartRateTargetSettingSupported", "targetedExpendedEnergySupported",
    "targetedStepNumberSupported", "targetedStrideNumberSupported", "targetedDistanceSupported",
    "targetedTrainingTimeSupported", "targetedTimeTwoHRZonesSupported",
    "targetedTimeThreeHRZonesSupported", "targetedTimeFiveHRZonesSupported",
    "indoorBikeSimulationSupported", "wheelCircumferenceSupported", "spinDownControlSupported",
    "targetedCadenceSupported",
  ]
  var result: [String: Bool] = [:]
  for (bit, name) in machineNames.enumerated() { result[name] = features.machine(bit) }
  for (bit, name) in targetNames.enumerated() { result[name] = features.target(bit) }
  result["supportsERG"] = features.target(3)
  result["supportsSIM"] = features.target(13)
  result["supportsResistance"] = features.target(2)
  return result
}

public func normalizeRange(_ range: SupportedRange) -> (
  min: Double, max: Double, increment: Double, unit: String
) {
  let scale: Double
  let unit: String
  switch range.kind {
  case .speed:
    scale = 0.01
    unit = "km/h"
  case .inclination:
    scale = 0.1
    unit = "percent"
  case .resistance:
    scale = range.format.resistance == .sint16Tenths ? 0.1 : 1
    unit = "level"
  case .heartRate:
    scale = 1
    unit = "bpm"
  case .power:
    scale = 1
    unit = "watts"
  }
  return (
    Double(range.minimum) * scale, Double(range.maximum) * scale, Double(range.increment) * scale,
    unit
  )
}
