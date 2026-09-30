import Foundation

/// Caller-owned snapshot evidence. This pure evaluator performs no GATT I/O and does not authorize control.
public struct CapabilityCharacteristic: Sendable {
  public let uuid: String
  public let properties: UInt16
  public let readState: Int
  public let reason: Int
  public let bytes: [UInt8]
  public init(
    uuid: String, properties: UInt16, readState: Int, reason: Int = 0, bytes: [UInt8] = []
  ) {
    self.uuid = uuid
    self.properties = properties
    self.readState = readState
    self.reason = reason
    self.bytes = bytes
  }
}
public struct CapabilityC7: Sendable {
  public let bondingSupported, featureMayChangeOverLifetime: Bool?
  public init(bondingSupported: Bool? = nil, featureMayChangeOverLifetime: Bool? = nil) {
    self.bondingSupported = bondingSupported
    self.featureMayChangeOverLifetime = featureMayChangeOverLifetime
  }
}
public struct CapabilitySnapshot: Sendable {
  public let discovery, scope: Int
  public let generation: UInt32
  public let characteristics: [CapabilityCharacteristic]
  public let c7: CapabilityC7?
  public init(
    discovery: Int, scope: Int, generation: UInt32, characteristics: [CapabilityCharacteristic],
    c7: CapabilityC7? = nil
  ) {
    self.discovery = discovery
    self.scope = scope
    self.generation = generation
    self.characteristics = characteristics
    self.c7 = c7
  }
}
public struct CapabilityRangeValue: Equatable, Sendable {
  public let kind, minimum, maximum, increment, scaleDivisor, unit: Int
}
public struct CapabilityRangeInspection: Equatable, Sendable {
  public let presence, decode: Int
  public let inputIndex: Int?
  public let value: CapabilityRangeValue?
}
public struct CapabilityOperation: Equatable, Sendable {
  public let opcode, targetBit, optionalInTable, declaration, prerequisite, reasons: Int
}
public struct CapabilityObservation: Equatable, Sendable {
  public let inputIndex: Int
  public let uuid: String
  public let properties, knownKind, readState, reason, readSize: Int
}
public struct CapabilityDiagnostic: Equatable, Sendable {
  public let code, knownKind: Int
  public let inputIndex: Int?
}
public struct CapabilityReport: Sendable {
  public let generation, discovery, scope, observationCount, diagnosticCount: Int
  public let presence: [Int]
  public let feature: [Int?]
  public let ranges: [CapabilityRangeInspection]
  public let operations: [CapabilityOperation]
  public let observations: [CapabilityObservation]
  public let diagnostics: [CapabilityDiagnostic]
}

public enum RangeInspectionStatus: String, Sendable { case valid, length, range }
public enum RangeProfile: String, Sendable {
  case uint16Hundredths, signed16Tenths, uint8Whole, uint8Bpm, signed16Watts
}
public struct RangeInspectionCandidate: Equatable, Sendable {
  public let profile: RangeProfile
  public let expectedLength: Int
  public let status: RangeInspectionStatus
  public let value: SupportedRange?
}
public struct RangeInspection: Equatable, Sendable {
  public let selectedProfile: RangeProfile
  public let actualLength, expectedLength: Int
  public let status: RangeInspectionStatus
  public let value: SupportedRange?
  public let candidates: [RangeInspectionCandidate]
}

private func profile(_ kind: RangeKind, _ options: RangeFormatOptions) -> RangeProfile {
  switch kind {
  case .speed: .uint16Hundredths
  case .inclination: .signed16Tenths
  case .resistance: options.resistance == .sint16Tenths ? .signed16Tenths : .uint8Whole
  case .heartRate: .uint8Bpm
  case .power: .signed16Watts
  }
}
/// Inspects all defined layouts while honoring the caller-selected resistance layout; no layout is inferred from bytes.
public func inspectRange(_ kind: RangeKind, bytes: [UInt8], options: RangeFormatOptions = .init())
  -> RangeInspection
{
  let choices: [RangeFormatOptions] =
    kind == .resistance
    ? [.init(resistance: .uint8Whole), .init(resistance: .sint16Tenths)] : [.init()]
  let candidates = choices.map { choice -> RangeInspectionCandidate in
    let p = profile(kind, choice)
    let expected = (p == .uint8Whole || p == .uint8Bpm) ? 3 : 6
    do {
      return .init(
        profile: p, expectedLength: expected, status: .valid,
        value: try decodeRange(kind, bytes: bytes, options: choice))
    } catch FTMSCodecError.range {
      return .init(profile: p, expectedLength: expected, status: .range, value: nil)
    } catch { return .init(profile: p, expectedLength: expected, status: .length, value: nil) }
  }
  let selected = candidates.first { $0.profile == profile(kind, options) }!
  return .init(
    selectedProfile: selected.profile, actualLength: bytes.count,
    expectedLength: selected.expectedLength, status: selected.status, value: selected.value,
    candidates: candidates)
}

