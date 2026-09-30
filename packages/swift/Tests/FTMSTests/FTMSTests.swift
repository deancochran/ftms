import Foundation
import Testing

@testable import FTMS

private typealias JSON = [String: Any]
// Canonical JSON serialization preserves booleans versus numeric 0/1, unlike
// NSDictionary equality. Key ordering is irrelevant; array ordering is exact.
private func exactJSONEqual(_ lhs: Any, _ rhs: Any) -> Bool {
  guard
    let left = try? JSONSerialization.data(
      withJSONObject: lhs, options: [.sortedKeys, .fragmentsAllowed]),
    let right = try? JSONSerialization.data(
      withJSONObject: rhs, options: [.sortedKeys, .fragmentsAllowed])
  else { return false }
  return left == right
}

@Test func exactJSONComparisonPreservesTypes() {
  #expect(!exactJSONEqual(["success": 1], ["success": true]))
  #expect(exactJSONEqual(["a": 1, "b": 2], ["b": 2, "a": 1]))
}
private let expectedCounts = [
  "features": 35, "ranges": 7, "controls": 21, "controlResponses": 12, "measurements": 8,
  "statuses": 4, "diagnostics": 10,
]

private func sharedJSON(_ relative: String) throws -> JSON {
  let testFile = URL(fileURLWithPath: #filePath)
  let root = testFile.deletingLastPathComponent().appendingPathComponent(
    "../../../../shared/conformance/\(relative)"
  ).standardized
  return try JSONSerialization.jsonObject(with: Data(contentsOf: root)) as! JSON
}
private func bytes(_ object: JSON, key: String = "bytes") -> [UInt8] {
  (object[key] as! [NSNumber]).map(\.uint8Value)
}
private func kind(_ string: String) -> MeasurementKind {
  [.treadmill, .crossTrainer, .stepClimber, .stairClimber, .rower, .indoorBike][
    ["00002acd", "00002ace", "00002acf", "00002ad0", "00002ad1", "00002ad2"].firstIndex(
      where: string.hasPrefix)!]
}
private func rangeKind(_ value: String) -> RangeKind {
  switch value {
  case "speed": .speed
  case "inclination": .inclination
  case "resistance": .resistance
  case "heartRate": .heartRate
  default: .power
  }
}

private func hexBytes(_ value: String) -> [UInt8] {
  stride(from: 0, to: value.count, by: 2).map {
    UInt8(
      value[
        value.index(
          value.startIndex, offsetBy: $0)...value.index(value.startIndex, offsetBy: $0 + 1)],
      radix: 16)!
  }
}
private func capabilitySnapshot(_ value: JSON) -> CapabilitySnapshot {
  func truth(_ value: Any?) -> Bool? {
    guard let value = value as? NSNumber else { return nil }
    return value.intValue == 0 ? nil : value.intValue == 2
  }
  let c7 = (value["c7"] as? JSON).map {
    CapabilityC7(
      bondingSupported: truth($0["bondingSupported"]),
      featureMayChangeOverLifetime: truth($0["featureMayChangeOverLifetime"]))
  }
  return CapabilitySnapshot(
    discovery: (value["discovery"] as! NSNumber).intValue,
    scope: (value["scope"] as! NSNumber).intValue,
    generation: (value["generation"] as! NSNumber).uint32Value,
    characteristics: (value["characteristics"] as! [JSON]).map { c in
      CapabilityCharacteristic(
        uuid: c["uuid"] as! String, properties: (c["properties"] as! NSNumber).uint16Value,
        readState: (c["readState"] as! NSNumber).intValue,
        reason: (c["reason"] as! NSNumber).intValue, bytes: hexBytes(c["bytes"] as! String))
    }, c7: c7)
}
private func reportJSON(_ r: CapabilityReport) -> JSON {
  [
    "generation": r.generation, "discovery": r.discovery, "scope": r.scope,
    "observationCount": r.observationCount, "diagnosticCount": r.diagnosticCount,
    "presence": r.presence, "feature": r.feature.map { $0 as Any },
    "ranges": r.ranges.map {
      [
        $0.presence, $0.decode, $0.inputIndex as Any,
        $0.value.map { [$0.kind, $0.minimum, $0.maximum, $0.increment, $0.scaleDivisor, $0.unit] }
          as Any,
      ]
    },
    "operations": r.operations.map {
      [$0.opcode, $0.targetBit, $0.optionalInTable, $0.declaration, $0.prerequisite, $0.reasons]
    },
    "observations": r.observations.map {
      [$0.inputIndex, $0.uuid, $0.properties, $0.knownKind, $0.readState, $0.reason, $0.readSize]
    }, "diagnostics": r.diagnostics.map { [$0.code, $0.knownKind, $0.inputIndex as Any] },
  ]
}
private func cloneJSON(_ value: Any) -> Any {
  try! JSONSerialization.jsonObject(with: JSONSerialization.data(withJSONObject: value))
}
private func editJSON(_ root: Any, path: [Any], operation: String, replacement: Any?) -> Any {
  guard let head = path.first else { return replacement! }
  let tail = Array(path.dropFirst())
  if var object = root as? JSON, let key = head as? String {
    if tail.isEmpty {
      if operation == "remove" {
        object.removeValue(forKey: key)
      } else if operation == "append" {
        var array = object[key] as! [Any]
        array.append(replacement!)
        object[key] = array
      } else {
        object[key] = replacement!
      }
    } else {
      object[key] = editJSON(
        object[key]!, path: tail, operation: operation, replacement: replacement)
    }
    return object
  }
  var array = root as! [Any]
  let indices: [Int] =
    head as? String == "*"
    ? Array(array.indices)
    : (head as? [NSNumber])?.map(\.intValue) ?? [(head as! NSNumber).intValue]
  for index in indices.reversed() {
    if tail.isEmpty {
      if operation == "remove" {
        array.remove(at: index)
      } else if operation == "append" {
        var nested = array[index] as! [Any]
        nested.append(replacement!)
        array[index] = nested
      } else {
        array[index] = replacement!
      }
    } else {
      array[index] = editJSON(
        array[index], path: tail, operation: operation, replacement: replacement)
    }
  }
  return array
}
private func expandCapability(_ templates: JSON, _ spec: JSON) -> JSON {
  var value = cloneJSON(templates[spec["template"] as! String]!)
  for edit in spec["edits"] as! [JSON] {
    value = editJSON(
      value, path: edit["path"] as! [Any], operation: edit["op"] as? String ?? "replace",
      replacement: edit["value"])
  }
  return value as! JSON
}

@Test func rangeInspectionCorpusIsExact() throws {
  let corpus = try sharedJSON("inspection/v1/fixtures.json")
  let cases = corpus["cases"] as! [JSON]
  #expect(cases.count == 9)
  for item in cases {
    let options =
      ((item["options"] as? JSON)?["resistanceFormat"] as? String) == "signed16Tenths"
      ? RangeFormatOptions(resistance: .sint16Tenths) : .init()
    let actual = inspectRange(
      rangeKind(item["kind"] as! String), bytes: bytes(item), options: options)
    let expected = item["expected"] as! JSON
    func valueJSON(_ value: SupportedRange?) -> Any {
      guard let value else { return NSNull() }
      let name: String
      let unit: Int
      let divisor: Int
      switch value.kind {
      case .speed: (name, unit, divisor) = ("speed", 0, 100)
      case .inclination: (name, unit, divisor) = ("inclination", 1, 10)
      case .resistance:
        (name, unit, divisor) = ("resistance", 2, value.format.resistance == .sint16Tenths ? 10 : 1)
      case .heartRate: (name, unit, divisor) = ("heartRate", 3, 1)
      case .power: (name, unit, divisor) = ("power", 4, 1)
      }
      return [
        "kind": name, "minimum": value.minimum, "maximum": value.maximum,
        "increment": value.increment, "scaleDivisor": divisor, "unit": unit,
      ] as JSON
    }
    let complete: JSON = [
      "selectedProfile": actual.selectedProfile.rawValue, "actualLength": actual.actualLength,
      "expectedLength": actual.expectedLength, "status": actual.status.rawValue,
      "value": valueJSON(actual.value),
      "candidates": actual.candidates.map { candidate -> JSON in
        [
          "profile": candidate.profile.rawValue, "expectedLength": candidate.expectedLength,
          "status": candidate.status.rawValue, "value": valueJSON(candidate.value),
        ]
      },
    ]
    #expect(exactJSONEqual(complete, expected))
    let candidates = expected["candidates"] as! [JSON]
    #expect(actual.candidates.count == candidates.count)
    for (candidate, wanted) in zip(actual.candidates, candidates) {
      #expect(candidate.profile.rawValue == wanted["profile"] as! String)
      #expect(candidate.expectedLength == (wanted["expectedLength"] as! NSNumber).intValue)
      #expect(candidate.status.rawValue == wanted["status"] as! String)
      let v = wanted["value"]
      #expect((candidate.value == nil) == (v is NSNull))
      if let value = candidate.value, let wanted = v as? JSON {
        #expect(value.minimum == (wanted["minimum"] as! NSNumber).int32Value)
        #expect(value.maximum == (wanted["maximum"] as! NSNumber).int32Value)
        #expect(value.increment == (wanted["increment"] as! NSNumber).int32Value)
        #expect(value.kind == rangeKind(wanted["kind"] as! String))
        let divisor =
          candidate.profile == .uint16Hundredths
          ? 100 : candidate.profile == .signed16Tenths ? 10 : 1
        #expect(divisor == (wanted["scaleDivisor"] as! NSNumber).intValue)
        let unit =
          value.kind == .speed
          ? 0
          : value.kind == .inclination
            ? 1 : value.kind == .resistance ? 2 : value.kind == .heartRate ? 3 : 4
        #expect(unit == (wanted["unit"] as! NSNumber).intValue)
      }
    }
    nativeCaseExecuted("inspection-v1", "cases", item["id"] as! String)
  }
}

@Test func capabilityCorpusIsExact() throws {
  let corpus = try sharedJSON("capabilities/v1/vectors.json")
  let templates = corpus["snapshots"] as! JSON
  let reports = corpus["reports"] as! JSON
  let cases = corpus["cases"] as! [JSON]
  #expect(cases.count == 63)
  var ids = Set<String>()
  var categoryCounts: [String: Int] = [:]
  for item in cases {
    #expect(ids.insert(item["id"] as! String).inserted)
    let input = expandCapability(templates, item["input"] as! JSON)
    let expected = expandCapability(reports, item["expected"] as! JSON)
    let actual = reportJSON(try evaluateCapabilities(capabilitySnapshot(input)))
    #expect(exactJSONEqual(actual, expected))
    let category = item["category"] as! String
    categoryCounts[category, default: 0] += 1
    nativeCaseExecuted("capabilities-v1", category, item["id"] as! String)
  }
  #expect(
    categoryCounts == [
      "discovery": 12, "duplicates": 3, "features": 5, "forward-compatibility": 2,
      "measurements": 7, "operations": 4, "properties": 22, "ranges": 8,
    ])
}

