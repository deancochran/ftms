// swift-tools-version: 6.0
import PackageDescription

// Thin SwiftPM entry point. All package-owned source and tests remain in packages/swift.
let package = Package(
  name: "FTMS",
  platforms: [.macOS(.v13), .iOS(.v16), .tvOS(.v16), .watchOS(.v9), .visionOS(.v1)],
  products: [.library(name: "FTMS", targets: ["FTMS"])],
  targets: [
    .target(name: "FTMS", path: "packages/swift/Sources/FTMS"),
    .testTarget(name: "FTMSTests", dependencies: ["FTMS"], path: "packages/swift/Tests/FTMSTests"),
  ]
)
