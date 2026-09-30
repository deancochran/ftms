import 'dart:typed_data';

/// Caller-reported state of service/characteristic discovery.
enum CapabilityDiscovery { notAttempted, partial, complete, failed }

/// Scope of the selected FTMS service instance.
enum CapabilityServiceScope { unknown, present, absent, ambiguous }

/// State of a caller-owned characteristic read.
enum CapabilityReadState { notAttempted, success, failed }

/// Normalized reason for a failed read.
enum CapabilityReadReason {
  none,
  generic,
  securityRequired,
  unavailable,
  timeout,
  disconnected,
}

/// Three-valued caller fact used by Table 4.1 condition C.7.
enum CapabilityTruth { unknown, no, yes }

/// Presence of one constrained known characteristic.
enum CapabilityPresence { unknown, absent, unique, ambiguous }

/// Result of local Feature/range decoding.
enum CapabilityDecode { notAttempted, valid, malformed, failed }

/// Static protocol declaration, rather than runtime authorization.
enum CapabilityDeclaration { unknown, notSupported, supported }

/// State of conservative static prerequisites only.
enum CapabilityPrerequisite {
  notApplicable,
  satisfied,
  incomplete,
  inconsistent,
}

/// FTMS characteristic kind recognized only for full Bluetooth-base UUIDs.
enum CapabilityKnownKind {
  unknown,
  feature,
  treadmill,
  crossTrainer,
  stepClimber,
  stairClimber,
  rower,
  indoorBike,
  trainingStatus,
  speedRange,
  inclinationRange,
  resistanceRange,
  heartRateRange,
  powerRange,
  controlPoint,
  machineStatus,
}

/// Stable diagnostic codes retained in normalized reports.
enum CapabilityDiagnosticCode {
  scopeUnavailable,
  discoveryIncomplete,
  discoveryFailed,
  duplicateCharacteristic,
  requiredCharacteristicMissing,
  requiredPropertyMissing,
  excludedPropertyPresent,
  readFailed,
  readSecurityRequired,
  malformedBytes,
  requiredRangeMissing,
  scopeContradiction,
  insufficientC7Evidence,
}

/// A caller-selected resistance layout; the evaluator never infers it from bytes.
enum CapabilityResistanceRangeFormat { uint8Whole, signed16Tenths }

/// Immutable input observation; its byte getter always returns a copy.
final class CapabilityCharacteristic {
  final String uuid;
  final int properties;
  final CapabilityReadState readState;
  final CapabilityReadReason reason;
  final Uint8List _bytes;

  /// Returns a defensive copy, so callers cannot mutate retained evidence.
  Uint8List get bytes => Uint8List.fromList(_bytes);
  CapabilityCharacteristic({
    required this.uuid,
    required this.properties,
    required this.readState,
    this.reason = CapabilityReadReason.none,
    Uint8List? bytes,
  }) : _bytes = Uint8List.fromList(bytes ?? const []) {
    if (!RegExp(r'^[0-9a-f]{32}$').hasMatch(uuid) ||
        properties < 0 ||
        properties > 0xffff ||
        (readState != CapabilityReadState.failed &&
            reason != CapabilityReadReason.none) ||
        (readState != CapabilityReadState.success && _bytes.isNotEmpty)) {
      throw ArgumentError.value(
        uuid,
        'characteristic',
        'invalid capability evidence',
      );
    }
  }
}

/// Caller-owned C.7 facts; unknown is deliberately not false.
final class CapabilityC7Evidence {
  final CapabilityTruth bondingSupported;
  final CapabilityTruth featureMayChangeOverLifetime;
  const CapabilityC7Evidence({
    this.bondingSupported = CapabilityTruth.unknown,
    this.featureMayChangeOverLifetime = CapabilityTruth.unknown,
  });
}

/// Immutable evidence for one selected service instance and opaque generation.
final class CapabilitySnapshot {
  final CapabilityDiscovery discovery;
  final CapabilityServiceScope scope;
  final int generation;
  final List<CapabilityCharacteristic> characteristics;
  final CapabilityC7Evidence? c7;
  CapabilitySnapshot({
    required this.discovery,
    required this.scope,
    required this.generation,
    required List<CapabilityCharacteristic> characteristics,
    this.c7,
  }) : characteristics = List.unmodifiable(characteristics) {
    if (generation < 0 || generation > 0xffffffff) {
      throw ArgumentError.value(generation, 'generation');
    }
  }
}