private let capBase = "00001000800000805f9b34fb"
private let targetForOpcode = [
  255, 255, 0, 1, 2, 3, 4, 255, 255, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
]
private let rangeForTarget = [0, 1, 2, 4, 3]
private let requiredProperties = [0, 2, 16, 16, 16, 16, 16, 16, 18, 2, 2, 2, 2, 2, 40, 16]
private func capKind(_ uuid: String) -> Int {
  guard uuid.count == 32, uuid.allSatisfy({ $0.isHexDigit && !$0.isUppercase }),
    uuid.hasPrefix("0000"), String(uuid.dropFirst(8)) == capBase,
    let value = Int(uuid.dropFirst(4).prefix(4), radix: 16), value >= 0x2acc && value <= 0x2ada
  else { return 0 }
  return value - 0x2acc + 1
}
private func c7Unknown(_ s: CapabilitySnapshot) -> Bool {
  let c = s.c7
  return
    !(c?.bondingSupported == false || c?.featureMayChangeOverLifetime == false
    || (c?.bondingSupported == true && c?.featureMayChangeOverLifetime == true))
}

/// Evaluates conservative static FTMS capability evidence. It never claims current control permission.
public func evaluateCapabilities(
  _ s: CapabilitySnapshot, rangeOptions: RangeFormatOptions = .init()
) throws -> CapabilityReport {
  guard (0...3).contains(s.discovery), (0...3).contains(s.scope) else { throw FTMSCodecError.range }
  for c in s.characteristics {
    // UUID evidence is canonical ASCII, not user-facing Unicode hex text.
    guard c.uuid.utf8.count == 32,
      c.uuid.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) })
    else { throw FTMSCodecError.kind }
    guard (0...2).contains(c.readState), (0...5).contains(c.reason),
      c.readState == 2 || c.reason == 0, c.readState == 1 || c.bytes.isEmpty
    else { throw FTMSCodecError.range }
  }
  let cs = s.characteristics
  let kinds = cs.map { capKind($0.uuid) }
  let scopeOk = s.scope == 1
  var first = Array(repeating: -1, count: 16)
  var counts = Array(repeating: 0, count: 16)
  var presence = Array(repeating: 0, count: 16)
  var diagnostics: [CapabilityDiagnostic] = []
  for (i, k) in kinds.enumerated() where k != 0 {
    if first[k] < 0 { first[k] = i }
    counts[k] = min(2, counts[k] + 1)
  }
  for k in 1..<16 {
    if counts[k] > 1 {
      presence[k] = 3
      diagnostics.append(.init(code: 3, knownKind: k, inputIndex: first[k]))
    } else if counts[k] == 1 {
      presence[k] = 2
    } else if s.discovery == 2 && scopeOk {
      presence[k] = 1
    }
  }
  if !scopeOk { diagnostics.append(.init(code: 0, knownKind: 0, inputIndex: nil)) }
  let absent = s.scope == 2 && s.discovery == 2 && cs.isEmpty
  if s.scope == 2 && !absent { diagnostics.append(.init(code: 11, knownKind: 0, inputIndex: nil)) }
  if s.discovery != 2 {
    diagnostics.append(.init(code: s.discovery == 3 ? 2 : 1, knownKind: 0, inputIndex: nil))
  }
  if scopeOk {
    for (i, c) in cs.enumerated() {
      let k = kinds[i]
      guard k != 0 else { continue }
      let c7Required =
        k == 1 && s.c7?.bondingSupported == true && s.c7?.featureMayChangeOverLifetime == true
      let unknown = k == 1 && c7Unknown(s)
      let expected = requiredProperties[k] | (c7Required ? 32 : 0)
      if c.properties & UInt16(expected) != UInt16(expected) {
        diagnostics.append(.init(code: 5, knownKind: k, inputIndex: i))
      }
      if c.properties & ~UInt16(unknown ? expected | 32 : expected) != 0 {
        diagnostics.append(.init(code: 6, knownKind: k, inputIndex: i))
      }
      if unknown { diagnostics.append(.init(code: 12, knownKind: k, inputIndex: i)) }
      if c.readState == 2 {
        diagnostics.append(.init(code: c.reason == 2 ? 8 : 7, knownKind: k, inputIndex: i))
      }
    }
  }
  var machine = 0
  var target = 0
  var machineUnknown = 0
  var targetUnknown = 0
  func decode(_ k: Int, _ r: Int? = nil) -> (Int, CapabilityRangeValue?) {
    guard scopeOk, presence[k] == 2 else { return (0, nil) }
    let c = cs[first[k]]
    if c.readState == 2 { return (3, nil) }
    guard c.readState == 1 else { return (0, nil) }
    do {
      if let r {
        let raw = try decodeRange(
          [.speed, .inclination, .resistance, .heartRate, .power][r], bytes: c.bytes,
          options: r == 2 ? rangeOptions : .init())
        let divisor =
          r == 0 ? 100 : (r == 1 || (r == 2 && rangeOptions.resistance == .sint16Tenths) ? 10 : 1)
        return (
          1,
          .init(
            kind: r, minimum: Int(raw.minimum), maximum: Int(raw.maximum),
            increment: Int(raw.increment), scaleDivisor: divisor, unit: r)
        )
      }
      let raw = try decodeFeatures(c.bytes)
      machine = Int(raw.machineRaw)
      target = Int(raw.targetRaw)
      machineUnknown = Int(raw.machineUnknown)
      targetUnknown = Int(raw.targetUnknown)
      return (1, nil)
    } catch { return (2, nil) }
  }
  let fd = decode(1).0
  let feature: [Int?] = [
    presence[1], fd, scopeOk && presence[1] == 2 ? first[1] : nil, machine, target, machineUnknown,
    targetUnknown,
  ]
  if fd == 2 { diagnostics.append(.init(code: 9, knownKind: 1, inputIndex: first[1])) }
  let ranges = (0..<5).map { r -> CapabilityRangeInspection in
    let k = 9 + r
    let x = decode(k, r)
    if x.0 == 2 { diagnostics.append(.init(code: 9, knownKind: k, inputIndex: first[k])) }
    return .init(
      presence: presence[k], decode: x.0, inputIndex: scopeOk && presence[k] == 2 ? first[k] : nil,
      value: x.1)
  }
  if scopeOk {
    if presence[1] == 1 { diagnostics.append(.init(code: 4, knownKind: 1, inputIndex: nil)) }
    if (presence[14] == 2 || presence[14] == 3) && presence[15] == 1 {
      diagnostics.append(.init(code: 4, knownKind: 15, inputIndex: nil))
    }
    if fd == 1 {
      if target & 0x1ffff != 0 && presence[14] == 1 {
        diagnostics.append(.init(code: 4, knownKind: 14, inputIndex: nil))
      }
      for b in 0..<5 where target & (1 << b) != 0 {
        let k = 9 + rangeForTarget[b]
        if presence[k] == 1 { diagnostics.append(.init(code: 10, knownKind: k, inputIndex: nil)) }
      }
    }
  }
  func reasons(_ k: Int, _ unavailable: Int, _ invalid: Int) -> Int {
    if presence[k] == 0 { return unavailable }
    if presence[k] != 2 { return invalid }
    let p = Int(cs[first[k]].properties)
    if k == 1 && c7Unknown(s) {
      return 1024 | (((p & 2) == 0 || (p & ~(2 | 32)) != 0) ? invalid : 0)
    }
    let expected =
      requiredProperties[k]
      | (k == 1 && s.c7?.bondingSupported == true && s.c7?.featureMayChangeOverLifetime == true
        ? 32 : 0)
    return p == expected ? 0 : invalid
  }
  let operations = targetForOpcode.enumerated().map { opcode, bit -> CapabilityOperation in
    var declaration = 0
    var prerequisite = 2
    var why = 0
    if !scopeOk {
      why = 1
      if absent {
        declaration = 1
        prerequisite = 0
      } else if s.scope == 2 {
        prerequisite = 3
      }
      return .init(
        opcode: opcode, targetBit: bit, optionalInTable: (opcode == 18 || opcode == 19) ? 1 : 0,
        declaration: declaration, prerequisite: prerequisite, reasons: why)
    }
    if bit == 255 {
      declaration = presence[14] == 2 ? 2 : presence[14] == 1 ? 1 : 0
    } else if fd == 1 {
      declaration = target & (1 << bit) != 0 ? 2 : 1
    }
    if declaration == 1 {
      return .init(
        opcode: opcode, targetBit: bit, optionalInTable: (opcode == 18 || opcode == 19) ? 1 : 0,
        declaration: declaration, prerequisite: 0, reasons: 0)
    }
    if s.discovery != 2 { why |= 2 }
    why |= reasons(1, 4, 8)
    if bit != 255 && presence[1] == 2 { why |= fd == 2 ? 8 : fd == 1 ? 0 : 4 }
    why |= reasons(14, 16, 32) | reasons(15, 64, 128)
    if bit != 255 && bit < 5 && declaration == 2 {
      let r = rangeForTarget[bit]
      let k = 9 + r
      why |= reasons(k, 256, 512)
      if presence[k] == 2 { why |= ranges[r].decode == 2 ? 512 : ranges[r].decode == 1 ? 0 : 256 }
    }
    prerequisite = why & (8 | 32 | 128 | 512) != 0 ? 3 : why == 0 ? 1 : 2
    return .init(
      opcode: opcode, targetBit: bit, optionalInTable: (opcode == 18 || opcode == 19) ? 1 : 0,
      declaration: declaration, prerequisite: prerequisite, reasons: why)
  }
  let observations = cs.enumerated().map { i, c in
    CapabilityObservation(
      inputIndex: i, uuid: c.uuid, properties: Int(c.properties), knownKind: kinds[i],
      readState: c.readState, reason: c.reason, readSize: c.bytes.count)
  }
  return .init(
    generation: Int(s.generation), discovery: s.discovery, scope: s.scope,
    observationCount: cs.count, diagnosticCount: diagnostics.count, presence: presence,
    feature: feature, ranges: ranges, operations: operations, observations: observations,
    diagnostics: diagnostics)
}
