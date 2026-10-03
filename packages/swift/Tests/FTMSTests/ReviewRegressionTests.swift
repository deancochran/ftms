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

@Test func universalMeasurementUUIDDecoderUsesOneStoredFormatAndNamedMetrics() throws {
  let cases: [(String, [UInt8], Double?)] = [
    ("00002acd-0000-1000-8000-00805f9b34fb", [0, 0, 232, 3], 2.7777777777777777),
    ("00002ace00001000800000805f9b34fb", [0, 0, 0, 232, 3], 2.7777777777777777),
    ("00002acf00001000800000805f9b34fb", [0, 0, 12, 0, 44, 1], nil),
    ("00002ad000001000800000805f9b34fb", [0, 0, 20, 0], nil),
    ("00002ad100001000800000805f9b34fb", [0, 0, 64, 44, 1], nil),
    ("00002ad200001000800000805f9b34fb", [0, 0, 232, 3], 2.7777777777777777),
  ]
  for (uuid, bytes, speed) in cases {
    let result = try decodeMeasurement(uuid: uuid, bytes: bytes, format: .init())
    guard case .measurement(let measurement) = result else {
      Issue.record("known UUID was unsupported: \(uuid)")
      continue
    }
    #expect(measurement.raw.values.isEmpty == false)
    #expect(measurement.metrics.speedMps == speed)
  }

  let legacy = try decodeMeasurement(
    uuid: "00002acd-0000-1000-8000-00805f9b34fb", bytes: [0x21, 0, 0],
    format: .init(treadmillPace: .uint8Legacy))
  guard case .measurement(let legacyMeasurement) = legacy else {
    Issue.record("legacy treadmill UUID was unsupported")
    return
  }
  #expect(legacyMeasurement.raw.values[.instantaneousPace] == 0)
  #expect(legacyMeasurement.metrics.instantaneousPaceSecondsPer500m == nil)
  #expect(legacyMeasurement.raw.format.treadmillPace == .uint8Legacy)

  let sentinel = try decodeMeasurement(
    uuid: "00002ad200001000800000805f9b34fb", bytes: [1, 1, 0xff, 0xff, 2, 0, 3])
  guard case .measurement(let unavailable) = sentinel else {
    Issue.record("bike unsupported")
    return
  }
  #expect(unavailable.raw.unavailable.contains(.totalEnergy))
  #expect(unavailable.metrics.energyKcal == nil)
  let prefix = try decodeMeasurement(uuid: "00002ad200001000800000805f9b34fb", bytes: [0xfe, 0x1f])
  guard case .measurement(let truncated) = prefix else {
    Issue.record("bike unsupported")
    return
  }
  #expect(truncated.raw.diagnostics.truncated)

  for uuid in ["00002ACD-0000-1000-8000-00805F9B34FB", "00002ACD00001000800000805F9B34FB", "2AcD", "0x2aCd"] {
    #expect(try decodeMeasurement(uuid: uuid, bytes: [0, 0, 0, 0]).isSupported)
  }
  for uuid in ["00002acd0000-1000-8000-00805f9b34fb", "00002acd_0000_1000_8000_00805f9b34fb", "0x2acd0", "00002acc00001000800000805f9b34fb", "12345678123456781234567812345678"] {
    #expect(try decodeMeasurement(uuid: uuid, bytes: []).isSupported == false)
  }
}
