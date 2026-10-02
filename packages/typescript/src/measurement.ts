import { isByteSource, toBytes } from "./binary.js";
import { FTMS_CHARACTERISTICS } from "./constants.js";
import { decodeFtmsMeasurementRaw } from "./parsers.js";
import {
  type FtmsMeasurementFormatOptions,
  type FtmsMeasurementRaw,
  type FtmsRuntimeMetrics,
  RawCodecError,
} from "./types.js";

/** A machine-data family supported by {@link decodeFtmsMeasurement}. */
export type FtmsMeasurementFamily =
  | "treadmill"
  | "cross_trainer"
  | "step_climber"
  | "stair_climber"
  | "rower"
  | "bike";

export type FtmsMeasurementDecodeResult =
  | {
      readonly status: "known";
      readonly family: FtmsMeasurementFamily;
      readonly characteristicUuid: string;
      /** Common physical-unit metrics. A metric does not require a family switch. */
      readonly metrics: FtmsUniversalMeasurementMetrics;
      /** Named, unscaled wire values. Null means absent, truncated, or unavailable. */
      readonly raw: FtmsUniversalMeasurementRaw;
      readonly diagnostics: FtmsUniversalMeasurementDiagnostics;
    }
  | { readonly status: "unsupported"; readonly characteristicUuid: string };

export interface FtmsUniversalMeasurementDiagnostics {
  readonly flags: number | null;
  readonly moreData: boolean | null;
  readonly backward: boolean | null;
  readonly truncated: boolean;
  readonly reservedFlags: boolean;
  readonly trailingBytes: number;
  readonly bytesRead: number;
  readonly byteLength: number;
  readonly unavailableFields: readonly (keyof FtmsUniversalMeasurementRaw)[];
}

/** Physical values shared across current FTMS measurement families. */
export interface FtmsUniversalMeasurementMetrics extends FtmsRuntimeMetrics {
  readonly speedKph: number | null;
  readonly averageSpeedKph: number | null;
  readonly heartRateBpm: number | null;
}

/** Named wire values. A field is null when this family does not select it, its
 * packet is truncated, or FTMS marks it unavailable. Values retain wire units. */
export interface FtmsUniversalMeasurementRaw {
  readonly speedHundredthsKph: number | null;
  readonly averageSpeedHundredthsKph: number | null;
  readonly distanceMeters: number | null;
  readonly inclinationTenthsPercent: number | null;
  readonly rampAngleTenthsDegrees: number | null;
  /** Treadmill: tenths of metres; all other applicable families: metres. */
  readonly positiveElevationRaw: number | null;
  /** Treadmill: tenths of metres; all other applicable families: metres. */
  readonly negativeElevationRaw: number | null;
  /** Seconds per 500 m in the standard layouts. The uint8Legacy treadmill
   * layout retains an integer with unresolved units; no physical value is inferred. */
  readonly instantaneousPaceRaw: number | null;
  /** Same wire-unit contract as instantaneousPaceRaw. */
  readonly averagePaceRaw: number | null;
  readonly energyKcal: number | null;
  readonly energyPerHourKcal: number | null;
  readonly energyPerMinuteKcal: number | null;
  readonly heartRateBpm: number | null;
  readonly metabolicEquivalentTenths: number | null;
  readonly elapsedTimeSeconds: number | null;
  readonly remainingTimeSeconds: number | null;
  readonly forceOnBeltNewtons: number | null;
  readonly powerWatts: number | null;
  readonly stepRateSpm: number | null;
  readonly averageStepRateSpm: number | null;
  /** Cross Trainer: tenths of strides; Stair Climber: whole strides. */
  readonly strideCountRaw: number | null;
  /** Whole UINT8 by default; signed INT16 tenths with signed16Tenths. */
  readonly resistance: number | null;
  readonly averagePowerWatts: number | null;
  readonly floorCount: number | null;
  readonly stepCount: number | null;
  readonly strokeRateHalfSpm: number | null;
  readonly strokeCount: number | null;
  readonly averageStrokeRateHalfSpm: number | null;
  readonly cadenceHalfRpm: number | null;
  readonly averageCadenceHalfRpm: number | null;
}

const BASE_UUID_SUFFIX = "-0000-1000-8000-00805f9b34fb";

