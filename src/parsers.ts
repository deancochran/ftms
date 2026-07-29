import { toBytes, toDataView } from "./binary.js";
import { FTMS_CHARACTERISTICS, FTMS_MACHINE_STATUS_OPCODES } from "./constants.js";
import type {
  FtmsDiagnostic,
  FtmsMachineStatusParameter,
  FtmsMachineType,
  FtmsParserDefinition,
  FtmsRuntimeMetrics,
  FtmsStatusPayload,
  ParsedFtmsIndoorBikeData,
  ParsedFtmsPayload,
} from "./types.js";

function decodeUtf8(bytes: Uint8Array): string {
  let result = "";
  for (let index = 0; index < bytes.byteLength; ) {
    const first = bytes[index];
    if (first === undefined) break;

    let codePoint: number;
    let continuationCount: number;
    if (first <= 0x7f) {
      codePoint = first;
      continuationCount = 0;
    } else if (first >= 0xc2 && first <= 0xdf) {
      codePoint = first & 0x1f;
      continuationCount = 1;
    } else if (first >= 0xe0 && first <= 0xef) {
      codePoint = first & 0x0f;
      continuationCount = 2;
    } else if (first >= 0xf0 && first <= 0xf4) {
      codePoint = first & 0x07;
      continuationCount = 3;
    } else {
      result += "\uFFFD";
      index += 1;
      continue;
    }

    if (index + continuationCount >= bytes.byteLength) {
      result += "\uFFFD";
      break;
    }

    const second = bytes[index + 1];
    let valid =
      continuationCount === 0 ||
      (second !== undefined &&
        !(first === 0xe0 && second < 0xa0) &&
        !(first === 0xed && second > 0x9f) &&
        !(first === 0xf0 && second < 0x90) &&
        !(first === 0xf4 && second > 0x8f));
    for (
      let continuationIndex = 1;
      valid && continuationIndex <= continuationCount;
      continuationIndex += 1
    ) {
      const continuation = bytes[index + continuationIndex];
      if (continuation === undefined || (continuation & 0xc0) !== 0x80) {
        valid = false;
        break;
      }
      codePoint = (codePoint << 6) | (continuation & 0x3f);
    }

    if (!valid) {
      result += "\uFFFD";
      index += 1;
      continue;
    }

    if (codePoint > 0x10ffff || (codePoint >= 0xd800 && codePoint <= 0xdfff)) {
      result += "\uFFFD";
      index += 1;
      continue;
    }

    result += String.fromCodePoint(codePoint);
    index += continuationCount + 1;
  }
  return result;
}

function createEmptyMetrics(): FtmsRuntimeMetrics {
  return {
    hrBpm: null,
    powerWatts: null,
    averagePowerWatts: null,
    cadenceRpm: null,
    averageCadenceRpm: null,
    speedMps: null,
    averageSpeedMps: null,
    distanceMeters: null,
    elapsedTimeSeconds: null,
    remainingTimeSeconds: null,
    energyKcal: null,
    energyPerHourKcal: null,
    energyPerMinuteKcal: null,
    metabolicEquivalent: null,
    stepCount: null,
    stepRateSpm: null,
    averageStepRateSpm: null,
    strideCount: null,
    floorCount: null,
    positiveElevationGainMeters: null,
    negativeElevationGainMeters: null,
    inclinationPercent: null,
    rampAngleDegrees: null,
    resistanceLevel: null,
    instantaneousPaceSecondsPer500m: null,
    averagePaceSecondsPer500m: null,
    forceOnBeltNewtons: null,
    strokeRateSpm: null,
    averageStrokeRateSpm: null,
    strokeCount: null,
    movementDirection: null,
  };
}

class FieldReader {
  public offset: number;
  public truncated = false;
  public readonly issues: FtmsDiagnostic[] = [];

  public constructor(
    private readonly view: DataView,
    initialOffset: number,
  ) {
    this.offset = initialOffset;
  }

  public readUint8(field: string): number | null {
    return this.read(1, field, (offset) => this.view.getUint8(offset));
  }

  public readUint16(field: string): number | null {
    return this.read(2, field, (offset) => this.view.getUint16(offset, true));
  }

  public readInt16(field: string): number | null {
    return this.read(2, field, (offset) => this.view.getInt16(offset, true));
  }

  public readUint24(field: string): number | null {
    return this.read(
      3,
      field,
      (offset) =>
        this.view.getUint8(offset) |
        (this.view.getUint8(offset + 1) << 8) |
        (this.view.getUint8(offset + 2) << 16),
    );
  }

  private read(size: number, field: string, getter: (offset: number) => number): number | null {
    if (this.truncated) {
      return null;
    }

    if (this.offset + size > this.view.byteLength) {
      this.truncated = true;
      this.issues.push({
        code: "truncated",
        field,
        offset: this.offset,
        expected: size,
        actual: Math.max(0, this.view.byteLength - this.offset),
      });
      return null;
    }

    const value = getter(this.offset);
    this.offset += size;
    return value;
  }
}

function isBitSet(flags: number, bit: number): boolean {
  return (flags & (2 ** bit)) !== 0;
}

function speedHundredthsKphToMps(value: number | null): number | null {
  return value === null ? null : value / 360;
}

function scale(value: number | null, divisor: number): number | null {
  return value === null ? null : value / divisor;
}

