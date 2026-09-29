import { runInNewContext } from "node:vm";
import { describe, expect, it } from "vitest";
import {
  decodeFtmsControlRequestRaw,
  decodeFtmsMeasurementRaw,
  decodeFtmsRangeRaw,
  encodeFtmsControlRequestRaw,
  encodeFtmsMeasurementRaw,
  encodeFtmsRangeRaw,
  evaluateFtmsCapabilities,
  RawCodecError,
  tryEncodeFtmsControlRequest,
} from "../src/index.js";

describe("explicit configuration boundaries", () => {
  it("rejects inherited control selections in every entry point", () => {
    const options = Object.create({ resistanceFormat: "uint8Tenths" });
    expect(() => encodeFtmsControlRequestRaw({ opcode: 4, operands: [123] }, options)).toThrow(
      RawCodecError,
    );
    expect(() => decodeFtmsControlRequestRaw(Uint8Array.of(4, 123), options)).toThrow(
      RawCodecError,
    );
    expect(
      tryEncodeFtmsControlRequest({ op: "setTargetResistance", resistanceLevel: 12.3 }, options),
    ).toMatchObject({ ok: false, error: { code: "invalid_request" } });
  });
  it("rejects inherited range and measurement profiles on encode and decode", () => {
    const options = Object.create({ resistanceFormat: "signed16Tenths" });
    expect(() =>
      decodeFtmsRangeRaw("resistance", Uint8Array.of(0, 0, 10, 0, 1, 0), options),
    ).toThrow(RawCodecError);
    expect(() =>
      encodeFtmsRangeRaw(
        { kind: "resistance", minimum: 0, maximum: 10, increment: 1, scaleDivisor: 10, unit: 2 },
        options,
      ),
    ).toThrow(RawCodecError);
    const measurement = decodeFtmsMeasurementRaw(0, Uint8Array.of(1, 0));
    for (const profile of [options, Object.create({ treadmillPaceFormat: "uint8Legacy" })]) {
      expect(() => decodeFtmsMeasurementRaw(0, Uint8Array.of(1, 0), profile)).toThrow(
        RawCodecError,
      );
      expect(() => encodeFtmsMeasurementRaw(measurement, profile)).toThrow(RawCodecError);
    }
  });
  it("rejects inherited C.7 evidence including the snapshot property", () => {
    const snapshot = {
      discovery: 2 as const,
      scope: 1 as const,
      generation: 0,
      characteristics: [],
    };
    expect(() =>
      evaluateFtmsCapabilities({
        ...snapshot,
        c7: Object.create({ bondingSupported: true, featureMayChangeOverLifetime: true }),
      }),
    ).toThrow(RawCodecError);
    expect(() =>
      evaluateFtmsCapabilities(
        Object.assign(Object.create({ c7: { bondingSupported: true } }), snapshot),
      ),
    ).toThrow(RawCodecError);
  });
  it("rejects configuration getters without invoking them", () => {
    let calls = 0;
    const options = {
      get resistanceFormat() {
        calls++;
        return "uint8Tenths" as const;
      },
    };
    expect(() => encodeFtmsControlRequestRaw({ opcode: 4, operands: [123] }, options)).toThrow(
      RawCodecError,
    );
    expect(calls).toBe(0);
  });
  it("keeps empty, null-prototype and foreign-realm defaults", () => {
    for (const options of [{}, Object.create(null), runInNewContext("({})")]) {
      expect(
        Array.from(encodeFtmsControlRequestRaw({ opcode: 4, operands: [123] }, options)),
      ).toEqual([4, 123, 0]);
    }
  });
});