/** Normalize the standard 16-bit, 0x-prefixed, and full Bluetooth UUID spellings. */
function normalizeFtmsCharacteristicUuid(uuid: string): string {
  const value = uuid.trim().toLowerCase();
  const short = value.startsWith("0x") ? value.slice(2) : value;
  return /^[0-9a-f]{4}$/.test(short) ? `0000${short}${BASE_UUID_SUFFIX}` : value;
}

const definitions = [
  [FTMS_CHARACTERISTICS.TREADMILL_DATA, "treadmill", 0],
  [FTMS_CHARACTERISTICS.CROSS_TRAINER_DATA, "cross_trainer", 1],
  [FTMS_CHARACTERISTICS.STEP_CLIMBER_DATA, "step_climber", 2],
  [FTMS_CHARACTERISTICS.STAIR_CLIMBER_DATA, "stair_climber", 3],
  [FTMS_CHARACTERISTICS.ROWER_DATA, "rower", 4],
  [FTMS_CHARACTERISTICS.INDOOR_BIKE_DATA, "bike", 5],
] as const satisfies readonly (readonly [string, FtmsMeasurementFamily, number])[];

const byUuid: ReadonlyMap<string, (typeof definitions)[number]> = new Map(
  definitions.map((definition) => [definition[0], definition]),
);
const rawNames = [
  "speedHundredthsKph",
  "averageSpeedHundredthsKph",
  "distanceMeters",
  "inclinationTenthsPercent",
  "rampAngleTenthsDegrees",
  "positiveElevationRaw",
  "negativeElevationRaw",
  "instantaneousPaceRaw",
  "averagePaceRaw",
  "energyKcal",
  "energyPerHourKcal",
  "energyPerMinuteKcal",
  "heartRateBpm",
  // biome-ignore lint/security/noSecrets: public FTMS field name, not a credential.
  "metabolicEquivalentTenths",
  "elapsedTimeSeconds",
  "remainingTimeSeconds",
  "forceOnBeltNewtons",
  "powerWatts",
  "stepRateSpm",
  "averageStepRateSpm",
  "strideCountRaw",
  "resistance",
  "averagePowerWatts",
  "floorCount",
  "stepCount",
  "strokeRateHalfSpm",
  "strokeCount",
  "averageStrokeRateHalfSpm",
  "cadenceHalfRpm",
  "averageCadenceHalfRpm",
] as const satisfies readonly (keyof FtmsUniversalMeasurementRaw)[];

function emptyRaw(): { -readonly [K in keyof FtmsUniversalMeasurementRaw]: number | null } {
  return Object.fromEntries(rawNames.map((name) => [name, null])) as {
    -readonly [K in keyof FtmsUniversalMeasurementRaw]: number | null;
  };
}

function projectMetrics(
  raw: FtmsUniversalMeasurementRaw,
  family: FtmsMeasurementFamily,
  options: FtmsMeasurementFormatOptions | undefined,
): FtmsUniversalMeasurementMetrics {
  const scale = (value: number | null, factor: number) => (value === null ? null : value * factor);
  const speedKph = scale(raw.speedHundredthsKph, 0.01);
  const averageSpeedKph = scale(raw.averageSpeedHundredthsKph, 0.01);
  const elevationDivisor = family === "treadmill" ? 10 : 1;
  return {
    hrBpm: raw.heartRateBpm,
    heartRateBpm: raw.heartRateBpm,
    powerWatts: raw.powerWatts,
    averagePowerWatts: raw.averagePowerWatts,
    cadenceRpm: scale(raw.cadenceHalfRpm, 0.5),
    averageCadenceRpm: scale(raw.averageCadenceHalfRpm, 0.5),
    speedMps: raw.speedHundredthsKph === null ? null : raw.speedHundredthsKph / 360,
    averageSpeedMps:
      raw.averageSpeedHundredthsKph === null ? null : raw.averageSpeedHundredthsKph / 360,
    speedKph,
    averageSpeedKph,
    distanceMeters: raw.distanceMeters,
    elapsedTimeSeconds: raw.elapsedTimeSeconds,
    remainingTimeSeconds: raw.remainingTimeSeconds,
    energyKcal: raw.energyKcal,
    energyPerHourKcal: raw.energyPerHourKcal,
    energyPerMinuteKcal: raw.energyPerMinuteKcal,
    metabolicEquivalent: scale(raw.metabolicEquivalentTenths, 0.1),
    stepCount: raw.stepCount,
    stepRateSpm: raw.stepRateSpm,
    averageStepRateSpm: raw.averageStepRateSpm,
    strideCount: family === "cross_trainer" ? scale(raw.strideCountRaw, 0.1) : raw.strideCountRaw,
    floorCount: raw.floorCount,
    positiveElevationGainMeters: scale(raw.positiveElevationRaw, 1 / elevationDivisor),
    negativeElevationGainMeters: scale(raw.negativeElevationRaw, 1 / elevationDivisor),
    inclinationPercent: scale(raw.inclinationTenthsPercent, 0.1),
    rampAngleDegrees: scale(raw.rampAngleTenthsDegrees, 0.1),
    resistanceLevel:
      raw.resistance === null
        ? null
        : options?.resistanceFormat === "signed16Tenths"
          ? raw.resistance * 0.1
          : raw.resistance,
    instantaneousPaceSecondsPer500m:
      family === "treadmill" && options?.treadmillPaceFormat === "uint8Legacy"
        ? null
        : raw.instantaneousPaceRaw,
    averagePaceSecondsPer500m:
      family === "treadmill" && options?.treadmillPaceFormat === "uint8Legacy"
        ? null
        : raw.averagePaceRaw,
    forceOnBeltNewtons: raw.forceOnBeltNewtons,
    strokeRateSpm: scale(raw.strokeRateHalfSpm, 0.5),
    averageStrokeRateSpm: scale(raw.averageStrokeRateHalfSpm, 0.5),
    strokeCount: raw.strokeCount,
    movementDirection: null,
  };
}