function unavailable(
  value: number | null,
  sentinel: number,
  field: string,
  reader: FieldReader,
): number | null {
  if (value === sentinel) {
    reader.issues.push({ code: "unavailable", field });
    return null;
  }
  return value;
}

function readEnergy(reader: FieldReader, metrics: FtmsRuntimeMetrics): void {
  metrics.energyKcal = unavailable(reader.readUint16("energyKcal"), 0xffff, "energyKcal", reader);
  metrics.energyPerHourKcal = unavailable(
    reader.readUint16("energyPerHourKcal"),
    0xffff,
    "energyPerHourKcal",
    reader,
  );
  metrics.energyPerMinuteKcal = unavailable(
    reader.readUint8("energyPerMinuteKcal"),
    0xff,
    "energyPerMinuteKcal",
    reader,
  );
}

function readUnavailableInt16(reader: FieldReader, field: string): number | null {
  return unavailable(reader.readInt16(field), 0x7fff, field, reader);
}

interface MeasurementDefinition {
  characteristicUuid: string;
  machineType: FtmsMachineType;
  flagBytes: 2 | 3;
  validFlagsMask: number;
  readFields: (flags: number, reader: FieldReader, metrics: FtmsRuntimeMetrics) => void;
}

function parseMeasurement(
  data: ArrayBuffer | Uint8Array,
  definition: MeasurementDefinition,
): ParsedFtmsPayload {
  const view = toDataView(data);
  const metrics = createEmptyMetrics();

  if (view.byteLength < definition.flagBytes) {
    return {
      kind: "measurement",
      characteristicUuid: definition.characteristicUuid,
      machineType: definition.machineType,
      metrics,
      status: null,
      diagnostics: {
        truncated: true,
        bytesRead: 0,
        byteLength: view.byteLength,
        issues: [
          {
            code: "truncated",
            field: "flags",
            offset: 0,
            expected: definition.flagBytes,
            actual: view.byteLength,
          },
        ],
      },
    };
  }

  let flags = 0;
  for (let index = 0; index < definition.flagBytes; index += 1) {
    flags |= view.getUint8(index) * 2 ** (index * 8);
  }

  const reader = new FieldReader(view, definition.flagBytes);
  definition.readFields(flags, reader, metrics);
  const moreData = isBitSet(flags, 0);

  if (moreData) {
    reader.issues.push({ code: "more_data", field: "flags" });
  }

  const reservedFlags = flags & ~definition.validFlagsMask;
  if (reservedFlags !== 0) {
    reader.issues.push({
      code: "reserved_flags",
      field: "flags",
      actual: reservedFlags,
    });
  }

  if (!reader.truncated && reader.offset < view.byteLength) {
    reader.issues.push({
      code: "trailing_bytes",
      offset: reader.offset,
      expected: reader.offset,
      actual: view.byteLength,
    });
  }

  return {
    kind: "measurement",
    characteristicUuid: definition.characteristicUuid,
    machineType: definition.machineType,
    metrics,
    status: null,
    diagnostics: {
      truncated: reader.truncated,
      flags,
      moreData,
      bytesRead: Math.min(reader.offset, view.byteLength),
      byteLength: view.byteLength,
      issues: reader.issues,
    },
  };
}

export function parseFtmsTreadmillData(data: ArrayBuffer | Uint8Array): ParsedFtmsPayload {
  return parseMeasurement(data, {
    characteristicUuid: FTMS_CHARACTERISTICS.TREADMILL_DATA,
    machineType: "treadmill",
    flagBytes: 2,
    validFlagsMask: 0x1fff,
    readFields(flags, reader, metrics) {
      if (!isBitSet(flags, 0)) {
        metrics.speedMps = speedHundredthsKphToMps(reader.readUint16("speed"));
      }
      if (isBitSet(flags, 1)) {
        metrics.averageSpeedMps = speedHundredthsKphToMps(reader.readUint16("averageSpeed"));
      }
      if (isBitSet(flags, 2)) {
        metrics.distanceMeters = reader.readUint24("distanceMeters");
      }
      if (isBitSet(flags, 3)) {
        metrics.inclinationPercent = scale(readUnavailableInt16(reader, "inclinationPercent"), 10);
        metrics.rampAngleDegrees = scale(readUnavailableInt16(reader, "rampAngleDegrees"), 10);
      }
      if (isBitSet(flags, 4)) {
        metrics.positiveElevationGainMeters = scale(
          reader.readUint16("positiveElevationGainMeters"),
          10,
        );
        metrics.negativeElevationGainMeters = scale(
          reader.readUint16("negativeElevationGainMeters"),
          10,
        );
      }
      if (isBitSet(flags, 5)) {
        metrics.instantaneousPaceSecondsPer500m = reader.readUint16(
          "instantaneousPaceSecondsPer500m",
        );
      }
      if (isBitSet(flags, 6)) {
        metrics.averagePaceSecondsPer500m = reader.readUint16("averagePaceSecondsPer500m");
      }
      if (isBitSet(flags, 7)) {
        readEnergy(reader, metrics);
      }
      if (isBitSet(flags, 8)) {
        metrics.hrBpm = reader.readUint8("heartRateBpm");
      }
      if (isBitSet(flags, 9)) {
        metrics.metabolicEquivalent = scale(reader.readUint8("metabolicEquivalent"), 10);
      }
      if (isBitSet(flags, 10)) {
        metrics.elapsedTimeSeconds = reader.readUint16("elapsedTimeSeconds");
      }
      if (isBitSet(flags, 11)) {
        metrics.remainingTimeSeconds = reader.readUint16("remainingTimeSeconds");
      }
      if (isBitSet(flags, 12)) {
        metrics.forceOnBeltNewtons = readUnavailableInt16(reader, "forceOnBeltNewtons");
        metrics.powerWatts = readUnavailableInt16(reader, "powerWatts");
      }
    },
  });
}