/// Exact range numerators with scale and unit metadata.
final class CapabilityRangeValue {
  final int kind, minimum, maximum, increment, scaleDivisor, unit;
  const CapabilityRangeValue(
    this.kind,
    this.minimum,
    this.maximum,
    this.increment,
    this.scaleDivisor,
    this.unit,
  );
  List<int> toJson() => [kind, minimum, maximum, increment, scaleDivisor, unit];
}

/// Presence, decode outcome, and optional exact range value.
final class CapabilityRangeEvidence {
  final CapabilityPresence presence;
  final CapabilityDecode decode;
  final int? inputIndex;
  final CapabilityRangeValue? value;
  const CapabilityRangeEvidence(
    this.presence,
    this.decode,
    this.inputIndex,
    this.value,
  );
  List<Object?> toJson() => [
    presence.index,
    decode.index,
    inputIndex,
    value?.toJson(),
  ];
}

/// Static declaration and prerequisite evidence for one wire opcode.
final class CapabilityOperation {
  final int opcode, targetBit;
  final bool optionalInTable;
  final CapabilityDeclaration declaration;
  final CapabilityPrerequisite prerequisite;
  final int reasons;
  const CapabilityOperation(
    this.opcode,
    this.targetBit,
    this.optionalInTable,
    this.declaration,
    this.prerequisite,
    this.reasons,
  );
  List<Object> toJson() => [
    opcode,
    targetBit,
    optionalInTable ? 1 : 0,
    declaration.index,
    prerequisite.index,
    reasons,
  ];
}

/// Normalized record of one input characteristic and input index.
final class CapabilityObservation {
  final int inputIndex, properties, readSize;
  final String uuid;
  final CapabilityKnownKind knownKind;
  final CapabilityReadState readState;
  final CapabilityReadReason reason;
  const CapabilityObservation(
    this.inputIndex,
    this.uuid,
    this.properties,
    this.knownKind,
    this.readState,
    this.reason,
    this.readSize,
  );
  List<Object> toJson() => [
    inputIndex,
    uuid,
    properties,
    knownKind.index,
    readState.index,
    reason.index,
    readSize,
  ];
}

/// Stable diagnostic tied to a known kind and optional input index.
final class CapabilityDiagnostic {
  final CapabilityDiagnosticCode code;
  final CapabilityKnownKind knownKind;
  final int? inputIndex;
  const CapabilityDiagnostic(this.code, this.knownKind, this.inputIndex);
  List<Object?> toJson() => [code.index, knownKind.index, inputIndex];
}

/// Decoded Feature words and retained unknown/reserved-bit masks.
final class CapabilityFeatureEvidence {
  final CapabilityPresence presence;
  final CapabilityDecode decode;
  final int? inputIndex;
  final int machineRaw, targetRaw, machineUnknown, targetUnknown;
  const CapabilityFeatureEvidence(
    this.presence,
    this.decode,
    this.inputIndex,
    this.machineRaw,
    this.targetRaw,
    this.machineUnknown,
    this.targetUnknown,
  );
  List<Object?> toJson() => [
    presence.index,
    decode.index,
    inputIndex,
    machineRaw,
    targetRaw,
    machineUnknown,
    targetUnknown,
  ];
}

