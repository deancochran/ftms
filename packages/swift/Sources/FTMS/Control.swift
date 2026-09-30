import Foundation

public enum ControlOpcode: UInt8, CaseIterable, Sendable {
  case requestControl = 0
  case reset, targetSpeed, targetInclination, targetResistance, targetPower, targetHeartRate,
    startResume, stopPause, targetedEnergy, targetedSteps, targetedStrides, targetedDistance,
    targetedTrainingTime, targetedTimeTwoHrZones, targetedTimeThreeHrZones, targetedTimeFiveHrZones,
    indoorBikeSimulation, wheelCircumference, spinDown, targetedCadence
}
public enum ControlResistanceFormat: Sendable { case sint16Tenths, uint8Tenths }
public struct ControlFormatOptions: Sendable {
  public var resistance: ControlResistanceFormat
  public init(resistance: ControlResistanceFormat = .sint16Tenths) { self.resistance = resistance }
}
/// Strict decoding is the codec-v1 default. Equipment-side diagnostic tools may
/// opt in to retaining non-spin-down trailing bytes as an explicit diagnostic.
public struct ControlResponseFormatOptions: Sendable, Equatable {
  public var allowDiagnosticTrailing: Bool
  public init(allowDiagnosticTrailing: Bool = false) {
    self.allowDiagnosticTrailing = allowDiagnosticTrailing
  }
}
public struct ControlRequest: Equatable, Sendable {
  public var opcode: UInt8
  public var operands: [Int32]
  public init(opcode: UInt8, operands: [Int32] = []) {
    self.opcode = opcode
    self.operands = operands
  }
}
private func controlLength(_ op: Int, _ options: ControlFormatOptions) -> Int? {
  guard op <= 20 else { return nil }
  let l = [1, 1, 3, 3, 3, 3, 2, 1, 2, 3, 3, 3, 4, 3, 5, 7, 11, 7, 3, 2, 3]
  return op == 4 && options.resistance == .uint8Tenths ? 2 : l[op]
}
public func decodeControlRequest(_ b: [UInt8], options: ControlFormatOptions = .init()) throws
  -> ControlRequest
{
  guard let first = b.first else { throw FTMSCodecError.length }
  guard let n = controlLength(Int(first), options) else { throw FTMSCodecError.kind }
  guard b.count == n else { throw FTMSCodecError.length }
  let op = Int(first)
  var v: [Int32] = []
  if [2, 9, 10, 11, 13, 18, 20].contains(op) {
    v = [Int32(u16(b, 1))]
  } else if [3, 5].contains(op) {
    v = [Int32(i16(b, 1))]
  } else if op == 4 {
    v = [options.resistance == .uint8Tenths ? Int32(b[1]) : Int32(i16(b, 1))]
  } else if [6, 8, 19].contains(op) {
    v = [Int32(b[1])]
  } else if op == 12 {
    v = [Int32(u24(b, 1))]
  } else if (14...16).contains(op) {
    v = stride(from: 1, to: n, by: 2).map { Int32(u16(b, $0)) }
  } else if op == 17 {
    v = [Int32(i16(b, 1)), Int32(i16(b, 3)), Int32(b[5]), Int32(b[6])]
  }
  if [8, 19].contains(op), v.first != 1 && v.first != 2 { throw FTMSCodecError.range }
  return ControlRequest(opcode: b[0], operands: v)
}
public func encodeControlRequest(_ r: ControlRequest, options: ControlFormatOptions = .init())
  throws -> [UInt8]
{
  let op = Int(r.opcode)
  guard let n = controlLength(op, options) else { throw FTMSCodecError.kind }
  let expected = [0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 2, 3, 5, 4, 1, 1, 1][op]
  guard r.operands.count == expected else { throw FTMSCodecError.length }
  func signed(_ i: Int) throws -> [UInt8] {
    let value = r.operands[i]
    guard value >= -32768 && value <= 32767 else { throw FTMSCodecError.range }
    return bytes16(UInt16(bitPattern: Int16(value)))
  }
  func unsigned(_ i: Int) throws -> [UInt8] {
    let value = r.operands[i]
    guard value >= 0 && value <= 65535 else { throw FTMSCodecError.range }
    return bytes16(UInt16(value))
  }
  var b = [r.opcode]
  if [2, 9, 10, 11, 13, 18, 20].contains(op) {
    guard r.operands[0] >= 0 && r.operands[0] <= 65535 else { throw FTMSCodecError.range }
    b += try unsigned(0)
  } else if [3, 5].contains(op) {
    b += try signed(0)
  } else if op == 4 {
    if options.resistance == .uint8Tenths {
      guard r.operands[0] >= 0 && r.operands[0] <= 255 else { throw FTMSCodecError.range }
      b += [UInt8(r.operands[0])]
    } else {
      b += try signed(0)
    }
  } else if [6, 8, 19].contains(op) {
    guard
      r.operands[0] >= 0 && r.operands[0] <= 255
        && (![8, 19].contains(op) || [1, 2].contains(r.operands[0]))
    else { throw FTMSCodecError.range }
    b += [UInt8(r.operands[0])]
  } else if op == 12 {
    guard r.operands[0] >= 0 && r.operands[0] <= 0xffffff else { throw FTMSCodecError.range }
    b += bytes24(UInt32(r.operands[0]))
  } else if (14...16).contains(op) {
    for i in r.operands.indices {
      guard r.operands[i] >= 0 && r.operands[i] <= 65535 else { throw FTMSCodecError.range }
      b += try unsigned(i)
    }
  } else if op == 17 {
    b += try signed(0) + signed(1)
    guard r.operands[2] >= 0 && r.operands[2] <= 255 && r.operands[3] >= 0 && r.operands[3] <= 255
    else { throw FTMSCodecError.range }
    b += [UInt8(r.operands[2]), UInt8(r.operands[3])]
  }
  guard b.count == n else { throw FTMSCodecError.malformed("internal") }
  return b
}
public struct ControlResponse: Sendable {
  public var requestOpcode: UInt8
  public var resultCode: UInt8
  public var spinDownSpeeds: (UInt16, UInt16)?
  public var unknownRequest: Bool
  public var unknownResult: Bool
  public var unexpectedParameters: Bool
  public init(
    requestOpcode: UInt8, resultCode: UInt8, spinDownSpeeds: (UInt16, UInt16)? = nil,
    unknownRequest: Bool = false, unknownResult: Bool = false, unexpectedParameters: Bool = false
  ) {
    self.requestOpcode = requestOpcode
    self.resultCode = resultCode
    self.spinDownSpeeds = spinDownSpeeds
    self.unknownRequest = unknownRequest
    self.unknownResult = unknownResult
    self.unexpectedParameters = unexpectedParameters
  }
}
public func decodeControlResponse(_ b: [UInt8], options: ControlResponseFormatOptions = .init())
  throws -> ControlResponse
{
  guard b.count >= 3 else { throw FTMSCodecError.length }
  guard b[0] == 0x80 else { throw FTMSCodecError.kind }
  if b[1] == 19 && b[2] == 1 && b.count != 3 && b.count != 7 { throw FTMSCodecError.length }
  let hasSpinDownParameters = b[1] == 19 && b[2] == 1 && b.count == 7
  guard b.count == 3 || hasSpinDownParameters || options.allowDiagnosticTrailing else {
    throw FTMSCodecError.length
  }
  return ControlResponse(
    requestOpcode: b[1], resultCode: b[2],
    spinDownSpeeds: hasSpinDownParameters ? (u16(b, 3), u16(b, 5)) : nil, unknownRequest: b[1] > 20,
    unknownResult: b[2] < 1 || b[2] > 5,
    unexpectedParameters: b.count != 3 && !hasSpinDownParameters)
}
public func encodeControlResponse(_ r: ControlResponse) throws -> [UInt8] {
  guard
    !r.unknownResult && !r.unexpectedParameters && r.resultCode >= 1 && r.resultCode <= 5
      && r.unknownRequest == (r.requestOpcode > 20)
  else { throw FTMSCodecError.range }
  // Reserved request opcodes may only be represented by Not Supported.
  guard r.requestOpcode <= 20 || (r.unknownRequest && r.resultCode == 2) else {
    throw FTMSCodecError.range
  }
  if let s = r.spinDownSpeeds {
    guard r.requestOpcode == 19 && r.resultCode == 1 else { throw FTMSCodecError.range }
    return [0x80, r.requestOpcode, r.resultCode] + bytes16(s.0) + bytes16(s.1)
  }
  return [0x80, r.requestOpcode, r.resultCode]
}

/// Decodes wire evidence, retaining unknown codes and unexpected parameters as diagnostics.
public func decodeControlResponseRaw(_ bytes: [UInt8]) throws -> ControlResponse {
  try decodeControlResponse(bytes, options: .init(allowDiagnosticTrailing: true))
}

/// Applies the older validated-response contract without discarding evidence in the raw API.
public func decodeValidatedControlResponse(_ bytes: [UInt8]) throws -> ControlResponse {
  let response = try decodeControlResponse(bytes)
  guard !response.unknownRequest && !response.unexpectedParameters else {
    throw FTMSCodecError.kind
  }
  return response
}