export function parseFtmsCrossTrainerData(data: ArrayBuffer | Uint8Array): ParsedFtmsPayload {
  return parseMeasurement(data, {
    characteristicUuid: FTMS_CHARACTERISTICS.CROSS_TRAINER_DATA,
    machineType: "cross_trainer",
    flagBytes: 3,
    validFlagsMask: 0xffff,
    readFields(flags, reader, metrics) {
      if (!isBitSet(flags, 0)) {
        metrics.speedMps = speedHundredthsKphToMps(reader.readUint16("speed"));
      }
      if (isBitSet(flags, 1)) {
        metrics.averageSpeedMps = speedHundredthsKphToMps(reader.readUint16("averageSpeed"));
      }
      if (isBitSet(flags, 2)) {
        metrics.distanceMeters = reader.readUint24("distanceMeters");
      }
      if (isBitSet(flags, 3)) {
        metrics.stepRateSpm = unavailable(
          reader.readUint16("stepRateSpm"),
          0xffff,
          "stepRateSpm",
          reader,
        );
        metrics.averageStepRateSpm = unavailable(
          reader.readUint16("averageStepRateSpm"),
          0xffff,
          "averageStepRateSpm",
          reader,
        );
      }
      if (isBitSet(flags, 4)) {
        metrics.strideCount = scale(reader.readUint16("strideCount"), 10);
      }
      if (isBitSet(flags, 5)) {
        metrics.positiveElevationGainMeters = reader.readUint16("positiveElevationGainMeters");
        metrics.negativeElevationGainMeters = reader.readUint16("negativeElevationGainMeters");
      }
      if (isBitSet(flags, 6)) {
        metrics.inclinationPercent = scale(readUnavailableInt16(reader, "inclinationPercent"), 10);
        metrics.rampAngleDegrees = scale(readUnavailableInt16(reader, "rampAngleDegrees"), 10);
      }
      if (isBitSet(flags, 7)) {
        metrics.resistanceLevel = reader.readUint8("resistanceLevel");
      }
      if (isBitSet(flags, 8)) {
        metrics.powerWatts = reader.readInt16("powerWatts");
      }
      if (isBitSet(flags, 9)) {
        metrics.averagePowerWatts = reader.readInt16("averagePowerWatts");
      }
      if (isBitSet(flags, 10)) {
        readEnergy(reader, metrics);
      }
      if (isBitSet(flags, 11)) {
        metrics.hrBpm = reader.readUint8("heartRateBpm");
      }
      if (isBitSet(flags, 12)) {
        metrics.metabolicEquivalent = scale(reader.readUint8("metabolicEquivalent"), 10);
      }
      if (isBitSet(flags, 13)) {
        metrics.elapsedTimeSeconds = reader.readUint16("elapsedTimeSeconds");
      }
      if (isBitSet(flags, 14)) {
        metrics.remainingTimeSeconds = reader.readUint16("remainingTimeSeconds");
      }
      metrics.movementDirection = isBitSet(flags, 15) ? "backward" : "forward";
    },
  });
}

export function parseFtmsStepClimberData(data: ArrayBuffer | Uint8Array): ParsedFtmsPayload {
  return parseMeasurement(data, {
    characteristicUuid: FTMS_CHARACTERISTICS.STEP_CLIMBER_DATA,
    machineType: "step_climber",
    flagBytes: 2,
    validFlagsMask: 0x01ff,
    readFields(flags, reader, metrics) {
      if (!isBitSet(flags, 0)) {
        metrics.floorCount = reader.readUint16("floorCount");
        metrics.stepCount = reader.readUint16("stepCount");
      }
      if (isBitSet(flags, 1)) {
        metrics.stepRateSpm = reader.readUint16("stepRateSpm");
      }
      if (isBitSet(flags, 2)) {
        metrics.averageStepRateSpm = reader.readUint16("averageStepRateSpm");
      }
      if (isBitSet(flags, 3)) {
        metrics.positiveElevationGainMeters = reader.readUint16("positiveElevationGainMeters");
      }
      if (isBitSet(flags, 4)) {
        readEnergy(reader, metrics);
      }
      if (isBitSet(flags, 5)) {
        metrics.hrBpm = reader.readUint8("heartRateBpm");
      }
      if (isBitSet(flags, 6)) {
        metrics.metabolicEquivalent = scale(reader.readUint8("metabolicEquivalent"), 10);
      }
      if (isBitSet(flags, 7)) {
        metrics.elapsedTimeSeconds = reader.readUint16("elapsedTimeSeconds");
      }
      if (isBitSet(flags, 8)) {
        metrics.remainingTimeSeconds = reader.readUint16("remainingTimeSeconds");
      }
    },
  });
}