/// Complete normalized static report. It has no execution-authority field.
final class CapabilityReport {
  final int generation;
  final CapabilityDiscovery discovery;
  final CapabilityServiceScope scope;
  final List<CapabilityPresence> presence;
  final CapabilityFeatureEvidence feature;
  final List<CapabilityRangeEvidence> ranges;
  final List<CapabilityOperation> operations;
  final List<CapabilityObservation> observations;
  final List<CapabilityDiagnostic> diagnostics;
  CapabilityReport(
    this.generation,
    this.discovery,
    this.scope,
    List<CapabilityPresence> presence,
    this.feature,
    List<CapabilityRangeEvidence> ranges,
    List<CapabilityOperation> operations,
    List<CapabilityObservation> observations,
    List<CapabilityDiagnostic> diagnostics,
  ) : presence = List.unmodifiable(presence),
      ranges = List.unmodifiable(ranges),
      operations = List.unmodifiable(operations),
      observations = List.unmodifiable(observations),
      diagnostics = List.unmodifiable(diagnostics);
  Map<String, Object?> toJson() => {
    'generation': generation,
    'discovery': discovery.index,
    'scope': scope.index,
    'observationCount': observations.length,
    'diagnosticCount': diagnostics.length,
    'presence': presence.map((x) => x.index).toList(),
    'feature': feature.toJson(),
    'ranges': ranges.map((x) => x.toJson()).toList(),
    'operations': operations.map((x) => x.toJson()).toList(),
    'observations': observations.map((x) => x.toJson()).toList(),
    'diagnostics': diagnostics.map((x) => x.toJson()).toList(),
  };
}

const _base = '00001000800000805f9b34fb';
const _targetForOpcode = [
  255,
  255,
  0,
  1,
  2,
  3,
  4,
  255,
  255,
  5,
  6,
  7,
  8,
  9,
  10,
  11,
  12,
  13,
  14,
  15,
  16,
];
const _rangeForTarget = [
  0,
  1,
  2,
  4,
  3,
]; // target power/heart-rate differs from range order.

CapabilityKnownKind _kind(String uuid) {
  if (!uuid.startsWith('0000') || uuid.substring(8) != _base) {
    return CapabilityKnownKind.unknown;
  }
  final value = int.tryParse(uuid.substring(4, 8), radix: 16);
  if (value == null || value < 0x2acc || value > 0x2ada) {
    return CapabilityKnownKind.unknown;
  }
  return CapabilityKnownKind.values[value - 0x2acc + 1];
}

bool _c7Unknown(CapabilityC7Evidence? c) =>
    c == null ||
    (c.bondingSupported != CapabilityTruth.no &&
        c.featureMayChangeOverLifetime != CapabilityTruth.no &&
        !(c.bondingSupported == CapabilityTruth.yes &&
            c.featureMayChangeOverLifetime == CapabilityTruth.yes));
int _required(CapabilityKnownKind k, CapabilityC7Evidence? c) {
  if (k == CapabilityKnownKind.feature) {
    return 2 |
        (c?.bondingSupported == CapabilityTruth.yes &&
                c?.featureMayChangeOverLifetime == CapabilityTruth.yes
            ? 32
            : 0);
  }
  if (k.index >= 9 && k.index <= 13) return 2;
  if (k == CapabilityKnownKind.trainingStatus) return 18;
  if (k == CapabilityKnownKind.controlPoint) return 40;
  return 16;
}

int _u16(Uint8List b, int p) => b[p] | (b[p + 1] << 8);
int _i16(Uint8List b, int p) {
  final x = _u16(b, p);
  return x >= 0x8000 ? x - 0x10000 : x;
}

int _u32(Uint8List b, int p) =>
    b[p] | b[p + 1] << 8 | b[p + 2] << 16 | b[p + 3] << 24;

