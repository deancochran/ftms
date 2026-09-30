import FTMS
import Testing

@Test func measurementEncodingRejectsContradictoryPresence() throws {
  let invalid: [Measurement] = [
    .init(kind: .indoorBike, flags: 0, values: [.speed: 100, .power: 300]),
    .init(kind: .indoorBike, flags: 0, values: [.speed: 100], unavailable: [.totalEnergy]),
    .init(
      kind: .indoorBike, flags: 0x101,
      values: [.totalEnergy: 1, .energyPerHour: 2, .energyPerMinute: 3],
      unavailable: [.totalEnergy]),
  ]
  for input in invalid {
    #expect(throws: FTMSCodecError.range) { try encodeMeasurement(input) }
  }
  let valid = Measurement(
    kind: .indoorBike, flags: 0x101,
    values: [.energyPerHour: 2, .energyPerMinute: 3],
    unavailable: [.totalEnergy])
  #expect(try encodeMeasurement(valid) == [1, 1, 255, 255, 2, 0, 3])
}

@Test func capabilityUUIDsMustBeCanonicalASCII() throws {
  for uuid in [
    "not-a-valid-uuid", "00002ACC00001000800000805f9b34fb",
    String(repeating: "a", count: 31), String(repeating: "a", count: 33),
    String(repeating: "g", count: 32), String(repeating: "０", count: 32),
  ] {
    let input = CapabilitySnapshot(
      discovery: 2, scope: 1, generation: 0,
      characteristics: [.init(uuid: uuid, properties: 0, readState: 0)])
    #expect(throws: FTMSCodecError.kind) { try evaluateCapabilities(input) }
  }
  let uuid = String(repeating: "a", count: 32)
  let report = try evaluateCapabilities(
    .init(
      discovery: 2, scope: 1, generation: 0,
      characteristics: [.init(uuid: uuid, properties: 0, readState: 0)]))
  #expect(report.observations.first?.uuid == uuid)
  #expect(report.observations.first?.knownKind == 0)
}

@Test func malformedByteInputsNeverTrap() throws {
  var seed: UInt32 = 0x4654_4d53
  for count in 0...64 {
    for _ in 0..<32 {
      let bytes: [UInt8] = (0..<count).map { _ in
        seed = seed &* 1_664_525 &+ 1_013_904_223
        return UInt8(truncatingIfNeeded: seed >> 24)
      }
      for kind in MeasurementKind.allCases { _ = try? decodeMeasurement(kind, bytes: bytes) }
      for kind in RangeKind.allCases { _ = inspectRange(kind, bytes: bytes) }
      _ = try? decodeFeatures(bytes)
      _ = try? decodeControlRequest(bytes)
      _ = try? decodeControlResponseRaw(bytes)
      _ = decodeMachineStatus(bytes)
      _ = decodeTrainingStatus(bytes)
    }
  }
  let features = Features(machineRaw: .max, targetRaw: .max)
  for bit in [Int.min, -1, 32, Int.max] {
    #expect(!features.machine(bit))
    #expect(!features.target(bit))
  }
}

@Test func rawUnknownResponsesRemainEvidence() throws {
  let unsupported = try decodeControlResponseRaw([0x80, 0xfa, 2])
  #expect(unsupported.unknownRequest)
  #expect(try encodeControlResponse(unsupported) == [0x80, 0xfa, 2])
  #expect(throws: FTMSCodecError.self) { try decodeValidatedControlResponse([0x80, 0xfa, 2]) }
  for result: UInt8 in [1, 6] {
    let response = try decodeControlResponseRaw([0x80, 0x15, result])
    #expect(response.unknownRequest)
    #expect(response.unknownResult == (result == 6))
    #expect(throws: FTMSCodecError.self) { try encodeControlResponse(response) }
  }
  #expect(throws: FTMSCodecError.self) {
    try encodeControlResponse(
      ControlResponse(requestOpcode: 5, resultCode: 1, unknownRequest: true))
  }
}

@Test func normalizedAlternativesAndFragments() throws {
  let options = MeasurementFormatOptions(resistance: .sint16Tenths)
  for (kind, bytes): (MeasurementKind, [UInt8]) in [
    (.indoorBike, [0x21, 0, 12, 0]),
    (.rower, [0x81, 0, 12, 0]),
    (.crossTrainer, [0x81, 0, 0, 12, 0]),
  ] {
    let metrics = normalizeMeasurement(try decodeMeasurement(kind, bytes: bytes, options: options))
    guard case .number(let value)? = metrics["resistanceLevel"], let value else {
      Issue.record("missing resistance")
      continue
    }
    #expect(abs(value - 1.2) < 0.000001)
  }
  let cross = try decodeMeasurement(.crossTrainer, bytes: [1, 0x80, 0])
  #expect(normalizeMeasurement(cross) == ["movementDirection": .direction(.backward)])
  let bike = try decodeMeasurement(.indoorBike, bytes: [0x41, 0, 1])
  #expect(normalizeMeasurement(bike) == ["powerWatts": .number(nil)])
}