export function parseFtmsStairClimberData(data: ArrayBuffer | Uint8Array): ParsedFtmsPayload {
  return parseMeasurement(data, {
    characteristicUuid: FTMS_CHARACTERISTICS.STAIR_CLIMBER_DATA,
    machineType: "stair_climber",
    flagBytes: 2,
    validFlagsMask: 0x03ff,
    readFields(flags, reader, metrics) {
      if (!isBitSet(flags, 0)) {
        metrics.floorCount = reader.readUint16("floorCount");
      }
      if (isBitSet(flags, 1)) {
        metrics.stepRateSpm = reader.readUint16("stepRateSpm");
      }
      if (isBitSet(flags, 2)) {
        metrics.averageStepRateSpm = reader.readUint16("averageStepRateSpm");
      }
      if (isBitSet(flags, 3)) {
        metrics.positiveElevationGainMeters = reader.readUint16("positiveElevationGainMeters");
      }
      if (isBitSet(flags, 4)) {
        metrics.strideCount = reader.readUint16("strideCount");
      }
      if (isBitSet(flags, 5)) {
        readEnergy(reader, metrics);
      }
      if (isBitSet(flags, 6)) {
        metrics.hrBpm = reader.readUint8("heartRateBpm");
      }
      if (isBitSet(flags, 7)) {
        metrics.metabolicEquivalent = scale(reader.readUint8("metabolicEquivalent"), 10);
      }
      if (isBitSet(flags, 8)) {
        metrics.elapsedTimeSeconds = reader.readUint16("elapsedTimeSeconds");
      }
      if (isBitSet(flags, 9)) {
        metrics.remainingTimeSeconds = reader.readUint16("remainingTimeSeconds");
      }
    },
  });
}

export function parseFtmsRowerData(data: ArrayBuffer | Uint8Array): ParsedFtmsPayload {
  return parseMeasurement(data, {
    characteristicUuid: FTMS_CHARACTERISTICS.ROWER_DATA,
    machineType: "rower",
    flagBytes: 2,
    validFlagsMask: 0x1fff,
    readFields(flags, reader, metrics) {
      if (!isBitSet(flags, 0)) {
        metrics.strokeRateSpm = scale(reader.readUint8("strokeRateSpm"), 2);
        metrics.strokeCount = reader.readUint16("strokeCount");
      }
      if (isBitSet(flags, 1)) {
        metrics.averageStrokeRateSpm = scale(reader.readUint8("averageStrokeRateSpm"), 2);
      }
      if (isBitSet(flags, 2)) {
        metrics.distanceMeters = reader.readUint24("distanceMeters");
      }
      if (isBitSet(flags, 3)) {
        metrics.instantaneousPaceSecondsPer500m = reader.readUint16(
          "instantaneousPaceSecondsPer500m",
        );
      }
      if (isBitSet(flags, 4)) {
        metrics.averagePaceSecondsPer500m = reader.readUint16("averagePaceSecondsPer500m");
      }
      if (isBitSet(flags, 5)) {
        metrics.powerWatts = reader.readInt16("powerWatts");
      }
      if (isBitSet(flags, 6)) {
        metrics.averagePowerWatts = reader.readInt16("averagePowerWatts");
      }
      if (isBitSet(flags, 7)) {
        metrics.resistanceLevel = reader.readUint8("resistanceLevel");
      }
      if (isBitSet(flags, 8)) {
        readEnergy(reader, metrics);
      }
      if (isBitSet(flags, 9)) {
        metrics.hrBpm = reader.readUint8("heartRateBpm");
      }
      if (isBitSet(flags, 10)) {
        metrics.metabolicEquivalent = scale(reader.readUint8("metabolicEquivalent"), 10);
      }
      if (isBitSet(flags, 11)) {
        metrics.elapsedTimeSeconds = reader.readUint16("elapsedTimeSeconds");
      }
      if (isBitSet(flags, 12)) {
        metrics.remainingTimeSeconds = reader.readUint16("remainingTimeSeconds");
      }
    },
  });
}

function parseIndoorBikePayload(data: ArrayBuffer | Uint8Array): ParsedFtmsPayload {
  return parseMeasurement(data, {
    characteristicUuid: FTMS_CHARACTERISTICS.INDOOR_BIKE_DATA,
    machineType: "bike",
    flagBytes: 2,
    validFlagsMask: 0x1fff,
    readFields(flags, reader, metrics) {
      if (!isBitSet(flags, 0)) {
        metrics.speedMps = speedHundredthsKphToMps(reader.readUint16("speed"));
      }
      if (isBitSet(flags, 1)) {
        metrics.averageSpeedMps = speedHundredthsKphToMps(reader.readUint16("averageSpeed"));
      }
      if (isBitSet(flags, 2)) {
        metrics.cadenceRpm = scale(reader.readUint16("cadenceRpm"), 2);
      }
      if (isBitSet(flags, 3)) {
        metrics.averageCadenceRpm = scale(reader.readUint16("averageCadenceRpm"), 2);
      }
      if (isBitSet(flags, 4)) {
        metrics.distanceMeters = reader.readUint24("distanceMeters");
      }
      if (isBitSet(flags, 5)) {
        metrics.resistanceLevel = reader.readUint8("resistanceLevel");
      }
      if (isBitSet(flags, 6)) {
        metrics.powerWatts = reader.readInt16("powerWatts");
      }
      if (isBitSet(flags, 7)) {
        metrics.averagePowerWatts = reader.readInt16("averagePowerWatts");
      }
      if (isBitSet(flags, 8)) {
        readEnergy(reader, metrics);
      }
      if (isBitSet(flags, 9)) {
        metrics.hrBpm = reader.readUint8("heartRateBpm");
      }
      if (isBitSet(flags, 10)) {
        metrics.metabolicEquivalent = scale(reader.readUint8("metabolicEquivalent"), 10);
      }
      if (isBitSet(flags, 11)) {
        metrics.elapsedTimeSeconds = reader.readUint16("elapsedTimeSeconds");
      }
      if (isBitSet(flags, 12)) {
        metrics.remainingTimeSeconds = reader.readUint16("remainingTimeSeconds");
      }
    },
  });
}

