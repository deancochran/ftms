import Foundation

public enum MeasurementKind: UInt8, CaseIterable, Sendable {
  case treadmill, crossTrainer, stepClimber, stairClimber, rower, indoorBike
}
public enum MeasurementField: Int, CaseIterable, Sendable {
  case speed, averageSpeed, distance, inclination, rampAngle, positiveElevation, negativeElevation,
    instantaneousPace, averagePace, totalEnergy, energyPerHour, energyPerMinute, heartRate,
    metabolicEquivalent, elapsedTime, remainingTime, forceOnBelt, power, stepRate, averageStepRate,
    strideCount, resistance, averagePower, floorCount, stepCount, strokeRate, strokeCount,
    averageStrokeRate, cadence, averageCadence
}
public enum ResistanceFormat: Sendable, Equatable { case uint8Whole, sint16Tenths }
public enum TreadmillPaceFormat: Sendable, Equatable { case uint16, uint8Legacy }
public struct MeasurementFormatOptions: Sendable, Equatable {
  public var resistance: ResistanceFormat
  public var treadmillPace: TreadmillPaceFormat
  public init(
    resistance: ResistanceFormat = .uint8Whole, treadmillPace: TreadmillPaceFormat = .uint16
  ) {
    self.resistance = resistance
    self.treadmillPace = treadmillPace
  }
}
public struct Measurement: Equatable, Sendable {
  public var kind: MeasurementKind
  public var flags: UInt32
  public var values: [MeasurementField: Int32]
  public var unavailable: Set<MeasurementField>
  public var diagnostics: FTMSDiagnostics
  public var bytesRead: Int
  /// The wire layout used to decode this value. Re-encoding requires this exact
  /// provenance rather than silently applying a caller's default profile.
  public var format: MeasurementFormatOptions
  public var moreData: Bool { flags & 1 != 0 }
  public var backward: Bool { kind == .crossTrainer && flags & 0x8000 != 0 }
  public init(
    kind: MeasurementKind, flags: UInt32, values: [MeasurementField: Int32] = [:],
    unavailable: Set<MeasurementField> = [], diagnostics: FTMSDiagnostics = .init(),
    bytesRead: Int = 0, format: MeasurementFormatOptions = .init()
  ) {
    self.kind = kind
    self.flags = flags
    self.values = values
    self.unavailable = unavailable
    self.diagnostics = diagnostics
    self.bytesRead = bytesRead
    self.format = format
  }
}
struct Field {
  let bit: Int
  let width: Int
  let field: MeasurementField
  let signed: Bool
  let unavailable: Bool
}
func fields(_ k: MeasurementKind, _ o: MeasurementFormatOptions) -> (Int, UInt32, [Field]) {
  let t: [Field] = [
    Field(bit: 0, width: 2, field: .speed, signed: false, unavailable: false),
    Field(bit: 1, width: 2, field: .averageSpeed, signed: false, unavailable: false),
    Field(bit: 2, width: 3, field: .distance, signed: false, unavailable: false),
    Field(bit: 3, width: 2, field: .inclination, signed: true, unavailable: true),
    Field(bit: 3, width: 2, field: .rampAngle, signed: true, unavailable: true),
    Field(bit: 4, width: 2, field: .positiveElevation, signed: false, unavailable: false),
    Field(bit: 4, width: 2, field: .negativeElevation, signed: false, unavailable: false),
    Field(
      bit: 5, width: o.treadmillPace == .uint16 ? 2 : 1, field: .instantaneousPace, signed: false,
      unavailable: false),
    Field(
      bit: 6, width: o.treadmillPace == .uint16 ? 2 : 1, field: .averagePace, signed: false,
      unavailable: false),
    Field(bit: 7, width: 2, field: .totalEnergy, signed: false, unavailable: true),
    Field(bit: 7, width: 2, field: .energyPerHour, signed: false, unavailable: true),
    Field(bit: 7, width: 1, field: .energyPerMinute, signed: false, unavailable: true),
    Field(bit: 8, width: 1, field: .heartRate, signed: false, unavailable: false),
    Field(bit: 9, width: 1, field: .metabolicEquivalent, signed: false, unavailable: false),
    Field(bit: 10, width: 2, field: .elapsedTime, signed: false, unavailable: false),
    Field(bit: 11, width: 2, field: .remainingTime, signed: false, unavailable: false),
    Field(bit: 12, width: 2, field: .forceOnBelt, signed: true, unavailable: true),
    Field(bit: 12, width: 2, field: .power, signed: true, unavailable: true),
  ]
  let c: [Field] = [
    Field(bit: 0, width: 2, field: .speed, signed: false, unavailable: false),
    Field(bit: 1, width: 2, field: .averageSpeed, signed: false, unavailable: false),
    Field(bit: 2, width: 3, field: .distance, signed: false, unavailable: false),
    Field(bit: 3, width: 2, field: .stepRate, signed: false, unavailable: true),
    Field(bit: 3, width: 2, field: .averageStepRate, signed: false, unavailable: true),
    Field(bit: 4, width: 2, field: .strideCount, signed: false, unavailable: false),
    Field(bit: 5, width: 2, field: .positiveElevation, signed: false, unavailable: false),
    Field(bit: 5, width: 2, field: .negativeElevation, signed: false, unavailable: false),
    Field(bit: 6, width: 2, field: .inclination, signed: true, unavailable: true),
    Field(bit: 6, width: 2, field: .rampAngle, signed: true, unavailable: true),
    Field(
      bit: 7, width: o.resistance == .uint8Whole ? 1 : 2, field: .resistance,
      signed: o.resistance != .uint8Whole, unavailable: false),
    Field(bit: 8, width: 2, field: .power, signed: true, unavailable: false),
    Field(bit: 9, width: 2, field: .averagePower, signed: true, unavailable: false),
    Field(bit: 10, width: 2, field: .totalEnergy, signed: false, unavailable: true),
    Field(bit: 10, width: 2, field: .energyPerHour, signed: false, unavailable: true),
    Field(bit: 10, width: 1, field: .energyPerMinute, signed: false, unavailable: true),
    Field(bit: 11, width: 1, field: .heartRate, signed: false, unavailable: false),
    Field(bit: 12, width: 1, field: .metabolicEquivalent, signed: false, unavailable: false),
    Field(bit: 13, width: 2, field: .elapsedTime, signed: false, unavailable: false),
    Field(bit: 14, width: 2, field: .remainingTime, signed: false, unavailable: false),
  ]
  let s: [Field] = [
    Field(bit: 0, width: 2, field: .floorCount, signed: false, unavailable: false),
    Field(bit: 0, width: 2, field: .stepCount, signed: false, unavailable: false),
    Field(bit: 1, width: 2, field: .stepRate, signed: false, unavailable: false),
    Field(bit: 2, width: 2, field: .averageStepRate, signed: false, unavailable: false),
    Field(bit: 3, width: 2, field: .positiveElevation, signed: false, unavailable: false),
    Field(bit: 4, width: 2, field: .totalEnergy, signed: false, unavailable: true),
    Field(bit: 4, width: 2, field: .energyPerHour, signed: false, unavailable: true),
    Field(bit: 4, width: 1, field: .energyPerMinute, signed: false, unavailable: true),
    Field(bit: 5, width: 1, field: .heartRate, signed: false, unavailable: false),
    Field(bit: 6, width: 1, field: .metabolicEquivalent, signed: false, unavailable: false),
    Field(bit: 7, width: 2, field: .elapsedTime, signed: false, unavailable: false),
    Field(bit: 8, width: 2, field: .remainingTime, signed: false, unavailable: false),
  ]
  let st: [Field] = [
    Field(bit: 0, width: 2, field: .floorCount, signed: false, unavailable: false),
    Field(bit: 1, width: 2, field: .stepRate, signed: false, unavailable: false),
    Field(bit: 2, width: 2, field: .averageStepRate, signed: false, unavailable: false),
    Field(bit: 3, width: 2, field: .positiveElevation, signed: false, unavailable: false),
    Field(bit: 4, width: 2, field: .strideCount, signed: false, unavailable: false),
    Field(bit: 5, width: 2, field: .totalEnergy, signed: false, unavailable: true),
    Field(bit: 5, width: 2, field: .energyPerHour, signed: false, unavailable: true),
    Field(bit: 5, width: 1, field: .energyPerMinute, signed: false, unavailable: true),
    Field(bit: 6, width: 1, field: .heartRate, signed: false, unavailable: false),
    Field(bit: 7, width: 1, field: .metabolicEquivalent, signed: false, unavailable: false),
    Field(bit: 8, width: 2, field: .elapsedTime, signed: false, unavailable: false),
    Field(bit: 9, width: 2, field: .remainingTime, signed: false, unavailable: false),
  ]
  let r: [Field] = [
    Field(bit: 0, width: 1, field: .strokeRate, signed: false, unavailable: false),
    Field(bit: 0, width: 2, field: .strokeCount, signed: false, unavailable: false),
    Field(bit: 1, width: 1, field: .averageStrokeRate, signed: false, unavailable: false),
    Field(bit: 2, width: 3, field: .distance, signed: false, unavailable: false),
    Field(bit: 3, width: 2, field: .instantaneousPace, signed: false, unavailable: false),
    Field(bit: 4, width: 2, field: .averagePace, signed: false, unavailable: false),
    Field(bit: 5, width: 2, field: .power, signed: true, unavailable: false),
    Field(bit: 6, width: 2, field: .averagePower, signed: true, unavailable: false),
    Field(
      bit: 7, width: o.resistance == .uint8Whole ? 1 : 2, field: .resistance,
      signed: o.resistance != .uint8Whole, unavailable: false),
    Field(bit: 8, width: 2, field: .totalEnergy, signed: false, unavailable: true),
    Field(bit: 8, width: 2, field: .energyPerHour, signed: false, unavailable: true),
    Field(bit: 8, width: 1, field: .energyPerMinute, signed: false, unavailable: true),
    Field(bit: 9, width: 1, field: .heartRate, signed: false, unavailable: false),
    Field(bit: 10, width: 1, field: .metabolicEquivalent, signed: false, unavailable: false),
    Field(bit: 11, width: 2, field: .elapsedTime, signed: false, unavailable: false),
    Field(bit: 12, width: 2, field: .remainingTime, signed: false, unavailable: false),
  ]
  let b: [Field] = [
    Field(bit: 0, width: 2, field: .speed, signed: false, unavailable: false),
    Field(bit: 1, width: 2, field: .averageSpeed, signed: false, unavailable: false),
    Field(bit: 2, width: 2, field: .cadence, signed: false, unavailable: false),
    Field(bit: 3, width: 2, field: .averageCadence, signed: false, unavailable: false),
    Field(bit: 4, width: 3, field: .distance, signed: false, unavailable: false),
    Field(
      bit: 5, width: o.resistance == .uint8Whole ? 1 : 2, field: .resistance,
      signed: o.resistance != .uint8Whole, unavailable: false),
    Field(bit: 6, width: 2, field: .power, signed: true, unavailable: false),
    Field(bit: 7, width: 2, field: .averagePower, signed: true, unavailable: false),
    Field(bit: 8, width: 2, field: .totalEnergy, signed: false, unavailable: true),
    Field(bit: 8, width: 2, field: .energyPerHour, signed: false, unavailable: true),
    Field(bit: 8, width: 1, field: .energyPerMinute, signed: false, unavailable: true),
    Field(bit: 9, width: 1, field: .heartRate, signed: false, unavailable: false),
    Field(bit: 10, width: 1, field: .metabolicEquivalent, signed: false, unavailable: false),
    Field(bit: 11, width: 2, field: .elapsedTime, signed: false, unavailable: false),
    Field(bit: 12, width: 2, field: .remainingTime, signed: false, unavailable: false),
  ]
  switch k {
  case .treadmill: return (2, 0x1fff, t)
  case .crossTrainer: return (3, 0xffff, c)
  case .stepClimber: return (2, 0x01ff, s)
  case .stairClimber: return (2, 0x03ff, st)
  case .rower: return (2, 0x1fff, r)
  case .indoorBike: return (2, 0x1fff, b)
  }
}
public func decodeMeasurement(
  _ kind: MeasurementKind, bytes: [UInt8], options: MeasurementFormatOptions = .init()
) throws -> Measurement {
  let (n, valid, fs) = fields(kind, options)
  guard bytes.count >= n else { throw FTMSCodecError.length }
  var flags: UInt32 = 0
  for i in 0..<n { flags |= UInt32(bytes[i]) << UInt32(i * 8) }
  var d = FTMSDiagnostics()
  d.reservedFlags = flags & ~valid != 0
  if d.reservedFlags { d.issues.append("reserved_flags") }
  var result = Measurement(kind: kind, flags: flags, diagnostics: d, bytesRead: n, format: options)
  if flags & 1 != 0 { result.diagnostics.issues.append("more_data") }
  var p = n
  for f in fs where f.bit == 0 ? flags & 1 == 0 : flags & (1 << UInt32(f.bit)) != 0 {
    guard p + f.width <= bytes.count else {
      result.diagnostics.truncated = true
      result.diagnostics.issues.append("truncated")
      result.bytesRead = p
      return result
    }
    let raw: UInt32 =
      f.width == 1 ? UInt32(bytes[p]) : f.width == 2 ? UInt32(u16(bytes, p)) : u24(bytes, p)
    p += f.width
    let sentinel: UInt32 = f.signed ? 0x7fff : f.width == 1 ? 0xff : 0xffff
    if f.unavailable && raw == sentinel {
      result.unavailable.insert(f.field)
      if !result.diagnostics.issues.contains("unavailable") {
        result.diagnostics.issues.append("unavailable")
      }
    } else {
      result.values[f.field] = f.signed ? Int32(i16(bytes, p - f.width)) : Int32(raw)
    }
  }
  result.bytesRead = p
  result.diagnostics.trailingBytes = p < bytes.count
  if result.diagnostics.trailingBytes { result.diagnostics.issues.append("trailing_bytes") }
  return result
}
public func encodeMeasurement(_ m: Measurement, options: MeasurementFormatOptions = .init()) throws
  -> [UInt8]
{
  guard m.format == options else { throw FTMSCodecError.kind }
  let (n, valid, fs) = fields(m.kind, options)
  guard m.flags & ~valid == 0 else { throw FTMSCodecError.range }
  let selected = fs.filter {
    $0.bit == 0 ? m.flags & 1 == 0 : m.flags & (1 << UInt32($0.bit)) != 0
  }
  let supplied = Set(m.values.keys)
  guard supplied.isDisjoint(with: m.unavailable),
    supplied.union(m.unavailable) == Set(selected.map(\.field))
  else { throw FTMSCodecError.range }
  var out: [UInt8] = []
  for i in 0..<n { out.append(UInt8(truncatingIfNeeded: m.flags >> UInt32(8 * i))) }
  for f in selected {
    guard m.values[f.field] != nil || m.unavailable.contains(f.field) else {
      throw FTMSCodecError.range
    }
    if m.unavailable.contains(f.field) {
      guard f.unavailable else { throw FTMSCodecError.range }
      out += f.width == 1 ? [255] : bytes16(f.signed ? 0x7fff : 0xffff)
    } else {
      let x = m.values[f.field]!
      if f.signed {
        guard x >= -32768 && x <= 32767 && (!f.unavailable || x != 32767) else {
          throw FTMSCodecError.range
        }
        out += bytes16(UInt16(bitPattern: Int16(x)))
      } else {
        let max: Int32 = f.width == 1 ? 255 : f.width == 2 ? 65535 : 0xffffff
        guard x >= 0 && x <= max && (!f.unavailable || x != max) else { throw FTMSCodecError.range }
        out += f.width == 3 ? bytes24(UInt32(x)) : f.width == 2 ? bytes16(UInt16(x)) : [UInt8(x)]
      }
    }
  }
  return out
}
