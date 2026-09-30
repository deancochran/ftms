import 'package:deancochran_ftms/deancochran_ftms.dart';

void main() {
  final report = evaluateCapabilities(
    CapabilitySnapshot(
      discovery: CapabilityDiscovery.notAttempted,
      scope: CapabilityServiceScope.unknown,
      generation: 1,
      characteristics: [],
    ),
  );
  // Unknown evidence must not become "not supported" or permission to execute.
  if (report.operations.any(
    (op) => op.declaration != CapabilityDeclaration.unknown,
  )) {
    throw StateError('Missing evidence was incorrectly promoted');
  }
  print('Static report: ${report.diagnostics.length} evidence diagnostics');
}