/** Complete Indoor Bike Data payload, including diagnostics and optional fields. */
export function parseFtmsIndoorBikeMeasurement(data: ArrayBuffer | Uint8Array): ParsedFtmsPayload {
  return parseIndoorBikePayload(data);
}

/**
 * @deprecated Use parseFtmsIndoorBikeMeasurement for complete metrics and diagnostics.
 * This compatibility projection falls back to average values when instantaneous
 * speed, cadence, or power is absent.
 */
export function parseFtmsIndoorBikeData(data: ArrayBuffer | Uint8Array): ParsedFtmsIndoorBikeData {
  const parsed = parseIndoorBikePayload(data);
  return {
    hrBpm: parsed.metrics.hrBpm,
    powerWatts: parsed.metrics.powerWatts ?? parsed.metrics.averagePowerWatts,
    cadenceRpm: parsed.metrics.cadenceRpm ?? parsed.metrics.averageCadenceRpm,
    speedMps: parsed.metrics.speedMps ?? parsed.metrics.averageSpeedMps,
    truncated: parsed.diagnostics.truncated,
  };
}

export const FTMS_TRAINING_STATUS_LABELS: Readonly<Record<number, string>> = Object.freeze({
  0: "other",
  1: "idle",
  2: "warming_up",
  3: "low_intensity_interval",
  4: "high_intensity_interval",
  5: "recovery_interval",
  6: "isometric",
  7: "heart_rate_control",
  8: "fitness_test",
  9: "speed_outside_control_region_low",
  10: "speed_outside_control_region_high",
  11: "cool_down",
  12: "watt_control",
  13: "manual_mode",
  14: "pre_workout",
  15: "post_workout",
});

export function parseFtmsTrainingStatus(data: ArrayBuffer | Uint8Array): ParsedFtmsPayload {
  const bytes = toBytes(data);
  const view = toDataView(data);
  const issues: FtmsDiagnostic[] = [];

  if (bytes.byteLength < 2) {
    issues.push({
      code: "truncated",
      offset: bytes.byteLength,
      expected: 2,
      actual: bytes.byteLength,
    });
  }

  const flags = view.byteLength >= 1 ? view.getUint8(0) : undefined;
  const code = view.byteLength >= 2 ? view.getUint8(1) : null;
  let details: FtmsStatusPayload["details"] = null;
  let bytesRead = Math.min(bytes.byteLength, 2);

  if (code !== null && code > 0x0f) {
    issues.push({ code: "reserved_value", field: "trainingStatus", offset: 1, actual: code });
  }

  if (flags !== undefined && code !== null) {
    const stringPresent = isBitSet(flags, 0);
    const extendedStringPresent = isBitSet(flags, 1);
    const reservedFlags = flags & 0xfc;

    if (reservedFlags !== 0) {
      issues.push({ code: "reserved_flags", field: "flags", actual: reservedFlags });
    }
    if (extendedStringPresent && !stringPresent) {
      issues.push({ code: "invalid_flags", field: "flags", actual: flags });
    }

    const trainingStatusString = stringPresent ? decodeUtf8(bytes.slice(2)) : undefined;
    if (stringPresent) {
      bytesRead = bytes.byteLength;
    } else if (bytes.byteLength > 2) {
      issues.push({
        code: "trailing_bytes",
        offset: 2,
        expected: 2,
        actual: bytes.byteLength,
      });
    }

    details = {
      kind: "training_status",
      flags,
      stringPresent,
      extendedStringPresent,
      ...(trainingStatusString === undefined ? {} : { trainingStatusString }),
    };
  }

  return {
    kind: "training_status",
    characteristicUuid: FTMS_CHARACTERISTICS.TRAINING_STATUS,
    machineType: "unknown",
    metrics: createEmptyMetrics(),
    status: {
      code,
      label: code === null ? "unknown" : (FTMS_TRAINING_STATUS_LABELS[code] ?? "reserved"),
      details,
    },
    diagnostics: {
      truncated: bytes.byteLength < 2,
      ...(flags === undefined ? {} : { flags }),
      bytesRead,
      byteLength: bytes.byteLength,
      issues,
    },
  };
}

