import FTMS
import Foundation
import Testing

/// Structural oracle for `ftms-measurement-matrix-v1`.
///
/// This deliberately builds wire bytes and the public Swift model from the
/// shared declaration.  It does not use the production codec's private field
/// table, and therefore an encode/decode round trip alone cannot make a case
/// pass.
private typealias MatrixJSON = [String: Any]

private struct MatrixField {
  let bit: Int
  let width: Int
  let index: Int
  let signed: Bool
  let sentinel: Bool
}

private struct MatrixLayout {
  let kind: MeasurementKind
  let flagBytes: Int
  let optionalGroups: Int
  let fullLength: Int
  let fields: [MatrixField]
}

private func matrixLayouts() throws -> [MatrixLayout] {
  let source = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
    .appendingPathComponent("../../../../shared/conformance/measurement-matrix/v1/layouts.json")
    .standardized
  let object = try JSONSerialization.jsonObject(with: Data(contentsOf: source)) as! MatrixJSON
  try #require(object["contract"] as? String == "ftms-measurement-matrix-v1")
  try #require(
    object["columns"] as? [String] == [
      "flagBit", "width", "rawFieldIndex", "signed", "unavailableSentinel",
    ])
  return try (object["layouts"] as! [MatrixJSON]).map { layout in
    let kind = try #require(MeasurementKind(rawValue: (layout["kind"] as! NSNumber).uint8Value))
    return MatrixLayout(
      kind: kind, flagBytes: (layout["flagBytes"] as! NSNumber).intValue,
      optionalGroups: (layout["optionalGroups"] as! NSNumber).intValue,
      fullLength: (layout["fullLength"] as! NSNumber).intValue,
      fields: (layout["fields"] as! [[NSNumber]]).map {
        MatrixField(
          bit: $0[0].intValue, width: $0[1].intValue, index: $0[2].intValue,
          signed: $0[3].boolValue, sentinel: $0[4].boolValue)
      })
  }
}

private func matrixOptions(kind: MeasurementKind, variant: Int) -> MeasurementFormatOptions {
  MeasurementFormatOptions(
    resistance: variant == 1 && kind != .treadmill ? .sint16Tenths : .uint8Whole,
    treadmillPace: variant == 1 && kind == .treadmill ? .uint8Legacy : .uint16)
}

private func matrixFields(_ layout: MatrixLayout, variant: Int) -> [MatrixField] {
  layout.fields.map { field in
    if variant == 1 && field.index == MeasurementField.resistance.rawValue {
      return MatrixField(
        bit: field.bit, width: 2, index: field.index, signed: true, sentinel: field.sentinel)
    }
    if variant == 1 && layout.kind == .treadmill
      && (field.index == MeasurementField.instantaneousPace.rawValue
        || field.index == MeasurementField.averagePace.rawValue)
    {
      return MatrixField(
        bit: field.bit, width: 1, index: field.index, signed: field.signed, sentinel: field.sentinel
      )
    }
    return field
  }
}

private func isPresent(_ bit: Int, flags: UInt32) -> Bool {
  bit == 0 ? flags & 1 == 0 : flags & (1 << UInt32(bit)) != 0
}

private func matrixBytes(_ value: Int32, width: Int) -> [UInt8] {
  let raw = UInt32(bitPattern: value)
  return (0..<width).map { UInt8(truncatingIfNeeded: raw >> UInt32($0 * 8)) }
}

private func matrixCase(
  _ layout: MatrixLayout, variant: Int, flags: UInt32, sentinelIndex: Int? = nil
) -> (wire: [UInt8], expected: FTMS.Measurement) {
  let fields = matrixFields(layout, variant: variant)
  var wire = (0..<layout.flagBytes).map { UInt8(truncatingIfNeeded: flags >> UInt32($0 * 8)) }
  var values: [MeasurementField: Int32] = [:]
  var unavailable = Set<MeasurementField>()
  for field in fields where isPresent(field.bit, flags: flags) {
    let key = MeasurementField(rawValue: field.index)!
    let isSentinel = key.rawValue == sentinelIndex
    let value: Int32
    if isSentinel {
      value = field.signed ? 32767 : Int32((1 << (field.width * 8)) - 1)
      unavailable.insert(key)
    } else {
      value = Int32(field.index + 1) * (field.signed ? -1 : 1)
      values[key] = value
    }
    wire += matrixBytes(value, width: field.width)
  }
  return (
    wire,
    FTMS.Measurement(
      kind: layout.kind, flags: flags, values: values, unavailable: unavailable,
      bytesRead: wire.count, format: matrixOptions(kind: layout.kind, variant: variant))
  )
}

