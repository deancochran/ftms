import { describe, expect, it } from "vitest";
import {
  decodeFtmsFeatures,
  decodeFtmsRange,
  decodeSupportedHeartRateRange,
  decodeSupportedInclinationRange,
  decodeSupportedPowerRange,
  decodeSupportedResistanceRange,
  decodeSupportedSpeedRange,
  type FTMSFeatures,
  type FtmsRange,
  type FtmsRangeKind,
} from "../src/index.js";

const machineFeatureCases: ReadonlyArray<{ name: keyof FTMSFeatures; bit: number }> = [
  { name: "averageSpeedSupported", bit: 0 },
  { name: "cadenceSupported", bit: 1 },
  { name: "totalDistanceSupported", bit: 2 },
  { name: "inclinationSupported", bit: 3 },
  { name: "elevationGainSupported", bit: 4 },
  { name: "paceSupported", bit: 5 },
  { name: "stepCountSupported", bit: 6 },
  { name: "resistanceLevelSupported", bit: 7 },
  { name: "strideCountSupported", bit: 8 },
  { name: "expendedEnergySupported", bit: 9 },
  { name: "heartRateMeasurementSupported", bit: 10 },
  { name: "metabolicEquivalentSupported", bit: 11 },
  { name: "elapsedTimeSupported", bit: 12 },
  { name: "remainingTimeSupported", bit: 13 },
  { name: "powerMeasurementSupported", bit: 14 },
  { name: "forceOnBeltSupported", bit: 15 },
  { name: "userDataRetentionSupported", bit: 16 },
];

const targetFeatureCases: ReadonlyArray<{ name: keyof FTMSFeatures; bit: number }> = [
  { name: "speedTargetSettingSupported", bit: 0 },
  { name: "inclinationTargetSettingSupported", bit: 1 },
  { name: "resistanceTargetSettingSupported", bit: 2 },
  { name: "powerTargetSettingSupported", bit: 3 },
  { name: "heartRateTargetSettingSupported", bit: 4 },
  { name: "targetedExpendedEnergySupported", bit: 5 },
  { name: "targetedStepNumberSupported", bit: 6 },
  { name: "targetedStrideNumberSupported", bit: 7 },
  { name: "targetedDistanceSupported", bit: 8 },
  { name: "targetedTrainingTimeSupported", bit: 9 },
  { name: "targetedTimeTwoHRZonesSupported", bit: 10 },
  { name: "targetedTimeThreeHRZonesSupported", bit: 11 },
  { name: "targetedTimeFiveHRZonesSupported", bit: 12 },
  { name: "indoorBikeSimulationSupported", bit: 13 },
  { name: "wheelCircumferenceSupported", bit: 14 },
  { name: "spinDownControlSupported", bit: 15 },
  { name: "targetedCadenceSupported", bit: 16 },
];

function featurePayload(machineWord: number, targetWord: number): Uint8Array {
  const bytes = new Uint8Array(8);
  const view = new DataView(bytes.buffer);
  view.setUint32(0, machineWord, true);
  view.setUint32(4, targetWord, true);
  return bytes;
}

describe("decodeFtmsFeatures", () => {
  it.each(machineFeatureCases)("decodes machine feature bit $bit as $name", ({ name, bit }) => {
    const result = decodeFtmsFeatures(featurePayload(2 ** bit, 0));
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value[name]).toBe(true);
    }
  });

  it.each(targetFeatureCases)("decodes target feature bit $bit as $name", ({ name, bit }) => {
    const result = decodeFtmsFeatures(featurePayload(0, 2 ** bit));
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value[name]).toBe(true);
    }
  });

  it("keeps compatibility aliases aligned with canonical target bits", () => {
    const result = decodeFtmsFeatures(featurePayload(0, (2 ** 2) | (2 ** 3) | (2 ** 13)));
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.supportsERG).toBe(true);
      expect(result.value.supportsSIM).toBe(true);
      expect(result.value.supportsResistance).toBe(true);
    }
  });

  it.each([0, 7, 9])("rejects a payload with %i bytes", (length) => {
    const result = decodeFtmsFeatures(new Uint8Array(length));
    expect(result).toMatchObject({
      ok: false,
      error: { code: "length", expected: 8, actual: length },
    });
  });
});

