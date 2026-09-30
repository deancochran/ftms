@inline(__always) func u16(_ bytes: [UInt8], _ offset: Int) -> UInt16 {
  UInt16(bytes[offset]) | UInt16(bytes[offset + 1]) << 8
}
@inline(__always) func i16(_ bytes: [UInt8], _ offset: Int) -> Int16 {
  Int16(bitPattern: u16(bytes, offset))
}
@inline(__always) func u24(_ bytes: [UInt8], _ offset: Int) -> UInt32 {
  UInt32(bytes[offset]) | UInt32(bytes[offset + 1]) << 8 | UInt32(bytes[offset + 2]) << 16
}
@inline(__always) func bytes16(_ value: UInt16) -> [UInt8] {
  [UInt8(truncatingIfNeeded: value), UInt8(truncatingIfNeeded: value >> 8)]
}
@inline(__always) func bytes24(_ value: UInt32) -> [UInt8] {
  [
    UInt8(truncatingIfNeeded: value), UInt8(truncatingIfNeeded: value >> 8),
    UInt8(truncatingIfNeeded: value >> 16),
  ]
}