export const FTMS_MACHINE_STATUS_LABELS: Readonly<Record<number, string>> = Object.freeze({
  [FTMS_MACHINE_STATUS_OPCODES.RESET]: "reset",
  [FTMS_MACHINE_STATUS_OPCODES.STOPPED_OR_PAUSED_BY_USER]: "stopped_or_paused_by_user",
  [FTMS_MACHINE_STATUS_OPCODES.STOPPED_BY_SAFETY_KEY]: "stopped_by_safety_key",
  [FTMS_MACHINE_STATUS_OPCODES.STARTED_OR_RESUMED_BY_USER]: "started_or_resumed_by_user",
  [FTMS_MACHINE_STATUS_OPCODES.TARGET_SPEED_CHANGED]: "target_speed_changed",
  [FTMS_MACHINE_STATUS_OPCODES.TARGET_INCLINATION_CHANGED]: "target_inclination_changed",
  [FTMS_MACHINE_STATUS_OPCODES.TARGET_RESISTANCE_CHANGED]: "target_resistance_changed",
  [FTMS_MACHINE_STATUS_OPCODES.TARGET_POWER_CHANGED]: "target_power_changed",
  [FTMS_MACHINE_STATUS_OPCODES.TARGET_HEART_RATE_CHANGED]: "target_heart_rate_changed",
  [FTMS_MACHINE_STATUS_OPCODES.TARGETED_EXPENDED_ENERGY_CHANGED]:
    "targeted_expended_energy_changed",
  [FTMS_MACHINE_STATUS_OPCODES.TARGETED_STEPS_CHANGED]: "targeted_steps_changed",
  [FTMS_MACHINE_STATUS_OPCODES.TARGETED_STRIDES_CHANGED]: "targeted_strides_changed",
  [FTMS_MACHINE_STATUS_OPCODES.TARGETED_DISTANCE_CHANGED]: "targeted_distance_changed",
  [FTMS_MACHINE_STATUS_OPCODES.TARGETED_TRAINING_TIME_CHANGED]: "targeted_training_time_changed",
  [FTMS_MACHINE_STATUS_OPCODES.TARGETED_TIME_TWO_HR_ZONES_CHANGED]:
    "targeted_time_two_hr_zones_changed",
  [FTMS_MACHINE_STATUS_OPCODES.TARGETED_TIME_THREE_HR_ZONES_CHANGED]:
    "targeted_time_three_hr_zones_changed",
  [FTMS_MACHINE_STATUS_OPCODES.TARGETED_TIME_FIVE_HR_ZONES_CHANGED]:
    "targeted_time_five_hr_zones_changed",
  [FTMS_MACHINE_STATUS_OPCODES.INDOOR_BIKE_SIMULATION_PARAMETERS_CHANGED]:
    "indoor_bike_simulation_parameters_changed",
  [FTMS_MACHINE_STATUS_OPCODES.WHEEL_CIRCUMFERENCE_CHANGED]: "wheel_circumference_changed",
  [FTMS_MACHINE_STATUS_OPCODES.SPIN_DOWN_STATUS]: "spin_down_status",
  [FTMS_MACHINE_STATUS_OPCODES.TARGETED_CADENCE_CHANGED]: "targeted_cadence_changed",
  [FTMS_MACHINE_STATUS_OPCODES.CONTROL_PERMISSION_LOST]: "control_permission_lost",
});

function expectedMachineStatusLength(code: number): number | null {
  switch (code) {
    case FTMS_MACHINE_STATUS_OPCODES.RESET:
    case FTMS_MACHINE_STATUS_OPCODES.STOPPED_BY_SAFETY_KEY:
    case FTMS_MACHINE_STATUS_OPCODES.STARTED_OR_RESUMED_BY_USER:
    case FTMS_MACHINE_STATUS_OPCODES.CONTROL_PERMISSION_LOST:
      return 1;
    case FTMS_MACHINE_STATUS_OPCODES.STOPPED_OR_PAUSED_BY_USER:
    case FTMS_MACHINE_STATUS_OPCODES.TARGET_HEART_RATE_CHANGED:
    case FTMS_MACHINE_STATUS_OPCODES.SPIN_DOWN_STATUS:
      return 2;
    case FTMS_MACHINE_STATUS_OPCODES.TARGET_SPEED_CHANGED:
    case FTMS_MACHINE_STATUS_OPCODES.TARGET_INCLINATION_CHANGED:
    case FTMS_MACHINE_STATUS_OPCODES.TARGET_RESISTANCE_CHANGED:
    case FTMS_MACHINE_STATUS_OPCODES.TARGET_POWER_CHANGED:
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_EXPENDED_ENERGY_CHANGED:
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_STEPS_CHANGED:
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_STRIDES_CHANGED:
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_TRAINING_TIME_CHANGED:
    case FTMS_MACHINE_STATUS_OPCODES.WHEEL_CIRCUMFERENCE_CHANGED:
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_CADENCE_CHANGED:
      return 3;
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_DISTANCE_CHANGED:
      return 4;
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_TIME_TWO_HR_ZONES_CHANGED:
      return 5;
    case FTMS_MACHINE_STATUS_OPCODES.INDOOR_BIKE_SIMULATION_PARAMETERS_CHANGED:
      return 7;
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_TIME_THREE_HR_ZONES_CHANGED:
      return 7;
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_TIME_FIVE_HR_ZONES_CHANGED:
      return 11;
    default:
      return null;
  }
}

function decodeHrZoneSeconds(view: DataView, count: number): readonly number[] {
  const seconds: number[] = [];
  for (let index = 0; index < count; index += 1) {
    seconds.push(view.getUint16(1 + index * 2, true));
  }
  return seconds;
}