@Test func codecV1CorpusIsCompleteAndExact() throws {
  let schema = try sharedJSON("v1/schema.json")
  let corpus = try sharedJSON("v1/vectors.json")
  #expect(
    (schema["$id"] as? String)
      == "https://raw.githubusercontent.com/deancochran/ftms/v0.2.0/conformance/v1/schema.json")
  #expect((corpus["schemaVersion"] as? NSNumber)?.intValue == 1)
  var ids = Set<String>()
  var total = 0
  for (category, count) in expectedCounts {
    let cases = corpus[category] as! [JSON]
    #expect(cases.count == count)
    total += cases.count
    for vector in cases { #expect(ids.insert(vector["id"] as! String).inserted) }
  }
  #expect(total == 97)

  for vector in corpus["features"] as! [JSON] {
    let actual = normalizedFeatures(try decodeFeatures(bytes(vector)))
    if let expected = vector["expected"] as? JSON {
      #expect(actual.count == expected.count)
      for (name, value) in expected { #expect(actual[name] == (value as! Bool)) }
    } else {
      let trueNames = Set(actual.compactMap { $0.value ? $0.key : nil })
      #expect(trueNames == Set(vector["expectedTrue"] as! [String]))
    }
    nativeCaseExecuted("codec-v1", "features", vector["id"] as! String)
  }
  for vector in corpus["ranges"] as! [JSON] {
    let range = rangeKind(vector["kind"] as! String)
    if let expected = vector["expected"] as? JSON {
      let actual = normalizeRange(try decodeRange(range, bytes: bytes(vector)))
      #expect(actual.min == (expected["min"] as! NSNumber).doubleValue)
      #expect(actual.max == (expected["max"] as! NSNumber).doubleValue)
      #expect(actual.increment == (expected["increment"] as! NSNumber).doubleValue)
      #expect(actual.unit == expected["unit"] as! String)
    } else {
      #expect(throws: FTMSCodecError.self) { try decodeRange(range, bytes: bytes(vector)) }
    }
    nativeCaseExecuted("codec-v1", "ranges", vector["id"] as! String)
  }
  for vector in corpus["controls"] as! [JSON] {
    #expect(try encodeV1Control(vector["request"] as! JSON) == bytes(vector, key: "expectedBytes"))
    nativeCaseExecuted("codec-v1", "controls", vector["id"] as! String)
  }
  for vector in corpus["controlResponses"] as! [JSON] {
    if let expected = vector["expected"] as? JSON {
      let response = try decodeValidatedControlResponse(bytes(vector))
      let adapted = v1ResponseResult { response }
      #expect(exactJSONEqual(adapted["value"]!, expected))
      if !response.unknownResult { #expect(try encodeControlResponse(response) == bytes(vector)) }
    } else {
      let adapted = v1ResponseResult { try decodeValidatedControlResponse(bytes(vector)) }
      #expect(exactJSONEqual(adapted["error"]!, ["code": vector["expectedError"] as! String]))
    }
    nativeCaseExecuted("codec-v1", "controlResponses", vector["id"] as! String)
  }
  for vector in corpus["measurements"] as! [JSON] {
    let measurement = try decodeMeasurement(
      kind(vector["characteristicUuid"] as! String), bytes: bytes(vector))
    let actual = normalizeMeasurement(measurement)
    for (name, expected) in vector["expectedMetrics"] as! JSON {
      assertMetric(actual[name], expected)
    }
    #expect(try encodeMeasurement(measurement) == bytes(vector))
    nativeCaseExecuted("codec-v1", "measurements", vector["id"] as! String, directions: 2)
  }
  for vector in corpus["statuses"] as! [JSON] {
    assertStatus(vector)
    nativeCaseExecuted("codec-v1", "statuses", vector["id"] as! String, directions: 2)
  }
  for vector in corpus["diagnostics"] as! [JSON] {
    assertDiagnostics(vector)
    nativeCaseExecuted("codec-v1", "diagnostics", vector["id"] as! String)
  }
}

private func assertMetric(_ actual: NormalizedMetricValue?, _ expected: Any) {
  if let expected = expected as? String {
    #expect(actual == .direction(MeasurementDirection(rawValue: expected)!))
    return
  }
  guard case let .number(value)? = actual else {
    Issue.record("missing numeric normalized metric")
    return
  }
  if expected is NSNull {
    #expect(value == nil)
  } else if let value {
    #expect(abs(value - (expected as! NSNumber).doubleValue) < 0.005)
  } else {
    Issue.record("missing normalized metric")
  }
}
private func assertStatus(_ vector: JSON) {
  let uuid = vector["characteristicUuid"] as! String
  let expected = vector["expectedStatus"] as! JSON
  if uuid.hasPrefix("00002ad3") {
    let value = decodeTrainingStatus(bytes(vector))
    #expect(Int(value.code) == (expected["code"] as! NSNumber).intValue)
    #expect(trainingStatusLabel(value.code) == expected["label"] as! String)
    let details = expected["details"] as! JSON
    #expect(Int(value.flags) == (details["flags"] as! NSNumber).intValue)
    #expect(value.text == details["trainingStatusString"] as? String)
    #expect(try! encodeTrainingStatus(value) == bytes(vector))
  } else {
    let value = decodeMachineStatus(bytes(vector))
    #expect(Int(value.opcode) == (expected["code"] as! NSNumber).intValue)
    #expect(machineStatusLabel(value.opcode) == expected["label"] as! String)
    let details = expected["details"] as! JSON
    switch details["kind"] as! String {
    case "speed":
      #expect(Double(value.operands[0]) / 100 == (details["speedKph"] as! NSNumber).doubleValue)
    case "simulation":
      #expect(
        Double(value.operands[0]) / 1000 == (details["windSpeedMps"] as! NSNumber).doubleValue)
      #expect(Double(value.operands[1]) / 100 == (details["gradePercent"] as! NSNumber).doubleValue)
      #expect(Double(value.operands[2]) / 10000 == (details["crr"] as! NSNumber).doubleValue)
      #expect(Double(value.operands[3]) / 100 == (details["cwKgPerM"] as! NSNumber).doubleValue)
    default: #expect(value.operands.isEmpty)
    }
    #expect(try! encodeMachineStatus(value) == bytes(vector))
  }
}

private func expectedError(_ operation: () throws -> Void) -> String? {
  do {
    try operation()
    return nil
  } catch let error as FTMSCodecError {
    switch error {
    case .length: return "length"
    case .kind: return "kind"
    case .range: return "range"
    default: return "malformed"
    }
  } catch { return "other" }
}

/// codec-v1 calls every rejected response `malformed_response`; the raw Swift
/// codec keeps its more specific error enum, so this adapter is explicit.
private func v1ResponseResult(_ operation: () throws -> ControlResponse) -> JSON {
  do {
    let response = try operation()
    let names = [
      1: "success", 2: "not_supported", 3: "invalid_parameter", 4: "operation_failed",
      5: "control_not_permitted",
    ]
    let parameter: JSON =
      response.spinDownSpeeds.map {
        [
          "kind": "spin_down_speeds", "targetSpeedLowKph": Int($0.0) / 100,
          "targetSpeedHighKph": Int($0.1) / 100,
        ]
      } ?? ["kind": "none"]
    return [
      "ok": true,
      "value": [
        "requestOpCode": Int(response.requestOpcode),
        "resultCode": Int(response.resultCode),
        "resultCodeName": names[Int(response.resultCode)]
          ?? String(format: "unknown_0x%02x", response.resultCode),
        "success": response.resultCode == 1, "parameter": parameter,
        "issues": response.unknownResult ? ["reserved_value"] : [],
      ],
    ]
  } catch is FTMSCodecError {
    return ["ok": false, "error": ["code": "malformed_response"]]
  } catch {
    return ["ok": false, "error": ["code": "unexpected"]]
  }
}

private func rawResponseJSON(_ value: ControlResponse) -> JSON {
  [
    "requestOpcode": Int(value.requestOpcode), "resultCode": Int(value.resultCode),
    "parameter": value.spinDownSpeeds == nil ? 0 : 1,
    "low": value.spinDownSpeeds.map { Int($0.0) } ?? 0,
    "high": value.spinDownSpeeds.map { Int($0.1) } ?? 0,
    "unknownRequest": value.unknownRequest ? 1 : 0,
    "unknownResult": value.unknownResult ? 1 : 0,
    "unexpectedParameters": value.unexpectedParameters ? 1 : 0,
  ]
}

private func machineStatusJSON(_ value: MachineStatus) -> JSON {
  let action = (value.opcode == 2 || value.opcode == 20) ? Int(value.operands.first ?? 0) : 0
  let parameter: Any =
    !value.diagnostics.truncated
      && (value.opcode >= 5 && value.opcode != 20 && value.opcode <= 21)
    ? [
      "opcode": Int(
        value.opcode == 21 ? 20 : value.opcode <= 9 ? value.opcode - 3 : value.opcode - 1),
      "operands": value.operands.map(Int.init),
    ] : NSNull()
  return [
    "opcode": Int(value.opcode), "action": action, "parameter": parameter,
    "unknownOpcode": value.diagnostics.issues.contains("unknown_opcode") ? 1 : 0,
    "reservedValue": value.diagnostics.issues.contains("reserved_value") ? 1 : 0,
    "truncated": value.diagnostics.truncated ? 1 : 0,
    "trailingBytes": value.diagnostics.trailingBytes ? 1 : 0,
  ]
}

private func trainingStatusJSON(_ value: TrainingStatus, wire: [UInt8]) -> JSON {
  let present = !value.diagnostics.truncated && value.flags & 1 != 0
  let textBytes = present ? Array(wire.dropFirst(2)) : []
  return [
    "flags": Int(value.flags), "code": Int(value.code),
    "textOffset": present ? 2 : 0,
    "textSize": present ? textBytes.count : 0,
    "textPresent": present ? 1 : 0,
    "extendedString": value.flags & 2 != 0 ? 1 : 0,
    "reservedFlags": Int(value.flags & ~3),
    "reservedValue": value.diagnostics.issues.contains("reserved_value") ? 1 : 0,
    "invalidFlags": value.diagnostics.issues.contains("invalid_flags") ? 1 : 0,
    "invalidUtf8": value.diagnostics.issues.contains("invalid_utf8") ? 1 : 0,
    "truncated": value.diagnostics.truncated ? 1 : 0,
    "trailingBytes": value.diagnostics.trailingBytes ? 1 : 0,
    "textHex": present ? textBytes.map { String(format: "%02x", $0) }.joined() : "",
  ]
}

@Test func rawControlCorpusDecodesEncodesAndPreservesReservedResponseRules() throws {
  let corpus = try sharedJSON("controls/v1/vectors.json")
  for vector in corpus["requests"] as! [JSON] {
    let options =
      (vector["format"] as? String) == "uint8Tenths"
      ? ControlFormatOptions(resistance: .uint8Tenths) : .init()
    let decoded = try decodeControlRequest(bytes(vector), options: options)
    let wanted = vector["decoded"] as! JSON
    #expect(Int(decoded.opcode) == (wanted["opcode"] as! NSNumber).intValue)
    #expect(decoded.operands == (wanted["operands"] as! [NSNumber]).map(\.int32Value))
    #expect(try encodeControlRequest(decoded, options: options) == bytes(vector))
    nativeCaseExecuted("controls-v1", "requests", vector["id"] as! String, directions: 2)
  }
  for vector in corpus["responses"] as! [JSON] {
    let decoded = try decodeControlResponse(
      bytes(vector), options: .init(allowDiagnosticTrailing: true))
    let wanted = vector["decoded"] as! JSON
    #expect(exactJSONEqual(rawResponseJSON(decoded), wanted))
    if vector["encode"] as? Bool != false {
      #expect(try encodeControlResponse(decoded) == bytes(vector))
    }
    nativeCaseExecuted(
      "controls-v1", "responses", vector["id"] as! String,
      directions: vector["encode"] as? Bool == false ? 1 : 2)
  }
  for vector in corpus["invalid"] as! [JSON] {
    let options =
      (vector["format"] as? String) == "uint8Tenths"
      ? ControlFormatOptions(resistance: .uint8Tenths) : .init()
    let actual =
      vector["operation"] as! String == "request"
      ? expectedError { _ = try decodeControlRequest(bytes(vector), options: options) }
      : expectedError { _ = try decodeControlResponse(bytes(vector)) }
    #expect(actual == vector["error"] as? String)
    nativeCaseExecuted("controls-v1", "invalid", vector["id"] as! String)
  }
  // Unknown requests are representable only as Not Supported responses.
  #expect(
    try encodeControlResponse(.init(requestOpcode: 250, resultCode: 2, unknownRequest: true)) == [
      0x80, 250, 2,
    ])
  #expect(
    expectedError {
      _ = try encodeControlResponse(.init(requestOpcode: 250, resultCode: 1, unknownRequest: true))
    } == "range")
}