/// Evaluates only static protocol evidence.  It never grants current execution permission.
CapabilityReport evaluateCapabilities(
  CapabilitySnapshot s, {
  CapabilityResistanceRangeFormat resistanceRangeFormat =
      CapabilityResistanceRangeFormat.uint8Whole,
}) {
  final cs = s.characteristics, kinds = cs.map((c) => _kind(c.uuid)).toList();
  final first = List<int>.filled(16, -1), counts = List<int>.filled(16, 0);
  final presence = List<CapabilityPresence>.filled(
    16,
    CapabilityPresence.unknown,
  );
  final diagnostics = <CapabilityDiagnostic>[];
  final scopeOk = s.scope == CapabilityServiceScope.present;
  for (var i = 0; i < cs.length; i++) {
    final k = kinds[i].index;
    if (k != 0) {
      if (first[k] < 0) first[k] = i;
      if (counts[k] < 2) counts[k]++;
    }
  }
  for (var k = 1; k < 16; k++) {
    if (counts[k] > 1) {
      presence[k] = CapabilityPresence.ambiguous;
      diagnostics.add(
        CapabilityDiagnostic(
          CapabilityDiagnosticCode.duplicateCharacteristic,
          CapabilityKnownKind.values[k],
          first[k],
        ),
      );
    } else if (counts[k] == 1) {
      presence[k] = CapabilityPresence.unique;
    } else if (s.discovery == CapabilityDiscovery.complete && scopeOk) {
      presence[k] = CapabilityPresence.absent;
    }
  }
  if (!scopeOk) {
    diagnostics.add(
      const CapabilityDiagnostic(
        CapabilityDiagnosticCode.scopeUnavailable,
        CapabilityKnownKind.unknown,
        null,
      ),
    );
  }
  final absent =
      s.scope == CapabilityServiceScope.absent &&
      s.discovery == CapabilityDiscovery.complete &&
      cs.isEmpty;
  if (s.scope == CapabilityServiceScope.absent && !absent) {
    diagnostics.add(
      const CapabilityDiagnostic(
        CapabilityDiagnosticCode.scopeContradiction,
        CapabilityKnownKind.unknown,
        null,
      ),
    );
  }
  if (s.discovery != CapabilityDiscovery.complete) {
    diagnostics.add(
      CapabilityDiagnostic(
        s.discovery == CapabilityDiscovery.failed
            ? CapabilityDiagnosticCode.discoveryFailed
            : CapabilityDiagnosticCode.discoveryIncomplete,
        CapabilityKnownKind.unknown,
        null,
      ),
    );
  }
  if (scopeOk) {
    for (var i = 0; i < cs.length; i++) {
      final k = kinds[i];
      if (k == CapabilityKnownKind.unknown) {
        continue;
      }
      final required = _required(k, s.c7);
      final unknown = k == CapabilityKnownKind.feature && _c7Unknown(s.c7);
      if ((cs[i].properties & required) != required) {
        diagnostics.add(
          CapabilityDiagnostic(
            CapabilityDiagnosticCode.requiredPropertyMissing,
            k,
            i,
          ),
        );
      }
      if ((cs[i].properties & ~(required | (unknown ? 32 : 0))) != 0) {
        diagnostics.add(
          CapabilityDiagnostic(
            CapabilityDiagnosticCode.excludedPropertyPresent,
            k,
            i,
          ),
        );
      }
      if (unknown) {
        diagnostics.add(
          CapabilityDiagnostic(
            CapabilityDiagnosticCode.insufficientC7Evidence,
            k,
            i,
          ),
        );
      }
      if (cs[i].readState == CapabilityReadState.failed) {
        diagnostics.add(
          CapabilityDiagnostic(
            cs[i].reason == CapabilityReadReason.securityRequired
                ? CapabilityDiagnosticCode.readSecurityRequired
                : CapabilityDiagnosticCode.readFailed,
            k,
            i,
          ),
        );
      }
    }
  }
  CapabilityDecode decodeFeature() {
    if (!scopeOk || presence[1] != CapabilityPresence.unique) {
      return CapabilityDecode.notAttempted;
    }
    final c = cs[first[1]];
    if (c.readState == CapabilityReadState.failed) {
      return CapabilityDecode.failed;
    }
    return c.readState == CapabilityReadState.success && c.bytes.length == 8
        ? CapabilityDecode.valid
        : c.readState == CapabilityReadState.success
        ? CapabilityDecode.malformed
        : CapabilityDecode.notAttempted;
  }

  final fd = decodeFeature();
  var machine = 0, target = 0, mu = 0, tu = 0;
  if (fd == CapabilityDecode.valid) {
    final b = cs[first[1]].bytes;
    machine = _u32(b, 0);
    target = _u32(b, 4);
    mu = machine & ~0x1ffff;
    tu = target & ~0x1ffff;
  }
  final feature = CapabilityFeatureEvidence(
    presence[1],
    fd,
    scopeOk && presence[1] == CapabilityPresence.unique ? first[1] : null,
    machine,
    target,
    mu,
    tu,
  );
  if (fd == CapabilityDecode.malformed) {
    diagnostics.add(
      CapabilityDiagnostic(
        CapabilityDiagnosticCode.malformedBytes,
        CapabilityKnownKind.feature,
        first[1],
      ),
    );
  }
  CapabilityRangeEvidence range(int r) {
    final k = 9 + r;
    final p = presence[k];
    if (!scopeOk || p != CapabilityPresence.unique) {
      return CapabilityRangeEvidence(
        p,
        CapabilityDecode.notAttempted,
        null,
        null,
      );
    }
    final i = first[k];
    final c = cs[i];
    if (c.readState == CapabilityReadState.failed) {
      return CapabilityRangeEvidence(p, CapabilityDecode.failed, i, null);
    }
    if (c.readState != CapabilityReadState.success) {
      return CapabilityRangeEvidence(p, CapabilityDecode.notAttempted, i, null);
    }
    final good = r == 3
        ? c.bytes.length == 3
        : r == 2
        ? (resistanceRangeFormat == CapabilityResistanceRangeFormat.uint8Whole
              ? c.bytes.length == 3
              : c.bytes.length == 6)
        : c.bytes.length == 6;
    if (!good) {
      return CapabilityRangeEvidence(p, CapabilityDecode.malformed, i, null);
    }
    final b = c.bytes;
    final min = r == 0
        ? _u16(b, 0)
        : r == 1 || r == 4
        ? _i16(b, 0)
        : r == 2
        ? (resistanceRangeFormat == CapabilityResistanceRangeFormat.uint8Whole
              ? b[0]
              : _i16(b, 0))
        : b[0];
    final max = r == 0
        ? _u16(b, 2)
        : r == 1 || r == 4
        ? _i16(b, 2)
        : r == 2
        ? (resistanceRangeFormat == CapabilityResistanceRangeFormat.uint8Whole
              ? b[1]
              : _i16(b, 2))
        : b[1];
    final inc = r == 0
        ? _u16(b, 4)
        : r == 1 || r == 4
        ? _u16(b, 4)
        : r == 2
        ? (resistanceRangeFormat == CapabilityResistanceRangeFormat.uint8Whole
              ? b[2]
              : _u16(b, 4))
        : b[2];
    if (inc == 0 || min > max) {
      return CapabilityRangeEvidence(p, CapabilityDecode.malformed, i, null);
    }
    final divisor = r == 0
        ? 100
        : r == 1
        ? 10
        : r == 2 &&
              resistanceRangeFormat ==
                  CapabilityResistanceRangeFormat.signed16Tenths
        ? 10
        : 1;
    return CapabilityRangeEvidence(
      p,
      CapabilityDecode.valid,
      i,
      CapabilityRangeValue(r, min, max, inc, divisor, r),
    );
  }

  final ranges = List.generate(5, range);
  for (var r = 0; r < 5; r++) {
    if (ranges[r].decode == CapabilityDecode.malformed) {
      diagnostics.add(
        CapabilityDiagnostic(
          CapabilityDiagnosticCode.malformedBytes,
          CapabilityKnownKind.values[9 + r],
          ranges[r].inputIndex,
        ),
      );
    }
  }
  if (scopeOk) {
    if (presence[1] == CapabilityPresence.absent) {
      diagnostics.add(
        const CapabilityDiagnostic(
          CapabilityDiagnosticCode.requiredCharacteristicMissing,
          CapabilityKnownKind.feature,
          null,
        ),
      );
    }
    if ((presence[14] == CapabilityPresence.unique ||
            presence[14] == CapabilityPresence.ambiguous) &&
        presence[15] == CapabilityPresence.absent) {
      diagnostics.add(
        const CapabilityDiagnostic(
          CapabilityDiagnosticCode.requiredCharacteristicMissing,
          CapabilityKnownKind.machineStatus,
          null,
        ),
      );
    }
    if (fd == CapabilityDecode.valid) {
      if ((target & 0x1ffff) != 0 &&
          presence[14] == CapabilityPresence.absent) {
        diagnostics.add(
          const CapabilityDiagnostic(
            CapabilityDiagnosticCode.requiredCharacteristicMissing,
            CapabilityKnownKind.controlPoint,
            null,
          ),
        );
      }
      for (var bit = 0; bit < 5; bit++) {
        if ((target & (1 << bit)) != 0) {
          final r = _rangeForTarget[bit];
          if (ranges[r].presence == CapabilityPresence.absent) {
            diagnostics.add(
              CapabilityDiagnostic(
                CapabilityDiagnosticCode.requiredRangeMissing,
                CapabilityKnownKind.values[9 + r],
                null,
              ),
            );
          }
        }
      }
    }
  }
  int charReasons(int k, int unavailable, int invalid) {
    if (presence[k] == CapabilityPresence.unknown) return unavailable;
    if (presence[k] != CapabilityPresence.unique) return invalid;
    final p = cs[first[k]].properties;
    if (k == 1 && _c7Unknown(s.c7)) {
      return 1024 | (((p & 2) == 0 || (p & ~(2 | 32)) != 0) ? invalid : 0);
    }
    return p == _required(CapabilityKnownKind.values[k], s.c7) ? 0 : invalid;
  }

  int decodeReasons(CapabilityDecode d, int unavailable, int invalid) =>
      d == CapabilityDecode.malformed
      ? invalid
      : d == CapabilityDecode.valid
      ? 0
      : unavailable;
  final operations = <CapabilityOperation>[];
  for (var op = 0; op < 21; op++) {
    final bit = _targetForOpcode[op];
    var declaration = CapabilityDeclaration.unknown,
        prerequisite = CapabilityPrerequisite.incomplete,
        why = 0;
    if (!scopeOk) {
      why = 1;
      if (absent) {
        declaration = CapabilityDeclaration.notSupported;
        prerequisite = CapabilityPrerequisite.notApplicable;
      } else if (s.scope == CapabilityServiceScope.absent) {
        prerequisite = CapabilityPrerequisite.inconsistent;
      }
      operations.add(
        CapabilityOperation(
          op,
          bit,
          op == 18 || op == 19,
          declaration,
          prerequisite,
          why,
        ),
      );
      continue;
    }
    if (bit == 255) {
      declaration = presence[14] == CapabilityPresence.unique
          ? CapabilityDeclaration.supported
          : presence[14] == CapabilityPresence.absent
          ? CapabilityDeclaration.notSupported
          : CapabilityDeclaration.unknown;
    } else if (fd == CapabilityDecode.valid) {
      declaration = (target & (1 << bit)) != 0
          ? CapabilityDeclaration.supported
          : CapabilityDeclaration.notSupported;
    }
    if (declaration == CapabilityDeclaration.notSupported) {
      operations.add(
        CapabilityOperation(
          op,
          bit,
          op == 18 || op == 19,
          declaration,
          CapabilityPrerequisite.notApplicable,
          0,
        ),
      );
      continue;
    }
    if (s.discovery != CapabilityDiscovery.complete) {
      why |= 2;
    }
    why |= charReasons(1, 4, 8);
    if (bit != 255 && presence[1] == CapabilityPresence.unique) {
      why |= decodeReasons(fd, 4, 8);
    }
    why |= charReasons(14, 16, 32) | charReasons(15, 64, 128);
    if (bit < 5 && declaration == CapabilityDeclaration.supported) {
      final r = _rangeForTarget[bit], k = 9 + r;
      why |= charReasons(k, 256, 512);
      if (presence[k] == CapabilityPresence.unique) {
        why |= decodeReasons(ranges[r].decode, 256, 512);
      }
    }
    prerequisite = (why & (8 | 32 | 128 | 512)) != 0
        ? CapabilityPrerequisite.inconsistent
        : why == 0
        ? CapabilityPrerequisite.satisfied
        : CapabilityPrerequisite.incomplete;
    operations.add(
      CapabilityOperation(
        op,
        bit,
        op == 18 || op == 19,
        declaration,
        prerequisite,
        why,
      ),
    );
  }
  final observations = List.generate(
    cs.length,
    (i) => CapabilityObservation(
      i,
      cs[i].uuid,
      cs[i].properties,
      kinds[i],
      cs[i].readState,
      cs[i].reason,
      cs[i].bytes.length,
    ),
  );
  return CapabilityReport(
    s.generation,
    s.discovery,
    s.scope,
    presence,
    feature,
    ranges,
    operations,
    observations,
    diagnostics,
  );
}