function decodeMachineStatusParameter(
  code: number,
  view: DataView,
): { details: FtmsMachineStatusParameter; parameter?: number } {
  switch (code) {
    case FTMS_MACHINE_STATUS_OPCODES.RESET:
    case FTMS_MACHINE_STATUS_OPCODES.STOPPED_BY_SAFETY_KEY:
    case FTMS_MACHINE_STATUS_OPCODES.STARTED_OR_RESUMED_BY_USER:
    case FTMS_MACHINE_STATUS_OPCODES.CONTROL_PERMISSION_LOST:
      return { details: { kind: "none" } };
    case FTMS_MACHINE_STATUS_OPCODES.STOPPED_OR_PAUSED_BY_USER: {
      const raw = view.getUint8(1);
      const action = raw === 1 ? "stop" : raw === 2 ? "pause" : "reserved";
      return { details: { kind: "stop_pause", action }, parameter: raw };
    }
    case FTMS_MACHINE_STATUS_OPCODES.TARGET_SPEED_CHANGED: {
      const speedKph = view.getUint16(1, true) / 100;
      return { details: { kind: "speed", speedKph }, parameter: speedKph };
    }
    case FTMS_MACHINE_STATUS_OPCODES.TARGET_INCLINATION_CHANGED: {
      const inclinationPercent = view.getInt16(1, true) / 10;
      return {
        details: { kind: "inclination", inclinationPercent },
        parameter: inclinationPercent,
      };
    }
    case FTMS_MACHINE_STATUS_OPCODES.TARGET_RESISTANCE_CHANGED: {
      const resistanceLevel = view.getInt16(1, true) / 10;
      return { details: { kind: "resistance", resistanceLevel }, parameter: resistanceLevel };
    }
    case FTMS_MACHINE_STATUS_OPCODES.TARGET_POWER_CHANGED: {
      const powerWatts = view.getInt16(1, true);
      return { details: { kind: "power", powerWatts }, parameter: powerWatts };
    }
    case FTMS_MACHINE_STATUS_OPCODES.TARGET_HEART_RATE_CHANGED: {
      const heartRateBpm = view.getUint8(1);
      return { details: { kind: "heart_rate", heartRateBpm }, parameter: heartRateBpm };
    }
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_EXPENDED_ENERGY_CHANGED: {
      const energyKcal = view.getUint16(1, true);
      return { details: { kind: "energy", energyKcal }, parameter: energyKcal };
    }
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_STEPS_CHANGED: {
      const steps = view.getUint16(1, true);
      return { details: { kind: "steps", steps }, parameter: steps };
    }
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_STRIDES_CHANGED: {
      const strides = view.getUint16(1, true);
      return { details: { kind: "strides", strides }, parameter: strides };
    }
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_DISTANCE_CHANGED: {
      const distanceMeters = view.getUint8(1) | (view.getUint8(2) << 8) | (view.getUint8(3) << 16);
      return { details: { kind: "distance", distanceMeters }, parameter: distanceMeters };
    }
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_TRAINING_TIME_CHANGED: {
      const seconds = view.getUint16(1, true);
      return { details: { kind: "training_time", seconds }, parameter: seconds };
    }
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_TIME_TWO_HR_ZONES_CHANGED:
      return { details: { kind: "hr_zones", seconds: decodeHrZoneSeconds(view, 2) } };
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_TIME_THREE_HR_ZONES_CHANGED:
      return { details: { kind: "hr_zones", seconds: decodeHrZoneSeconds(view, 3) } };
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_TIME_FIVE_HR_ZONES_CHANGED:
      return { details: { kind: "hr_zones", seconds: decodeHrZoneSeconds(view, 5) } };
    case FTMS_MACHINE_STATUS_OPCODES.INDOOR_BIKE_SIMULATION_PARAMETERS_CHANGED:
      return {
        details: {
          kind: "simulation",
          windSpeedMps: view.getInt16(1, true) / 1000,
          gradePercent: view.getInt16(3, true) / 100,
          crr: view.getUint8(5) / 10_000,
          cwKgPerM: view.getUint8(6) / 100,
        },
      };
    case FTMS_MACHINE_STATUS_OPCODES.WHEEL_CIRCUMFERENCE_CHANGED: {
      const circumferenceMm = view.getUint16(1, true) / 10;
      return {
        details: { kind: "wheel_circumference", circumferenceMm },
        parameter: circumferenceMm,
      };
    }
    case FTMS_MACHINE_STATUS_OPCODES.SPIN_DOWN_STATUS: {
      const raw = view.getUint8(1);
      const status =
        raw === 1
          ? "requested"
          : raw === 2
            ? "success"
            : raw === 3
              ? "error"
              : raw === 4
                ? "stop_pedaling"
                : "reserved";
      return { details: { kind: "spin_down", status }, parameter: raw };
    }
    case FTMS_MACHINE_STATUS_OPCODES.TARGETED_CADENCE_CHANGED: {
      const cadenceRpm = view.getUint16(1, true) / 2;
      return { details: { kind: "cadence", cadenceRpm }, parameter: cadenceRpm };
    }
    default:
      return { details: { kind: "none" } };
  }
}