@Test func machineStatusUsesItsOwnFixedLayouts() throws {
  let signedResistance = [UInt8(7), 0xf9, 0xff]
  let decoded = decodeMachineStatus(signedResistance, options: .init(resistance: .uint8Tenths))
  #expect(decoded.operands == [-7])
  #expect(
    try encodeMachineStatus(decoded, options: .init(resistance: .uint8Tenths)) == signedResistance)
  for action: UInt8 in 1...4 {
    let status = decodeMachineStatus([20, action])
    #expect(status.diagnostics.issues.isEmpty)
    #expect(try encodeMachineStatus(status) == [20, action])
  }
  #expect(decodeMachineStatus([20, 5]).diagnostics.issues == ["reserved_value"])
  #expect(expectedError { _ = try decodeControlRequest([19, 3]) } == "range")
}

@Test func rawStatusCorpusRunsEveryMachineAndTrainingVector() throws {
  let corpus = try sharedJSON("statuses/v1/vectors.json")
  for vector in corpus["machine"] as! [JSON] {
    let value = decodeMachineStatus(bytes(vector))
    let expected = vector["decoded"] as! JSON
    #expect(exactJSONEqual(machineStatusJSON(value), expected))
    if vector["encode"] as! Bool { #expect(try encodeMachineStatus(value) == bytes(vector)) }
    nativeCaseExecuted(
      "statuses-v1", "machine", vector["id"] as! String,
      directions: vector["encode"] as! Bool ? 2 : 1)
  }
  for vector in corpus["training"] as! [JSON] {
    let value = decodeTrainingStatus(bytes(vector))
    let expected = vector["decoded"] as! JSON
    #expect(exactJSONEqual(trainingStatusJSON(value, wire: bytes(vector)), expected))
    if vector["encode"] as! Bool { #expect(try encodeTrainingStatus(value) == bytes(vector)) }
    nativeCaseExecuted(
      "statuses-v1", "training", vector["id"] as! String,
      directions: vector["encode"] as! Bool ? 2 : 1)
  }
}

@Test func normalizedMeasurementCarriesDirectionAndFormatProvenance() throws {
  for (flag, direction) in [(UInt32(0), MeasurementDirection.forward), (UInt32(0x8000), .backward)]
  {
    let source = Measurement(
      kind: .crossTrainer, flags: flag, values: [.speed: 360], format: .init())
    let actual = normalizeMeasurement(
      try decodeMeasurement(.crossTrainer, bytes: encodeMeasurement(source)))
    #expect(actual["movementDirection"] == .direction(direction))
  }
  let legacy = Measurement(
    kind: .treadmill, flags: 1 << 5, values: [.speed: 360, .instantaneousPace: 12],
    format: .init(treadmillPace: .uint8Legacy))
  let decoded = try decodeMeasurement(
    .treadmill, bytes: encodeMeasurement(legacy, options: legacy.format), options: legacy.format)
  #expect(normalizeMeasurement(decoded)["instantaneousPaceSecondsPer500m"] == .number(nil))
}
private func assertDiagnostics(_ vector: JSON) {
  let uuid = vector["characteristicUuid"] as! String
  let wire = bytes(vector)
  if uuid.hasPrefix("00002ac") || uuid.hasPrefix("00002ad0") || uuid.hasPrefix("00002ad1")
    || uuid.hasPrefix("00002ad2")
  {
    let measurement = try! decodeMeasurement(kind(uuid), bytes: wire)
    #expect(measurement.diagnostics.truncated == vector["expectedTruncated"] as! Bool)
    for issue in vector["expectedIssues"] as! [String] {
      #expect(measurement.diagnostics.issues.contains(issue))
    }
    for (name, expected) in (vector["expectedMetrics"] as? JSON ?? [:]) {
      assertMetric(normalizeMeasurement(measurement)[name] ?? nil, expected)
    }
  } else if uuid.hasPrefix("00002ad3") {
    let value = decodeTrainingStatus(wire)
    #expect(value.diagnostics.truncated == vector["expectedTruncated"] as! Bool)
    for issue in vector["expectedIssues"] as! [String] {
      #expect(value.diagnostics.issues.contains(issue))
    }
    #expect(
      (vector["expectedStatusCode"] is NSNull)
        || Int(value.code) == (vector["expectedStatusCode"] as! NSNumber).intValue)
  } else {
    let value = decodeMachineStatus(wire)
    #expect(value.diagnostics.truncated == vector["expectedTruncated"] as! Bool)
    for issue in vector["expectedIssues"] as! [String] {
      #expect(value.diagnostics.issues.contains(issue))
    }
    if !(vector["expectedStatusCode"] is NSNull) {
      #expect(Int(value.opcode) == (vector["expectedStatusCode"] as! NSNumber).intValue)
    }
  }
}

private func encodeV1Control(_ request: JSON) throws -> [UInt8] {
  let op = request["op"] as! String
  let operands: [Int32] =
    switch op {
    case "requestControl", "reset", "startResume": []
    case "setTargetSpeed": [Int32((request["speedKph"] as! NSNumber).doubleValue * 100)]
    case "setTargetInclination":
      [Int32((request["inclinationPercent"] as! NSNumber).doubleValue * 10)]
    case "setTargetResistance": [Int32((request["resistanceLevel"] as! NSNumber).doubleValue * 10)]
    case "setTargetPower": [(request["powerWatts"] as! NSNumber).int32Value]
    case "setTargetHeartRate": [(request["heartRateBpm"] as! NSNumber).int32Value]
    case "stopPause": [request["action"] as! String == "stop" ? 1 : 2]
    case "setTargetedExpendedEnergy": [(request["energyKcal"] as! NSNumber).int32Value]
    case "setTargetedSteps": [(request["steps"] as! NSNumber).int32Value]
    case "setTargetedStrides": [(request["strides"] as! NSNumber).int32Value]
    case "setTargetedDistance": [(request["distanceMeters"] as! NSNumber).int32Value]
    case "setTargetedTrainingTime": [(request["seconds"] as! NSNumber).int32Value]
    case "setTargetedTimeTwoHrZones", "setTargetedTimeThreeHrZones", "setTargetedTimeFiveHrZones":
      (request["seconds"] as! [NSNumber]).map(\.int32Value)
    case "setIndoorBikeSimulation":
      [
        Int32((request["windSpeedMps"] as! NSNumber).doubleValue * 1000),
        Int32((request["gradePercent"] as! NSNumber).doubleValue * 100),
        Int32((request["crr"] as! NSNumber).doubleValue * 10000),
        Int32((request["cwKgPerM"] as! NSNumber).doubleValue * 100),
      ]
    case "setWheelCircumference": [(request["circumferenceMm"] as! NSNumber).int32Value * 10]
    case "spinDown": [request["action"] as! String == "start" ? 1 : 2]
    default: [Int32((request["cadenceRpm"] as! NSNumber).doubleValue * 2)]
    }
  let opcode = [
    "requestControl": 0, "reset": 1, "setTargetSpeed": 2, "setTargetInclination": 3,
    "setTargetResistance": 4, "setTargetPower": 5, "setTargetHeartRate": 6, "startResume": 7,
    "stopPause": 8, "setTargetedExpendedEnergy": 9, "setTargetedSteps": 10,
    "setTargetedStrides": 11, "setTargetedDistance": 12, "setTargetedTrainingTime": 13,
    "setTargetedTimeTwoHrZones": 14, "setTargetedTimeThreeHrZones": 15,
    "setTargetedTimeFiveHrZones": 16, "setIndoorBikeSimulation": 17, "setWheelCircumference": 18,
    "spinDown": 19, "setTargetedCadence": 20,
  ][op]!
  return try encodeControlRequest(ControlRequest(opcode: UInt8(opcode), operands: operands))
}

@Test func rawValuesAndControlsCompareEntireValues() throws {
  let values = try sharedJSON("values/v1/vectors.json")["cases"] as! [JSON]
  #expect(values.count == 8)
  for vector in values {
    if vector["operation"] as! String == "features" {
      let value = Features(
        machineRaw: (vector["machine"] as! NSNumber).uint32Value,
        targetRaw: (vector["target"] as! NSNumber).uint32Value)
      #expect(encodeFeatures(value) == bytes(vector, key: "expectedBytes"))
      #expect(try decodeFeatures(bytes(vector, key: "expectedBytes")) == value)
      nativeCaseExecuted("values-v1", "cases", vector["id"] as! String, directions: 2)
    } else {
      let range = SupportedRange(
        kind: rangeKind(vector["kind"] as! String),
        minimum: (vector["minimum"] as! NSNumber).int32Value,
        maximum: (vector["maximum"] as! NSNumber).int32Value,
        increment: (vector["increment"] as! NSNumber).int32Value)
      let wire = bytes(vector, key: "expectedBytes")
      #expect(try encodeRange(range) == wire)
      #expect(try decodeRange(range.kind, bytes: wire) == range)
      nativeCaseExecuted("values-v1", "cases", vector["id"] as! String, directions: 2)
    }
  }
}
