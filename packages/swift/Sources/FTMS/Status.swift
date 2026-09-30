import Foundation

public struct MachineStatus: Equatable, Sendable {
  public var opcode: UInt8
  public var operands: [Int32]
  public var diagnostics: FTMSDiagnostics
  public init(opcode: UInt8, operands: [Int32] = [], diagnostics: FTMSDiagnostics = .init()) {
    self.opcode = opcode
    self.operands = operands
    self.diagnostics = diagnostics
  }
}

private func machineLength(_ opcode: UInt8) -> Int? {
  switch opcode {
  case 1, 3, 4, 255: return 1
  case 2, 9, 20: return 2
  case 13: return 4
  case 15: return 5
  case 16, 18: return 7
  case 17: return 11
  case 5...8, 10...12, 14, 19, 21: return 3
  default: return nil
  }
}

private func machineControlOpcode(_ statusOpcode: UInt8) -> UInt8? {
  switch statusOpcode {
  case 5...9: return statusOpcode - 3
  case 10...19: return statusOpcode - 1
  case 21: return 20
  default: return nil
  }
}

public func decodeMachineStatus(_ bytes: [UInt8], options: ControlFormatOptions = .init())
  -> MachineStatus
{
  guard let opcode = bytes.first else {
    var diagnostics = FTMSDiagnostics()
    diagnostics.truncated = true
    diagnostics.issues = ["unknown_opcode", "truncated"]
    return MachineStatus(opcode: 0, diagnostics: diagnostics)
  }
  guard let length = machineLength(opcode) else {
    var diagnostics = FTMSDiagnostics()
    diagnostics.issues = ["unknown_opcode"]
    return MachineStatus(opcode: opcode, diagnostics: diagnostics)
  }
  guard bytes.count >= length else {
    var diagnostics = FTMSDiagnostics()
    diagnostics.truncated = true
    diagnostics.issues = ["truncated"]
    return MachineStatus(opcode: opcode, diagnostics: diagnostics)
  }
  var diagnostics = FTMSDiagnostics()
  if bytes.count > length {
    diagnostics.trailingBytes = true
    diagnostics.issues.append("trailing_bytes")
  }
  if opcode == 2 || opcode == 20 {
    // These are status actions, not Control Point requests.  Spin Down status
    // has four defined states while the request only accepts start/stop.
    let valid = opcode == 20 ? (1...4).contains(bytes[1]) : (bytes[1] == 1 || bytes[1] == 2)
    if !valid { diagnostics.issues.append("reserved_value") }
    return MachineStatus(opcode: opcode, operands: [Int32(bytes[1])], diagnostics: diagnostics)
  }
  // Machine Status 0x07 has a fixed sint16 (0.1 level) layout.  It is not
  // selected by the caller's legacy Control Point resistance profile.
  if opcode == 7 {
    return MachineStatus(opcode: opcode, operands: [Int32(i16(bytes, 1))], diagnostics: diagnostics)
  }
  guard let controlOpcode = machineControlOpcode(opcode) else {
    return MachineStatus(opcode: opcode, diagnostics: diagnostics)
  }
  do {
    let request = try decodeControlRequest(
      [controlOpcode] + Array(bytes[1..<length]), options: options)
    return MachineStatus(opcode: opcode, operands: request.operands, diagnostics: diagnostics)
  } catch {
    diagnostics.truncated = true
    diagnostics.issues.append("truncated")
    return MachineStatus(opcode: opcode, diagnostics: diagnostics)
  }
}

public func encodeMachineStatus(_ status: MachineStatus, options: ControlFormatOptions = .init())
  throws -> [UInt8]
{
  guard let length = machineLength(status.opcode), !status.diagnostics.truncated,
    !status.diagnostics.trailingBytes, !status.diagnostics.issues.contains("unknown_opcode"),
    !status.diagnostics.issues.contains("reserved_value")
  else { throw FTMSCodecError.kind }
  if status.opcode == 2 || status.opcode == 20 {
    let valid =
      status.opcode == 20
      ? (1...4).contains(status.operands.first ?? 0)
      : (status.operands.first == 1 || status.operands.first == 2)
    guard status.operands.count == 1, valid else {
      throw FTMSCodecError.range
    }
    return [status.opcode, UInt8(status.operands[0])]
  }
  if status.opcode == 7 {
    guard status.operands.count == 1, status.operands[0] >= -32768, status.operands[0] <= 32767
    else {
      throw FTMSCodecError.range
    }
    return [status.opcode] + bytes16(UInt16(bitPattern: Int16(status.operands[0])))
  }
  guard let controlOpcode = machineControlOpcode(status.opcode) else {
    guard status.operands.isEmpty else { throw FTMSCodecError.range }
    return [status.opcode]
  }
  let encoded = try encodeControlRequest(
    ControlRequest(opcode: controlOpcode, operands: status.operands), options: options)
  guard encoded.count == length else { throw FTMSCodecError.malformed("machine status length") }
  return [status.opcode] + encoded.dropFirst()
}

