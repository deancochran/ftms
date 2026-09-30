import FTMS
import Foundation
import Testing

/// Canonical `ftms:measurements:conformance:v1` adapter. Expectations below
/// come exclusively from the shared fixture; this test never derives them by
/// re-encoding or re-decoding a production model.
private typealias RawMeasurementJSON = [String: Any]

private let rawMeasurementFields: [String: MeasurementField] = [
  "speed": .speed,
  "averageSpeed": .averageSpeed,
  "distance": .distance,
  "inclination": .inclination,
  "rampAngle": .rampAngle,
  "positiveElevation": .positiveElevation,
  "negativeElevation": .negativeElevation,
  "instantaneousPace": .instantaneousPace,
  "averagePace": .averagePace,
  "energy": .totalEnergy,
  "energyPerHour": .energyPerHour,
  "energyPerMinute": .energyPerMinute,
  "heartRate": .heartRate,
  "met": .metabolicEquivalent,
  "elapsed": .elapsedTime,
  "remaining": .remainingTime,
  "force": .forceOnBelt,
  "power": .power,
  "stepRate": .stepRate,
  "averageStepRate": .averageStepRate,
  "strideCount": .strideCount,
  "resistance": .resistance,
  "averagePower": .averagePower,
  "floorCount": .floorCount,
  "stepCount": .stepCount,
  "strokeRate": .strokeRate,
  "strokeCount": .strokeCount,
  "averageStrokeRate": .averageStrokeRate,
  "cadence": .cadence,
  "averageCadence": .averageCadence,
]

private func rawMeasurementCorpus(_ name: String) throws -> RawMeasurementJSON {
  let source = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
    .appendingPathComponent("../../../../shared/conformance/measurements/v1/\(name)")
    .standardized
  return try JSONSerialization.jsonObject(with: Data(contentsOf: source)) as! RawMeasurementJSON
}

private func rawMeasurementBytes(_ item: RawMeasurementJSON) -> [UInt8] {
  (item["bytes"] as! [NSNumber]).map(\.uint8Value)
}

private func rawMeasurementError(_ code: Int, operation: () throws -> Void) {
  let expected: FTMSCodecError =
    switch code {
    case 2: .length
    case 3: .kind
    case 4: .range
    default: fatalError("Unsupported fixture error code \(code)")
    }
  #expect(throws: expected) { try operation() }
}

private func expectedRawMeasurement(
  _ decoded: RawMeasurementJSON, fieldOrder: [String]
) throws -> FTMS.Measurement {
  let kind = try #require(MeasurementKind(rawValue: (decoded["kind"] as! NSNumber).uint8Value))
  let flags = (decoded["flags"] as! NSNumber).uint32Value
  let present = (decoded["present"] as! NSNumber).uint32Value
  let unavailable = (decoded["unavailable"] as! NSNumber).uint32Value
  let values = decoded["values"] as! [NSNumber]
  try #require(values.count == fieldOrder.count)
  try #require(unavailable & ~present == 0)

  var modelValues: [MeasurementField: Int32] = [:]
  var modelUnavailable = Set<MeasurementField>()
  for (index, name) in fieldOrder.enumerated() where present & (1 << UInt32(index)) != 0 {
    let field = try #require(rawMeasurementFields[name])
    if unavailable & (1 << UInt32(index)) != 0 {
      modelUnavailable.insert(field)
    } else {
      modelValues[field] = values[index].int32Value
    }
  }
  return FTMS.Measurement(
    kind: kind, flags: flags, values: modelValues, unavailable: modelUnavailable,
    bytesRead: (decoded["bytesRead"] as! NSNumber).intValue)
}

private func assertRawMeasurement(
  _ actual: FTMS.Measurement, expected: FTMS.Measurement, decoded: RawMeasurementJSON
) {
  #expect(actual.kind == expected.kind)
  #expect(actual.flags == expected.flags)
  #expect(actual.values == expected.values)
  #expect(actual.unavailable == expected.unavailable)
  #expect(actual.bytesRead == expected.bytesRead)
  #expect(actual.moreData == ((decoded["moreData"] as! NSNumber).intValue == 1))
  #expect(actual.backward == ((decoded["backward"] as! NSNumber).intValue == 1))
  #expect(actual.diagnostics.truncated == ((decoded["truncated"] as! NSNumber).intValue == 1))
  #expect(
    actual.diagnostics.trailingBytes == ((decoded["trailingBytes"] as! NSNumber).intValue == 1))
  #expect(
    actual.diagnostics.reservedFlags == ((decoded["reservedFlags"] as! NSNumber).intValue == 1))
}

@Test("raw measurement corpus v1 executes all declared directions")
func rawMeasurementCorpusV1() throws {
  let schema = try rawMeasurementCorpus("schema.json")
  let corpus = try rawMeasurementCorpus("vectors.json")
  #expect(schema["$id"] as? String == "urn:ftms:measurements:conformance:v1")
  #expect((corpus["schemaVersion"] as? NSNumber)?.intValue == 1)
  #expect(
    corpus["specificationBasis"] as? String
      == "FTMS 1.0 measurement notifications; ESR11 signed fields")

  let fieldOrder = corpus["fieldOrder"] as! [String]
  #expect(fieldOrder.count == 30)
  #expect(Set(fieldOrder).count == fieldOrder.count)
  #expect(Set(fieldOrder) == Set(rawMeasurementFields.keys))

  let cases = corpus["cases"] as! [RawMeasurementJSON]
  #expect(cases.count == 26)
  var ids = Set<String>()
  var directions = 0
  for item in cases {
    #expect(ids.insert(item["id"] as! String).inserted)
    directions += 1
    let decoded = item["decoded"] as! RawMeasurementJSON
    let wire = rawMeasurementBytes(item)
    let kindValue = (item["kind"] as! NSNumber).intValue
    if let error = decoded["error"] as? NSNumber {
      rawMeasurementError(error.intValue) {
        guard let kind = MeasurementKind(rawValue: UInt8(exactly: kindValue) ?? 255) else {
          throw FTMSCodecError.kind
        }
        _ = try decodeMeasurement(kind, bytes: wire)
      }
      nativeCaseExecuted("measurements-v1", "cases", item["id"] as! String)
      continue
    }

    let kind = try #require(MeasurementKind(rawValue: UInt8(kindValue)))
    let expected = try expectedRawMeasurement(decoded, fieldOrder: fieldOrder)
    let actual = try decodeMeasurement(kind, bytes: wire)
    assertRawMeasurement(actual, expected: expected, decoded: decoded)
    if item["encode"] as! Bool {
      #expect(try encodeMeasurement(expected) == wire)
      directions += 1
    }
    nativeCaseExecuted(
      "measurements-v1", "cases", item["id"] as! String,
      directions: (item["encode"] as! Bool) ? 2 : 1)
  }
  #expect(ids.count == 26)
  #expect(directions == 47)
}