interface RangeCase {
  name: string;
  decode: (bytes: Uint8Array) => { ok: true; value: FtmsRange } | { ok: false };
  valid: number[];
  expected: Partial<FtmsRange>;
  wrongLength: number;
  reversed: number[];
  zeroIncrement: number[];
}

const rangeCases: readonly RangeCase[] = [
  {
    name: "speed",
    decode: decodeSupportedSpeedRange,
    valid: [0xf4, 0x01, 0xb8, 0x0b, 0x32, 0x00],
    expected: { min: 5, max: 30, increment: 0.5, unit: "km/h" },
    wrongLength: 5,
    reversed: [0xd0, 0x07, 0xe8, 0x03, 0x01, 0x00],
    zeroIncrement: [0xe8, 0x03, 0xd0, 0x07, 0x00, 0x00],
  },
  {
    name: "inclination",
    decode: decodeSupportedInclinationRange,
    valid: [0x9c, 0xff, 0x90, 0x01, 0x05, 0x00],
    expected: { min: -10, max: 40, increment: 0.5, unit: "percent" },
    wrongLength: 5,
    reversed: [0x64, 0x00, 0x9c, 0xff, 0x01, 0x00],
    zeroIncrement: [0x9c, 0xff, 0x64, 0x00, 0x00, 0x00],
  },
  {
    name: "resistance",
    decode: decodeSupportedResistanceRange,
    valid: [1, 100, 1],
    expected: { min: 1, max: 100, increment: 1, unit: "level" },
    wrongLength: 6,
    reversed: [100, 1, 1],
    zeroIncrement: [1, 100, 0],
  },
  {
    name: "heart rate",
    decode: decodeSupportedHeartRateRange,
    valid: [60, 200, 1],
    expected: { min: 60, max: 200, increment: 1, unit: "bpm" },
    wrongLength: 6,
    reversed: [200, 60, 1],
    zeroIncrement: [60, 200, 0],
  },
  {
    name: "power",
    decode: decodeSupportedPowerRange,
    valid: [0x9c, 0xff, 0xa0, 0x0f, 0x05, 0x00],
    expected: { min: -100, max: 4000, increment: 5, unit: "watts" },
    wrongLength: 5,
    reversed: [0xe8, 0x03, 0x64, 0x00, 0x01, 0x00],
    zeroIncrement: [0x00, 0x00, 0xe8, 0x03, 0x00, 0x00],
  },
];

describe("supported range decoders", () => {
  it.each(rangeCases)("decodes the $name range", ({ decode, valid, expected }) => {
    const result = decode(Uint8Array.from(valid));
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value).toMatchObject(expected);
    }
  });

  it.each(rangeCases)("rejects the wrong byte length for the $name range", ({
    decode,
    wrongLength,
  }) => {
    expect(decode(new Uint8Array(wrongLength))).toMatchObject({
      ok: false,
      error: { code: "length" },
    });
  });

  it.each(rangeCases)("rejects reversed $name bounds", ({ decode, reversed }) => {
    expect(decode(Uint8Array.from(reversed))).toMatchObject({
      ok: false,
      error: { code: "range" },
    });
  });

  it.each(rangeCases)("rejects a zero $name increment", ({ decode, zeroIncrement }) => {
    expect(decode(Uint8Array.from(zeroIncrement))).toMatchObject({
      ok: false,
      error: { code: "range" },
    });
  });

  it("rejects an unsupported range kind at runtime", () => {
    expect(decodeFtmsRange("unsupported" as FtmsRangeKind, new Uint8Array(6))).toMatchObject({
      ok: false,
      error: { code: "kind" },
    });
  });

  it.each([
    { kind: "speed" as const, bytes: [0, 0, 1, 0, 0, 0], offset: 4 },
    { kind: "heartRate" as const, bytes: [1, 2, 0], offset: 2 },
  ])("reports the $kind increment at its wire offset", ({ kind, bytes, offset }) => {
    expect(decodeFtmsRange(kind, Uint8Array.from(bytes))).toMatchObject({
      ok: false,
      error: { code: "range", offset },
    });
  });
});