public struct TrainingStatus: Equatable, Sendable {
  public var flags: UInt8
  public var code: UInt8
  public var text: String?
  public var diagnostics: FTMSDiagnostics
  public init(
    flags: UInt8, code: UInt8, text: String? = nil, diagnostics: FTMSDiagnostics = .init()
  ) {
    self.flags = flags
    self.code = code
    self.text = text
    self.diagnostics = diagnostics
  }
}

public func decodeTrainingStatus(_ bytes: [UInt8]) -> TrainingStatus {
  guard bytes.count >= 2 else {
    var diagnostics = FTMSDiagnostics()
    diagnostics.truncated = true
    diagnostics.issues = ["truncated"]
    return TrainingStatus(flags: bytes.first ?? 0, code: 0, diagnostics: diagnostics)
  }
  let flags = bytes[0]
  var diagnostics = FTMSDiagnostics()
  if flags & ~3 != 0 {
    diagnostics.reservedFlags = true
    diagnostics.issues.append("reserved_flags")
  }
  if flags & 2 != 0 && flags & 1 == 0 { diagnostics.issues.append("invalid_flags") }
  if bytes[1] > 15 { diagnostics.issues.append("reserved_value") }
  let textPresent = flags & 1 != 0
  let text = textPresent ? String(bytes: bytes.dropFirst(2), encoding: .utf8) : nil
  if textPresent && text == nil { diagnostics.issues.append("invalid_utf8") }
  if !textPresent && bytes.count > 2 {
    diagnostics.trailingBytes = true
    diagnostics.issues.append("trailing_bytes")
  }
  return TrainingStatus(flags: flags, code: bytes[1], text: text, diagnostics: diagnostics)
}

public func encodeTrainingStatus(_ status: TrainingStatus) throws -> [UInt8] {
  guard status.flags & ~3 == 0, !(status.flags & 2 != 0 && status.flags & 1 == 0),
    status.code <= 15,
    !status.diagnostics.truncated, !status.diagnostics.trailingBytes,
    status.diagnostics.issues.isEmpty
  else { throw FTMSCodecError.range }
  guard status.flags & 1 != 0 || status.text == nil else { throw FTMSCodecError.range }
  return [status.flags, status.code] + Array((status.text ?? "").utf8)
}

public func trainingStatusLabel(_ code: UInt8) -> String {
  [
    "other", "idle", "warming_up", "low_intensity_interval", "high_intensity_interval",
    "recovery_interval", "isometric", "heart_rate_control", "fitness_test",
    "speed_outside_control_region_low", "speed_outside_control_region_high", "cool_down",
    "watt_control", "manual_mode", "pre_workout", "post_workout",
  ][safe: Int(code)] ?? "unknown_0x\(String(code, radix: 16))"
}

public func machineStatusLabel(_ opcode: UInt8) -> String {
  let labels: [UInt8: String] = [
    1: "reset", 2: "stopped_or_paused_by_user", 3: "safety_key_present",
    4: "started_or_resumed_by_user", 5: "target_speed_changed", 6: "target_inclination_changed",
    7: "target_resistance_level_changed", 8: "target_power_changed",
    9: "targeted_heart_rate_changed", 10: "targeted_expended_energy_changed",
    11: "targeted_step_number_changed", 12: "targeted_stride_number_changed",
    13: "targeted_distance_changed", 14: "targeted_training_time_changed",
    15: "targeted_time_in_two_heart_rate_zones_changed",
    16: "targeted_time_in_three_heart_rate_zones_changed",
    17: "targeted_time_in_five_heart_rate_zones_changed",
    18: "indoor_bike_simulation_parameters_changed", 19: "wheel_circumference_changed",
    20: "spin_down_status", 21: "targeted_cadence_changed", 255: "control_permission_lost",
  ]
  return labels[opcode] ?? "unknown_0x\(String(opcode, radix: 16))"
}

extension Array {
  fileprivate subscript(safe index: Int) -> Element? { indices.contains(index) ? self[index] : nil }
}
