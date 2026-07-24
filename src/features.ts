import type { FTMSFeatures } from "./types.js";

export interface FtmsDecodeErrorDetails {
  code: "length" | "range";
  offset: number;
  expected: number;
  actual: number;
  message: string;
}

export type FtmsDecodeError = { ok: false; error: FtmsDecodeErrorDetails };
export type FtmsDecodeSuccess<T> = { ok: true; value: T };
export type FtmsDecodeResult<T> = FtmsDecodeSuccess<T> | FtmsDecodeError;

export type FtmsRangeKind = "speed" | "inclination" | "resistance" | "heartRate" | "power";

export interface FtmsRange {
  kind: FtmsRangeKind;
  min: number;
  max: number;
  increment: number;
  unit: "km/h" | "percent" | "level" | "bpm" | "watts";
}

function toDataView(data: ArrayBuffer | Uint8Array): DataView {
  return data instanceof Uint8Array
    ? new DataView(data.buffer, data.byteOffset, data.byteLength)
    : new DataView(data);
}

function lengthError(actual: number, expected: number): FtmsDecodeError {
  return {
    ok: false,
    error: {
      code: "length",
      offset: 0,
      expected,
      actual,
      message: `Expected exactly ${expected} bytes, received ${actual}`,
    },
  };
}

function isBitSet(word: number, bit: number): boolean {
  return (word & (2 ** bit)) !== 0;
}

export function decodeFtmsFeatures(data: ArrayBuffer | Uint8Array): FtmsDecodeResult<FTMSFeatures> {
  const view = toDataView(data);
  if (view.byteLength !== 8) {
    return lengthError(view.byteLength, 8);
  }

  const machine = view.getUint32(0, true);
  const target = view.getUint32(4, true);
  const powerTargetSettingSupported = isBitSet(target, 3);
  const indoorBikeSimulationSupported = isBitSet(target, 13);
  const resistanceTargetSettingSupported = isBitSet(target, 2);

  return {
    ok: true,
    value: {
      averageSpeedSupported: isBitSet(machine, 0),
      cadenceSupported: isBitSet(machine, 1),
      totalDistanceSupported: isBitSet(machine, 2),
      inclinationSupported: isBitSet(machine, 3),
      elevationGainSupported: isBitSet(machine, 4),
      paceSupported: isBitSet(machine, 5),
      stepCountSupported: isBitSet(machine, 6),
      resistanceLevelSupported: isBitSet(machine, 7),
      strideCountSupported: isBitSet(machine, 8),
      expendedEnergySupported: isBitSet(machine, 9),
      heartRateMeasurementSupported: isBitSet(machine, 10),
      metabolicEquivalentSupported: isBitSet(machine, 11),
      elapsedTimeSupported: isBitSet(machine, 12),
      remainingTimeSupported: isBitSet(machine, 13),
      powerMeasurementSupported: isBitSet(machine, 14),
      forceOnBeltSupported: isBitSet(machine, 15),
      userDataRetentionSupported: isBitSet(machine, 16),
      speedTargetSettingSupported: isBitSet(target, 0),
      inclinationTargetSettingSupported: isBitSet(target, 1),
      resistanceTargetSettingSupported,
      powerTargetSettingSupported,
      heartRateTargetSettingSupported: isBitSet(target, 4),
      targetedExpendedEnergySupported: isBitSet(target, 5),
      targetedStepNumberSupported: isBitSet(target, 6),
      targetedStrideNumberSupported: isBitSet(target, 7),
      targetedDistanceSupported: isBitSet(target, 8),
      targetedTrainingTimeSupported: isBitSet(target, 9),
      targetedTimeTwoHRZonesSupported: isBitSet(target, 10),
      targetedTimeThreeHRZonesSupported: isBitSet(target, 11),
      targetedTimeFiveHRZonesSupported: isBitSet(target, 12),
      indoorBikeSimulationSupported,
      wheelCircumferenceSupported: isBitSet(target, 14),
      spinDownControlSupported: isBitSet(target, 15),
      targetedCadenceSupported: isBitSet(target, 16),
      supportsERG: powerTargetSettingSupported,
      supportsSIM: indoorBikeSimulationSupported,
      supportsResistance: resistanceTargetSettingSupported,
    },
  };
}

function rangeError(min: number, max: number, increment: number): FtmsDecodeError {
  const invalidMinimum = min > max;
  return {
    ok: false,
    error: {
      code: "range",
      offset: invalidMinimum ? 0 : 2,
      expected: 1,
      actual: invalidMinimum ? min - max : increment,
      message: invalidMinimum
        ? "Minimum must not exceed maximum"
        : "Increment must be greater than zero",
    },
  };
}

export function decodeFtmsRange(
  kind: FtmsRangeKind,
  data: ArrayBuffer | Uint8Array,
): FtmsDecodeResult<FtmsRange> {
  const view = toDataView(data);
  const expectedLength = kind === "heartRate" || kind === "resistance" ? 3 : 6;
  if (view.byteLength !== expectedLength) {
    return lengthError(view.byteLength, expectedLength);
  }

  let min: number;
  let max: number;
  let increment: number;
  let unit: FtmsRange["unit"];

  switch (kind) {
    case "speed":
      min = view.getUint16(0, true) / 100;
      max = view.getUint16(2, true) / 100;
      increment = view.getUint16(4, true) / 100;
      unit = "km/h";
      break;
    case "inclination":
      min = view.getInt16(0, true) / 10;
      max = view.getInt16(2, true) / 10;
      increment = view.getUint16(4, true) / 10;
      unit = "percent";
      break;
    case "power":
      min = view.getInt16(0, true);
      max = view.getInt16(2, true);
      increment = view.getUint16(4, true);
      unit = "watts";
      break;
    case "heartRate":
      min = view.getUint8(0);
      max = view.getUint8(1);
      increment = view.getUint8(2);
      unit = "bpm";
      break;
    case "resistance":
      min = view.getUint8(0);
      max = view.getUint8(1);
      increment = view.getUint8(2);
      unit = "level";
      break;
  }

  if (min > max || increment <= 0) {
    return rangeError(min, max, increment);
  }

  return { ok: true, value: { kind, min, max, increment, unit } };
}

export function decodeSupportedSpeedRange(
  data: ArrayBuffer | Uint8Array,
): FtmsDecodeResult<FtmsRange> {
  return decodeFtmsRange("speed", data);
}

export function decodeSupportedInclinationRange(
  data: ArrayBuffer | Uint8Array,
): FtmsDecodeResult<FtmsRange> {
  return decodeFtmsRange("inclination", data);
}

export function decodeSupportedResistanceRange(
  data: ArrayBuffer | Uint8Array,
): FtmsDecodeResult<FtmsRange> {
  return decodeFtmsRange("resistance", data);
}

export function decodeSupportedHeartRateRange(
  data: ArrayBuffer | Uint8Array,
): FtmsDecodeResult<FtmsRange> {
  return decodeFtmsRange("heartRate", data);
}

export function decodeSupportedPowerRange(
  data: ArrayBuffer | Uint8Array,
): FtmsDecodeResult<FtmsRange> {
  return decodeFtmsRange("power", data);
}
