/// A transport-independent codec for Bluetooth Fitness Machine Service 1.0.
/// The core deliberately contains no BLE, scheduling, UI, or connection APIs.
import Foundation

public enum FTMSCodecError: Error, Equatable, Sendable {
  case length, kind, range
  case malformed(String)
}
public struct FTMSDiagnostics: Equatable, Sendable {
  public var truncated = false
  public var trailingBytes = false
  public var reservedFlags = false
  public var issues: [String] = []
  public init() {}
}
