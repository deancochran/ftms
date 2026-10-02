import { isByteSource, toBytes } from "./binary.js";
import { FTMS_CHARACTERISTICS } from "./constants.js";
import { decodeFtmsMeasurement } from "./measurement.js";
import { type FtmsMeasurementFormatOptions, RawCodecError } from "./types.js";

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
  const decoded = decodeFtmsMeasurement(FTMS_CHARACTERISTICS.INDOOR_BIKE_DATA, bytes, options);
  if (decoded.status !== "known")
    throw new RawCodecError("kind", "Indoor Bike characteristic unavailable");
  const field = (name: keyof IndoorBikeRawFields): number | null =>
    (decoded.raw[name] as number | null | undefined) ?? null;
  const raw: IndoorBikeRawFields = {
    speedHundredthsKph: field("speedHundredthsKph"),
    averageSpeedHundredthsKph: field("averageSpeedHundredthsKph"),
    cadenceHalfRpm: field("cadenceHalfRpm"),
    averageCadenceHalfRpm: field("averageCadenceHalfRpm"),
    distanceMeters: field("distanceMeters"),
    resistance: field("resistance"),
    powerWatts: field("powerWatts"),
    averagePowerWatts: field("averagePowerWatts"),
    energyKcal: field("energyKcal"),
    energyPerHourKcal: field("energyPerHourKcal"),
    energyPerMinuteKcal: field("energyPerMinuteKcal"),
    heartRateBpm: field("heartRateBpm"),
    // biome-ignore lint/security/noSecrets: FTMS field name, not a credential.
    metabolicEquivalentTenths: field("metabolicEquivalentTenths"),
    elapsedTimeSeconds: field("elapsedTimeSeconds"),
    remainingTimeSeconds: field("remainingTimeSeconds"),
  };

  return {
    measurement: {
      speedKph: decoded.metrics.speedKph,
      speedMps: decoded.metrics.speedMps,
      averageSpeedKph: decoded.metrics.averageSpeedKph,
      averageSpeedMps: decoded.metrics.averageSpeedMps,
      cadenceRpm: decoded.metrics.cadenceRpm,
      averageCadenceRpm: decoded.metrics.averageCadenceRpm,
      distanceMeters: decoded.metrics.distanceMeters,
      resistanceLevel: decoded.metrics.resistanceLevel,
      powerWatts: decoded.metrics.powerWatts,
      averagePowerWatts: decoded.metrics.averagePowerWatts,
      energyKcal: decoded.metrics.energyKcal,
      energyPerHourKcal: decoded.metrics.energyPerHourKcal,
      energyPerMinuteKcal: decoded.metrics.energyPerMinuteKcal,
      heartRateBpm: decoded.metrics.heartRateBpm,
      metabolicEquivalent: decoded.metrics.metabolicEquivalent,
      elapsedTimeSeconds: decoded.metrics.elapsedTimeSeconds,
      remainingTimeSeconds: decoded.metrics.remainingTimeSeconds,
    },
    raw,
    diagnostics: {
      flags: decoded.diagnostics.flags,
      moreData: decoded.diagnostics.moreData,
      truncated: decoded.diagnostics.truncated,
      reservedFlags: decoded.diagnostics.reservedFlags,
      trailingBytes: decoded.diagnostics.trailingBytes,
      bytesRead: decoded.diagnostics.bytesRead,
      byteLength: bytes.length,
      unavailableFields: decoded.diagnostics.unavailableFields as (keyof IndoorBikeRawFields)[],
    },
  };
}