export function parseFtmsMachineStatus(data: ArrayBuffer | Uint8Array): ParsedFtmsPayload {
  const view = toDataView(data);
  const issues: FtmsDiagnostic[] = [];
  const code = view.byteLength >= 1 ? view.getUint8(0) : null;
  let details: FtmsMachineStatusParameter | null = null;
  let parameter: number | undefined;
  let bytesRead = Math.min(view.byteLength, 1);
  let truncated = false;

  if (code === null) {
    truncated = true;
    issues.push({ code: "truncated", offset: 0, expected: 1, actual: 0 });
  } else {
    const expectedLength = expectedMachineStatusLength(code);
    if (expectedLength === null) {
      issues.push({ code: "unknown_opcode", field: "opcode", actual: code });
      bytesRead = view.byteLength;
    } else if (view.byteLength < expectedLength) {
      truncated = true;
      bytesRead = view.byteLength;
      issues.push({
        code: "truncated",
        offset: view.byteLength,
        expected: expectedLength,
        actual: view.byteLength,
      });
    } else {
      const decoded = decodeMachineStatusParameter(code, view);
      details = decoded.details;
      parameter = decoded.parameter;
      bytesRead = expectedLength;
      if (view.byteLength > expectedLength) {
        issues.push({
          code: "trailing_bytes",
          offset: expectedLength,
          expected: expectedLength,
          actual: view.byteLength,
        });
      }

      if (details.kind === "stop_pause" && details.action === "reserved") {
        issues.push({
          code: "reserved_value",
          field: "stopPause",
          ...(parameter === undefined ? {} : { actual: parameter }),
        });
      }
      if (details.kind === "spin_down" && details.status === "reserved") {
        issues.push({
          code: "reserved_value",
          field: "spinDownStatus",
          ...(parameter === undefined ? {} : { actual: parameter }),
        });
      }
    }
  }

  const status: FtmsStatusPayload = {
    code,
    label: code === null ? "unknown" : (FTMS_MACHINE_STATUS_LABELS[code] ?? "reserved"),
    ...(parameter === undefined ? {} : { parameter }),
    details,
  };

  return {
    kind: "machine_status",
    characteristicUuid: FTMS_CHARACTERISTICS.STATUS,
    machineType: "unknown",
    metrics: createEmptyMetrics(),
    status,
    diagnostics: {
      truncated,
      bytesRead,
      byteLength: view.byteLength,
      issues,
    },
  };
}

function freezeParserDefinition(definition: FtmsParserDefinition): Readonly<FtmsParserDefinition> {
  return Object.freeze(definition);
}

export const FTMS_PARSER_DEFINITIONS_BY_UUID = Object.freeze({
  [FTMS_CHARACTERISTICS.TREADMILL_DATA]: {
    uuid: FTMS_CHARACTERISTICS.TREADMILL_DATA,
    name: "Treadmill Data",
    kind: "measurement",
    machineType: "treadmill",
    parse: parseFtmsTreadmillData,
  },
  [FTMS_CHARACTERISTICS.CROSS_TRAINER_DATA]: {
    uuid: FTMS_CHARACTERISTICS.CROSS_TRAINER_DATA,
    name: "Cross Trainer Data",
    kind: "measurement",
    machineType: "cross_trainer",
    parse: parseFtmsCrossTrainerData,
  },
  [FTMS_CHARACTERISTICS.STEP_CLIMBER_DATA]: {
    uuid: FTMS_CHARACTERISTICS.STEP_CLIMBER_DATA,
    name: "Step Climber Data",
    kind: "measurement",
    machineType: "step_climber",
    parse: parseFtmsStepClimberData,
  },
  [FTMS_CHARACTERISTICS.STAIR_CLIMBER_DATA]: {
    uuid: FTMS_CHARACTERISTICS.STAIR_CLIMBER_DATA,
    name: "Stair Climber Data",
    kind: "measurement",
    machineType: "stair_climber",
    parse: parseFtmsStairClimberData,
  },
  [FTMS_CHARACTERISTICS.ROWER_DATA]: {
    uuid: FTMS_CHARACTERISTICS.ROWER_DATA,
    name: "Rower Data",
    kind: "measurement",
    machineType: "rower",
    parse: parseFtmsRowerData,
  },
  [FTMS_CHARACTERISTICS.INDOOR_BIKE_DATA]: {
    uuid: FTMS_CHARACTERISTICS.INDOOR_BIKE_DATA,
    name: "Indoor Bike Data",
    kind: "measurement",
    machineType: "bike",
    parse: parseFtmsIndoorBikeMeasurement,
  },
  [FTMS_CHARACTERISTICS.TRAINING_STATUS]: {
    uuid: FTMS_CHARACTERISTICS.TRAINING_STATUS,
    name: "Training Status",
    kind: "training_status",
    machineType: "unknown",
    parse: parseFtmsTrainingStatus,
  },
  [FTMS_CHARACTERISTICS.STATUS]: {
    uuid: FTMS_CHARACTERISTICS.STATUS,
    name: "Fitness Machine Status",
    kind: "machine_status",
    machineType: "unknown",
    parse: parseFtmsMachineStatus,
  },
} as const satisfies Record<string, FtmsParserDefinition>);

for (const definition of Object.values(FTMS_PARSER_DEFINITIONS_BY_UUID)) {
  freezeParserDefinition(definition);
}

export function getFtmsParserDefinition(uuid: string): FtmsParserDefinition | undefined {
  return (FTMS_PARSER_DEFINITIONS_BY_UUID as Record<string, FtmsParserDefinition>)[
    uuid.toLowerCase()
  ];
}

export function listFtmsParserDefinitions(): FtmsParserDefinition[] {
  return Object.values(FTMS_PARSER_DEFINITIONS_BY_UUID);
}

export function parseRegisteredFtmsPayload(
  uuid: string,
  data: ArrayBuffer | Uint8Array,
): ParsedFtmsPayload | null {
  return getFtmsParserDefinition(uuid)?.parse(data) ?? null;
}