function adjacent(value: number, up: boolean): number {
  if (value === 0) return up ? Number.MIN_VALUE : -Number.MIN_VALUE;
  const view = new DataView(new ArrayBuffer(8));
  view.setFloat64(0, value);
  const bits = view.getBigUint64(0);
  view.setBigUint64(0, bits + (value > 0 === up ? 1n : -1n));
  return view.getFloat64(0);
}
const simulation = {
  op: "setIndoorBikeSimulation",
  windSpeedMps: 0,
  gradePercent: 0,
  crr: 0,
  cwKgPerM: 0,
};
const numericCases = [
  ["setTargetSpeed", "speedKph", 0, 65535, 100],
  ["setTargetInclination", "inclinationPercent", -32768, 32767, 10],
  ["setTargetResistance", "resistanceLevel", -32768, 32767, 10],
  ["setTargetPower", "powerWatts", -32768, 32767, 1],
  ["setTargetHeartRate", "heartRateBpm", 0, 255, 1],
  ["setTargetedExpendedEnergy", "energyKcal", 0, 65535, 1],
  ["setTargetedSteps", "steps", 0, 65535, 1],
  ["setTargetedStrides", "strides", 0, 65535, 1],
  ["setTargetedDistance", "distanceMeters", 0, 16777215, 1],
  ["setTargetedTrainingTime", "seconds", 0, 65535, 1],
  ["setWheelCircumference", "circumferenceMm", 0, 65535, 10],
  ["setTargetedCadence", "cadenceRpm", 0, 65535, 2],
  ["setIndoorBikeSimulation", "windSpeedMps", -32768, 32767, 1000],
  ["setIndoorBikeSimulation", "gradePercent", -32768, 32767, 100],
  ["setIndoorBikeSimulation", "crr", 0, 255, 10000],
  ["setIndoorBikeSimulation", "cwKgPerM", 0, 255, 100],
] as const;
describe("normalized numbers: strict bounds, representational tolerance only", () => {
  for (const [op, field, low, high, scale] of numericCases) {
    it(`${op}.${field} checks original bounds before grid tolerance`, () => {
      const encode = (value: number) =>
        tryEncodeFtmsControlRequest({
          ...(op === "setIndoorBikeSimulation" ? simulation : {}),
          op,
          [field]: value,
        });
      for (const value of [low / scale, high / scale, 0, 1 / scale])
        expect(encode(value).ok).toBe(true);
      for (const value of [adjacent(low / scale, false), adjacent(high / scale, true)])
        expect(encode(value)).toMatchObject({ ok: false, error: { code: "out_of_range" } });
      expect(encode(0.5 / scale)).toMatchObject({
        ok: false,
        error: { code: "invalid_resolution" },
      });
      if (low < 0)
        expect(encode(-0.5 / scale)).toMatchObject({
          ok: false,
          error: { code: "invalid_resolution" },
        });
      for (const value of [NaN, Infinity, -Infinity])
        expect(encode(value)).toMatchObject({ ok: false, error: { code: "invalid_number" } });
    });
  }
  it("rejects the reported near-boundary regressions", () => {
    expect(
      tryEncodeFtmsControlRequest(
        { op: "setTargetResistance", resistanceLevel: 25.5000000005 },
        { resistanceFormat: "uint8Tenths" },
      ),
    ).toMatchObject({ ok: false, error: { code: "out_of_range" } });
    expect(
      tryEncodeFtmsControlRequest({ op: "setTargetResistance", resistanceLevel: -3276.8000000005 }),
    ).toMatchObject({ ok: false, error: { code: "out_of_range" } });
    expect(
      tryEncodeFtmsControlRequest({ op: "setTargetSpeed", speedKph: 1.0100000005 }),
    ).toMatchObject({ ok: false, error: { code: "invalid_resolution" } });
  });
  it("accepts representational error inside the range, not arbitrary quantization", () => {
    const result = tryEncodeFtmsControlRequest({ op: "setTargetSpeed", speedKph: 0.1 + 0.2 });
    expect(result.ok).toBe(true);
    if (result.ok) expect(Array.from(result.value)).toEqual([2, 30, 0]);
    expect(() =>
      encodeFtmsControlRequestRaw({ opcode: 2, operands: [30.000000000000004] }),
    ).toThrow(RawCodecError);
  });
});
