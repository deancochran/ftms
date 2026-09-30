import Foundation

/// Machine-readable evidence consumed by `Verification/verify.py`.  Emit this
/// only after the fixture's assertions have run; a non-zero test process still
/// makes every marker unresolved rather than a pass.
func nativeCaseExecuted(_ corpus: String, _ category: String, _ id: String, directions: Int = 1) {
  let marker: [String: Any] = [
    "corpus": corpus, "category": category, "id": id,
    "assertions": directions, "directions": directions,
  ]
  let data = try! JSONSerialization.data(withJSONObject: marker, options: [.sortedKeys])
  print("FTMS_NATIVE_CASE \(String(data: data, encoding: .utf8)!)")
}
