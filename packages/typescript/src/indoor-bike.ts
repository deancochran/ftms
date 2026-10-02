import { isByteSource, toBytes } from "./binary.js";
import { decodeFtmsMeasurementRaw } from "./parsers.js";
import {
  type FtmsMeasurementFormatOptions,
  type FtmsMeasurementRaw,
  RawCodecError,
} from "./types.js";

/** Indoor Bike values in physical units. Null means absent, incomplete or
 * unavailable; diagnostics retain unavailable-field evidence. Zero is a value. */
export interface IndoorBikeMeasurement {
  speedKph: number | null;
  speedMps: number | null;
  averageSpeedKph: number | null;
  averageSpeedMps: number | null;
  cadenceRpm: number | null;
  averageCadenceRpm: number | null;
  distanceMeters: number | null;
  resistanceLevel: number | null;
  powerWatts: number | null;
  averagePowerWatts: number | null;
  energyKcal: number | null;
  energyPerHourKcal: number | null;
  energyPerMinuteKcal: number | null;
  heartRateBpm: number | null;
  metabolicEquivalent: number | null;
  elapsedTimeSeconds: number | null;
  remainingTimeSeconds: number | null;
}

/** Named, unscaled wire integers. Resistance follows the explicitly selected
 * format: unsigned whole levels by default, signed tenths with signed16Tenths.
 * Sentinels are null, not fabricated physical values or zeros. */
export interface IndoorBikeRawFields {
  speedHundredthsKph: number | null;
  averageSpeedHundredthsKph: number | null;
  cadenceHalfRpm: number | null;
  averageCadenceHalfRpm: number | null;
  distanceMeters: number | null;
  resistance: number | null;
  powerWatts: number | null;
  averagePowerWatts: number | null;
  energyKcal: number | null;
  energyPerHourKcal: number | null;
  energyPerMinuteKcal: number | null;
  heartRateBpm: number | null;
  metabolicEquivalentTenths: number | null;
  elapsedTimeSeconds: number | null;
  remainingTimeSeconds: number | null;
}

export interface IndoorBikeDiagnostics {
  /** Null if the two-byte flags field is incomplete. */
  flags: number | null;
  /** Null if flags are incomplete; this function does not assemble fragments. */
  moreData: boolean | null;
  truncated: boolean;
  reservedFlags: boolean;
  trailingBytes: number;
  bytesRead: number;
  byteLength: number;
  unavailableFields: (keyof IndoorBikeRawFields)[];
}

export interface DecodedIndoorBikeData {
  measurement: IndoorBikeMeasurement;
  raw: IndoorBikeRawFields;
  diagnostics: IndoorBikeDiagnostics;
}

const scale = (value: number | null, factor: number): number | null =>
  value === null ? null : value * factor;

/** Decode one Indoor Bike Data value (0x2AD2), not a connection or assembled
 * record. Uses the existing raw codec; performs no device/layout inference.
 *
 * Truncated packets return complete earlier fields plus diagnostics, including
 * packets with incomplete flags. Invalid input types/options throw RawCodecError.
 * Both speed units derive directly from the wire integer (no round trip).
 */
export function decodeIndoorBikeData(
  data: Uint8Array | ArrayBuffer,
  options?: FtmsMeasurementFormatOptions,
): DecodedIndoorBikeData {
  if (!isByteSource(data))
    throw new RawCodecError("null", "Indoor Bike input must be an ArrayBuffer or Uint8Array");
  const bytes = toBytes(data);
  let decoded: FtmsMeasurementRaw | null;
  try {
    decoded = decodeFtmsMeasurementRaw(5, bytes, options);
  } catch (error) {
    // The raw codec validates options before requiring a complete flags field.
    if (!(error instanceof RawCodecError) || error.code !== "length" || bytes.length >= 2)
      throw error;
    decoded = null;
  }

  const unavailableFields: (keyof IndoorBikeRawFields)[] = [];
  const field = (name: keyof IndoorBikeRawFields, index: number): number | null => {
    if (decoded === null || !(decoded.present & (1 << index))) return null;
    if (decoded.unavailable & (1 << index)) {
      unavailableFields.push(name);
      return null;
    }
    return decoded.values[index] as number;
  };
  // These indices belong to the shared raw codec contract, never caller code.
  const raw: IndoorBikeRawFields = {
    speedHundredthsKph: field("speedHundredthsKph", 0),
    averageSpeedHundredthsKph: field("averageSpeedHundredthsKph", 1),
    cadenceHalfRpm: field("cadenceHalfRpm", 28),
    averageCadenceHalfRpm: field("averageCadenceHalfRpm", 29),
    distanceMeters: field("distanceMeters", 2),
    resistance: field("resistance", 21),
    powerWatts: field("powerWatts", 17),
    averagePowerWatts: field("averagePowerWatts", 22),
    energyKcal: field("energyKcal", 9),
    energyPerHourKcal: field("energyPerHourKcal", 10),
    energyPerMinuteKcal: field("energyPerMinuteKcal", 11),
    heartRateBpm: field("heartRateBpm", 12),
    // biome-ignore lint/security/noSecrets: FTMS field name, not a credential.
    metabolicEquivalentTenths: field("metabolicEquivalentTenths", 13),
    elapsedTimeSeconds: field("elapsedTimeSeconds", 14),
    remainingTimeSeconds: field("remainingTimeSeconds", 15),
  };

  return {
    measurement: {
      speedKph: scale(raw.speedHundredthsKph, 0.01),
      speedMps: raw.speedHundredthsKph === null ? null : raw.speedHundredthsKph / 360,
      averageSpeedKph: scale(raw.averageSpeedHundredthsKph, 0.01),
      averageSpeedMps:
        raw.averageSpeedHundredthsKph === null ? null : raw.averageSpeedHundredthsKph / 360,
      cadenceRpm: scale(raw.cadenceHalfRpm, 0.5),
      averageCadenceRpm: scale(raw.averageCadenceHalfRpm, 0.5),
      distanceMeters: raw.distanceMeters,
      resistanceLevel:
        options?.resistanceFormat === "signed16Tenths"
          ? scale(raw.resistance, 0.1)
          : raw.resistance,
      powerWatts: raw.powerWatts,
      averagePowerWatts: raw.averagePowerWatts,
      energyKcal: raw.energyKcal,
      energyPerHourKcal: raw.energyPerHourKcal,
      energyPerMinuteKcal: raw.energyPerMinuteKcal,
      heartRateBpm: raw.heartRateBpm,
      metabolicEquivalent: scale(raw.metabolicEquivalentTenths, 0.1),
      elapsedTimeSeconds: raw.elapsedTimeSeconds,
      remainingTimeSeconds: raw.remainingTimeSeconds,
    },
    raw,
    diagnostics: {
      flags: decoded?.flags ?? null,
      moreData: decoded === null ? null : decoded.moreData !== 0,
      truncated: decoded === null || decoded.truncated !== 0,
      reservedFlags: decoded !== null && decoded.reservedFlags !== 0,
      trailingBytes: decoded?.trailingBytes ? bytes.length - decoded.bytesRead : 0,
      bytesRead: decoded?.bytesRead ?? 0,
      byteLength: bytes.length,
      unavailableFields,
    },
  };
}