/**
 * Decode any currently specified FTMS machine-data characteristic. The UUID,
 * rather than packet shape, selects the layout. Status and unknown characteristics
 * are explicitly unsupported by this measurement-only function.
 */
export function decodeFtmsMeasurement(
  characteristicUuid: string,
  data: Uint8Array | ArrayBuffer,
  options?: FtmsMeasurementFormatOptions,
): FtmsMeasurementDecodeResult {
  if (typeof characteristicUuid !== "string")
    throw new RawCodecError("kind", "Characteristic UUID must be a string");
  if (!isByteSource(data))
    throw new RawCodecError("null", "Measurement input must be an ArrayBuffer or Uint8Array");
  const uuid = normalizeFtmsCharacteristicUuid(characteristicUuid);
  const definition = byUuid.get(uuid);
  if (definition === undefined) return { status: "unsupported", characteristicUuid: uuid };
  const bytes = toBytes(data);
  let rawDecoded: FtmsMeasurementRaw;
  try {
    rawDecoded = decodeFtmsMeasurementRaw(definition[2], bytes, options);
  } catch (error) {
    if (!(error instanceof RawCodecError) || error.code !== "length") throw error;
    const raw = emptyRaw();
    return {
      status: "known",
      family: definition[1],
      characteristicUuid: uuid,
      metrics: projectMetrics(raw, definition[1], options),
      raw,
      diagnostics: {
        flags: null,
        moreData: null,
        backward: null,
        truncated: true,
        reservedFlags: false,
        trailingBytes: 0,
        bytesRead: 0,
        byteLength: bytes.length,
        unavailableFields: [],
      },
    };
  }
  const unavailableFields: (keyof FtmsUniversalMeasurementRaw)[] = [];
  const raw = emptyRaw();
  rawNames.forEach((name, index) => {
    const present = (rawDecoded.present & (1 << index)) !== 0;
    const unavailable = (rawDecoded.unavailable & (1 << index)) !== 0;
    if (unavailable) unavailableFields.push(name);
    raw[name] = present && !unavailable ? (rawDecoded.values[index] ?? null) : null;
  });
  const metrics = projectMetrics(raw, definition[1], options);
  if (definition[1] === "cross_trainer")
    metrics.movementDirection = rawDecoded.backward ? "backward" : "forward";
  return {
    status: "known",
    family: definition[1],
    characteristicUuid: uuid,
    metrics,
    raw,
    diagnostics: {
      flags: rawDecoded.flags,
      moreData: rawDecoded.moreData !== 0,
      backward: definition[1] === "cross_trainer" ? rawDecoded.backward !== 0 : null,
      truncated: rawDecoded.truncated !== 0,
      reservedFlags: rawDecoded.reservedFlags !== 0,
      trailingBytes: rawDecoded.trailingBytes ? bytes.length - rawDecoded.bytesRead : 0,
      bytesRead: rawDecoded.bytesRead,
      byteLength: bytes.length,
      unavailableFields,
    },
  };
}