private func assertMatrixDecode(_ actual: FTMS.Measurement, expected: FTMS.Measurement) {
  #expect(actual.kind == expected.kind)
  #expect(actual.flags == expected.flags)
  #expect(actual.values == expected.values)
  #expect(actual.unavailable == expected.unavailable)
  #expect(actual.bytesRead == expected.bytesRead)
  #expect(!actual.diagnostics.truncated)
  #expect(!actual.diagnostics.trailingBytes)
  #expect(!actual.diagnostics.reservedFlags)
}

@Test("measurement matrix v1 exhaustively checks independently generated layouts")
func measurementMatrixV1() throws {
  var structural = 0
  var sentinels = 0
  var reserved = 0
  var prefixes = 0

  for layout in try matrixLayouts() {
    let variants = [.treadmill, .crossTrainer, .rower, .indoorBike].contains(layout.kind) ? 2 : 1
    for variant in 0..<variants {
      let options = matrixOptions(kind: layout.kind, variant: variant)
      for subset in 0..<(1 << layout.optionalGroups) {
        for more in 0...1 {
          for backward in 0..<(layout.kind == .crossTrainer ? 2 : 1) {
            let flags = UInt32((subset << 1) | more | (backward << 15))
            let item = matrixCase(layout, variant: variant, flags: flags)
            let decoded = try decodeMeasurement(layout.kind, bytes: item.wire, options: options)
            assertMatrixDecode(decoded, expected: item.expected)
            #expect(try encodeMeasurement(item.expected, options: options) == item.wire)
            structural += 1
          }
        }
      }

      let all = UInt32((1 << layout.optionalGroups) - 1) << 1
      for field in matrixFields(layout, variant: variant) where field.sentinel {
        let item = matrixCase(layout, variant: variant, flags: all, sentinelIndex: field.index)
        assertMatrixDecode(
          try decodeMeasurement(layout.kind, bytes: item.wire, options: options),
          expected: item.expected)
        #expect(try encodeMeasurement(item.expected, options: options) == item.wire)
        sentinels += 1
      }

      let complete = matrixCase(layout, variant: variant, flags: all)
      #expect(
        complete.wire.count == layout.fullLength
          + (variant == 1 ? (layout.kind == .treadmill ? -2 : 1) : 0))
      for length in 0..<complete.wire.count {
        let prefix = Array(complete.wire.prefix(length))
        if length < layout.flagBytes {
          #expect(throws: FTMSCodecError.self) {
            try decodeMeasurement(layout.kind, bytes: prefix, options: options)
          }
        } else {
          let decoded = try decodeMeasurement(layout.kind, bytes: prefix, options: options)
          #expect(decoded.diagnostics.truncated)
        }
        prefixes += 1
      }

      let firstReserved = layout.kind == .crossTrainer ? 16 : layout.optionalGroups + 1
      for bit in firstReserved..<(layout.flagBytes * 8) {
        let flags = all | (1 << UInt32(bit))
        let item = matrixCase(layout, variant: variant, flags: flags)
        let decoded = try decodeMeasurement(layout.kind, bytes: item.wire, options: options)
        #expect(decoded.diagnostics.reservedFlags)
        #expect(decoded.diagnostics.issues.contains("reserved_flags"))
        #expect(throws: FTMSCodecError.self) {
          try encodeMeasurement(item.expected, options: options)
        }
        reserved += 1
      }
    }
  }
  #expect(structural == 181_760)
  #expect(sentinels == 46)
  #expect(reserved == 47)
  #expect(prefixes > 0)
}
