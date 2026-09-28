import { describe, expect, it } from "vitest";
import {
  FTMS_CHARACTERISTICS,
  type FtmsRuntimeMetrics,
  type ParsedFtmsPayload,
  parseFtmsCrossTrainerData,
  parseFtmsIndoorBikeData,
  parseFtmsIndoorBikeMeasurement,
  parseFtmsRowerData,
  parseFtmsStairClimberData,
  parseFtmsStepClimberData,
  parseFtmsTreadmillData,
  parseRegisteredFtmsPayload,
} from "../src/index.js";

function flags16(flags: number, ...fields: number[]): Uint8Array {
  return Uint8Array.of(flags & 0xff, (flags >>> 8) & 0xff, ...fields);
}

function flags24(flags: number, ...fields: number[]): Uint8Array {
  return Uint8Array.of(flags & 0xff, (flags >>> 8) & 0xff, (flags >>> 16) & 0xff, ...fields);
}

type MeasurementParser = (bytes: Uint8Array) => ParsedFtmsPayload;

interface MandatoryCase {
  name: string;
  parser: MeasurementParser;
  bytes: Uint8Array;
  expected: Partial<FtmsRuntimeMetrics>;
}

const mandatoryCases: readonly MandatoryCase[] = [
  {
    name: "treadmill",
    parser: parseFtmsTreadmillData,
    bytes: flags16(0, 0x10, 0x27),
    expected: { speedMps: 100 / 3.6 },
  },
  {
    name: "cross trainer",
    parser: parseFtmsCrossTrainerData,
    bytes: flags24(0, 0xe8, 0x03),
    expected: { speedMps: 10 / 3.6, movementDirection: "forward" },
  },
  {
    name: "step climber",
    parser: parseFtmsStepClimberData,
    bytes: flags16(0, 0x0c, 0x00, 0x2c, 0x01),
    expected: { floorCount: 12, stepCount: 300 },
  },
  {
    name: "stair climber",
    parser: parseFtmsStairClimberData,
    bytes: flags16(0, 0x14, 0x00),
    expected: { floorCount: 20 },
  },
  {
    name: "rower",
    parser: parseFtmsRowerData,
    bytes: flags16(0, 64, 0x2c, 0x01),
    expected: { strokeRateSpm: 32, strokeCount: 300 },
  },
  {
    name: "indoor bike",
    parser: parseFtmsIndoorBikeMeasurement,
    bytes: flags16(0, 0xe8, 0x03),
    expected: { speedMps: 10 / 3.6 },
  },
];

describe("mandatory FTMS measurement fields", () => {
  it.each(mandatoryCases)("decodes $name mandatory fields", ({ parser, bytes, expected }) => {
    const result = parser(bytes);
    expect(result.metrics).toMatchObject(expected);
    expect(result.diagnostics.truncated).toBe(false);
  });

  it.each([
    { name: "treadmill", parser: parseFtmsTreadmillData, bytes: flags16(0x01) },
    { name: "cross trainer", parser: parseFtmsCrossTrainerData, bytes: flags24(0x01) },
    { name: "step climber", parser: parseFtmsStepClimberData, bytes: flags16(0x01) },
    { name: "stair climber", parser: parseFtmsStairClimberData, bytes: flags16(0x01) },
    { name: "rower", parser: parseFtmsRowerData, bytes: flags16(0x01) },
    { name: "indoor bike", parser: parseFtmsIndoorBikeMeasurement, bytes: flags16(0x01) },
  ])("omits $name mandatory fields when More Data is set", ({ parser, bytes }) => {
    const result = parser(bytes);
    expect(result.diagnostics.moreData).toBe(true);
    expect(result.diagnostics.truncated).toBe(false);
    expect(result.diagnostics.issues).toContainEqual(
      expect.objectContaining({ code: "more_data" }),
    );
  });
});

describe("complete FTMS measurement layouts", () => {
  it("decodes every treadmill field in wire order", () => {
    const result = parseFtmsTreadmillData(
      flags16(
        0x1ffe,
        0xe8,
        0x03,
        0x84,
        0x03,
        0x03,
        0x02,
        0x01,
        0xf1,
        0xff,
        0x19,
        0x00,
        0x7b,
        0x00,
        0x2d,
        0x00,
        0x2c,
        0x01,
        0x40,
        0x01,
        0xf4,
        0x01,
        0x58,
        0x02,
        10,
        150,
        85,
        0x10,
        0x0e,
        0x58,
        0x02,
        0xec,
        0xff,
        0xfa,
        0x00,
      ),
    );

    expect(result.metrics).toMatchObject({
      speedMps: 10 / 3.6,
      averageSpeedMps: 9 / 3.6,
      distanceMeters: 0x010203,
      inclinationPercent: -1.5,
      rampAngleDegrees: 2.5,
      positiveElevationGainMeters: 12.3,
      negativeElevationGainMeters: 4.5,
      instantaneousPaceSecondsPer500m: 300,
      averagePaceSecondsPer500m: 320,
      energyKcal: 500,
      energyPerHourKcal: 600,
      energyPerMinuteKcal: 10,
      hrBpm: 150,
      metabolicEquivalent: 8.5,
      elapsedTimeSeconds: 3600,
      remainingTimeSeconds: 600,
      forceOnBeltNewtons: -20,
      powerWatts: 250,
    });
    expect(result.diagnostics).toMatchObject({ truncated: false, bytesRead: 36, byteLength: 36 });
  });

  it("decodes three-byte cross-trainer flags and corrected field positions", () => {
    const result = parseFtmsCrossTrainerData(
      flags24(
        0xfffe,
        0xe8,
        0x03,
        0x84,
        0x03,
        0x03,
        0x02,
        0x01,
        100,
        0,
        80,
        0,
        50,
        0,
        10,
        0,
        4,
        0,
        0xf6,
        0xff,
        20,
        0,
        7,
        200,
        0,
        180,
        0,
        0x2c,
        0x01,
        0x90,
        0x01,
        5,
        140,
        75,
        0xe8,
        0x03,
        200,
        0,
      ),
    );

    expect(result.metrics).toMatchObject({
      speedMps: 10 / 3.6,
      averageSpeedMps: 9 / 3.6,
      distanceMeters: 0x010203,
      stepRateSpm: 100,
      averageStepRateSpm: 80,
      strideCount: 5,
      positiveElevationGainMeters: 10,
      negativeElevationGainMeters: 4,
      inclinationPercent: -1,
      rampAngleDegrees: 2,
      resistanceLevel: 7,
      powerWatts: 200,
      averagePowerWatts: 180,
      energyKcal: 300,
      energyPerHourKcal: 400,
      energyPerMinuteKcal: 5,
      hrBpm: 140,
      metabolicEquivalent: 7.5,
      elapsedTimeSeconds: 1000,
      remainingTimeSeconds: 200,
      movementDirection: "backward",
    });
    expect(result.diagnostics.truncated).toBe(false);
  });

  it("decodes every step-climber field", () => {
    const result = parseFtmsStepClimberData(
      flags16(
        0x01fe,
        12,
        0,
        0x2c,
        0x01,
        60,
        0,
        55,
        0,
        10,
        0,
        0x2c,
        0x01,
        0x90,
        0x01,
        5,
        140,
        75,
        0xe8,
        0x03,
        200,
        0,
      ),
    );

    expect(result.metrics).toMatchObject({
      floorCount: 12,
      stepCount: 300,
      stepRateSpm: 60,
      averageStepRateSpm: 55,
      positiveElevationGainMeters: 10,
      energyKcal: 300,
      energyPerHourKcal: 400,
      energyPerMinuteKcal: 5,
      hrBpm: 140,
      metabolicEquivalent: 7.5,
      elapsedTimeSeconds: 1000,
      remainingTimeSeconds: 200,
    });
  });

  it("decodes every stair-climber field", () => {
    const result = parseFtmsStairClimberData(
      flags16(
        0x03fe,
        20,
        0,
        70,
        0,
        65,
        0,
        30,
        0,
        0xfa,
        0x00,
        0x2c,
        0x01,
        0x90,
        0x01,
        5,
        142,
        80,
        0x58,
        0x02,
        100,
        0,
      ),
    );

    expect(result.metrics).toMatchObject({
      floorCount: 20,
      stepRateSpm: 70,
      averageStepRateSpm: 65,
      positiveElevationGainMeters: 30,
      strideCount: 250,
      energyKcal: 300,
      energyPerHourKcal: 400,
      energyPerMinuteKcal: 5,
      hrBpm: 142,
      metabolicEquivalent: 8,
      elapsedTimeSeconds: 600,
      remainingTimeSeconds: 100,
    });
  });

  it("decodes every rower field with one-byte resistance", () => {
    const result = parseFtmsRowerData(
      flags16(
        0x1ffe,
        64,
        0x2c,
        0x01,
        60,
        0xf4,
        0x01,
        0x00,
        120,
        0,
        130,
        0,
        250,
        0,
        240,
        0,
        8,
        0x2c,
        0x01,
        0x90,
        0x01,
        5,
        145,
        80,
        0x58,
        0x02,
        100,
        0,
      ),
    );

    expect(result.metrics).toMatchObject({
      strokeRateSpm: 32,
      strokeCount: 300,
      averageStrokeRateSpm: 30,
      distanceMeters: 500,
      instantaneousPaceSecondsPer500m: 120,
      averagePaceSecondsPer500m: 130,
      powerWatts: 250,
      averagePowerWatts: 240,
      resistanceLevel: 8,
      energyKcal: 300,
      energyPerHourKcal: 400,
      energyPerMinuteKcal: 5,
      hrBpm: 145,
      metabolicEquivalent: 8,
      elapsedTimeSeconds: 600,
      remainingTimeSeconds: 100,
    });
  });

  it("decodes every indoor-bike field with one-byte resistance", () => {
    const result = parseFtmsIndoorBikeMeasurement(
      flags16(
        0x1ffe,
        0xe8,
        0x03,
        0x84,
        0x03,
        180,
        0,
        170,
        0,
        0xe8,
        0x03,
        0x00,
        8,
        250,
        0,
        240,
        0,
        0x2c,
        0x01,
        0x90,
        0x01,
        5,
        145,
        80,
        0x58,
        0x02,
        100,
        0,
      ),
    );

    expect(result.metrics).toMatchObject({
      speedMps: 10 / 3.6,
      averageSpeedMps: 9 / 3.6,
      cadenceRpm: 90,
      averageCadenceRpm: 85,
      distanceMeters: 1000,
      resistanceLevel: 8,
      powerWatts: 250,
      averagePowerWatts: 240,
      energyKcal: 300,
      energyPerHourKcal: 400,
      energyPerMinuteKcal: 5,
      hrBpm: 145,
      metabolicEquivalent: 8,
      elapsedTimeSeconds: 600,
      remainingTimeSeconds: 100,
    });
  });
});

describe("measurement diagnostics", () => {
  it.each([
    {
      name: "treadmill",
      parser: parseFtmsTreadmillData,
      bytes: flags16(0x1000, 0xe8, 0x03, 1),
    },
    {
      name: "cross trainer",
      parser: parseFtmsCrossTrainerData,
      bytes: flags24(0x0101, 1),
    },
    {
      name: "step climber",
      parser: parseFtmsStepClimberData,
      bytes: flags16(0x0003, 1),
    },
    {
      name: "stair climber",
      parser: parseFtmsStairClimberData,
      bytes: flags16(0x0003, 1),
    },
    { name: "rower", parser: parseFtmsRowerData, bytes: flags16(0x0021, 1) },
    {
      name: "indoor bike",
      parser: parseFtmsIndoorBikeMeasurement,
      bytes: flags16(0x0041, 1),
    },
  ])("marks a truncated $name field and stops parsing", ({ parser, bytes }) => {
    const result = parser(bytes);
    expect(result.diagnostics.truncated).toBe(true);
    expect(result.diagnostics.issues).toContainEqual(
      expect.objectContaining({ code: "truncated" }),
    );
    expect(Object.values(result.metrics)).not.toContain(Number.NaN);
  });

  it("does not reinterpret a truncated power byte as heart rate", () => {
    const result = parseFtmsIndoorBikeMeasurement(flags16(0x0241, 0x01));
    expect(result.metrics.powerWatts).toBeNull();
    expect(result.metrics.hrBpm).toBeNull();
  });

  it("maps known unavailable treadmill values to null", () => {
    const result = parseFtmsTreadmillData(
      flags16(
        0x1088,
        0xe8,
        0x03,
        0xff,
        0x7f,
        0xff,
        0x7f,
        0xff,
        0xff,
        0xff,
        0xff,
        0xff,
        0xff,
        0x7f,
        0xff,
        0x7f,
      ),
    );
    expect(result.metrics).toMatchObject({
      inclinationPercent: null,
      rampAngleDegrees: null,
      energyKcal: null,
      energyPerHourKcal: null,
      energyPerMinuteKcal: null,
      forceOnBeltNewtons: null,
      powerWatts: null,
    });
    expect(result.diagnostics.issues.filter((issue) => issue.code === "unavailable")).toHaveLength(
      7,
    );
  });

  it.each([
    {
      name: "treadmill",
      parser: parseFtmsTreadmillData,
      bytes: flags16(0x0180, 0xe8, 0x03, 0xff, 0xff, 0xff, 0xff, 0xff, 150),
    },
    {
      name: "cross trainer",
      parser: parseFtmsCrossTrainerData,
      bytes: flags24(0x0c01, 0xff, 0xff, 0xff, 0xff, 0xff, 150),
    },
    {
      name: "step climber",
      parser: parseFtmsStepClimberData,
      bytes: flags16(0x0031, 0xff, 0xff, 0xff, 0xff, 0xff, 150),
    },
    {
      name: "stair climber",
      parser: parseFtmsStairClimberData,
      bytes: flags16(0x0061, 0xff, 0xff, 0xff, 0xff, 0xff, 150),
    },
    {
      name: "rower",
      parser: parseFtmsRowerData,
      bytes: flags16(0x0301, 0xff, 0xff, 0xff, 0xff, 0xff, 150),
    },
    {
      name: "indoor bike",
      parser: parseFtmsIndoorBikeMeasurement,
      bytes: flags16(0x0301, 0xff, 0xff, 0xff, 0xff, 0xff, 150),
    },
  ])("maps every unavailable $name energy value to null without shifting heart rate", ({
    parser,
    bytes,
  }) => {
    const result = parser(bytes);
    expect(result.metrics).toMatchObject({
      energyKcal: null,
      energyPerHourKcal: null,
      energyPerMinuteKcal: null,
      hrBpm: 150,
    });
    expect(result.diagnostics.issues.filter((issue) => issue.code === "unavailable")).toHaveLength(
      3,
    );
    expect(result.diagnostics.truncated).toBe(false);
  });

  it("maps unavailable cross-trainer step rates and preserves scaled stride alignment", () => {
    const result = parseFtmsCrossTrainerData(flags24(0x0819, 0xff, 0xff, 0xff, 0xff, 123, 0, 150));
    expect(result.metrics).toMatchObject({
      stepRateSpm: null,
      averageStepRateSpm: null,
      strideCount: 12.3,
      hrBpm: 150,
    });
    expect(result.diagnostics.issues.filter((issue) => issue.code === "unavailable")).toHaveLength(
      2,
    );
  });

  it("maps unavailable cross-trainer inclination fields without shifting resistance or power", () => {
    const result = parseFtmsCrossTrainerData(
      flags24(0x01c1, 0xff, 0x7f, 0xff, 0x7f, 9, 0xec, 0xff),
    );
    expect(result.metrics).toMatchObject({
      inclinationPercent: null,
      rampAngleDegrees: null,
      resistanceLevel: 9,
      powerWatts: -20,
    });
    expect(result.diagnostics.issues.filter((issue) => issue.code === "unavailable")).toHaveLength(
      2,
    );
  });

  it.each([
    {
      name: "cross trainer instantaneous",
      parser: parseFtmsCrossTrainerData,
      bytes: flags24(0x0901, 0xff, 0x7f, 150),
    },
    {
      name: "cross trainer average",
      parser: parseFtmsCrossTrainerData,
      bytes: flags24(0x0a01, 0xff, 0x7f, 150),
    },
    {
      name: "rower instantaneous",
      parser: parseFtmsRowerData,
      bytes: flags16(0x0221, 0xff, 0x7f, 150),
    },
    {
      name: "rower average",
      parser: parseFtmsRowerData,
      bytes: flags16(0x0241, 0xff, 0x7f, 150),
    },
    {
      name: "indoor bike instantaneous",
      parser: parseFtmsIndoorBikeMeasurement,
      bytes: flags16(0x0241, 0xff, 0x7f, 150),
    },
    {
      name: "indoor bike average",
      parser: parseFtmsIndoorBikeMeasurement,
      bytes: flags16(0x0281, 0xff, 0x7f, 150),
    },
  ])("does not invent an unavailable sentinel for $name power", ({ name, parser, bytes }) => {
    const result = parser(bytes);
    const field = name.endsWith("average") ? "averagePowerWatts" : "powerWatts";
    expect(Reflect.get(result.metrics, field)).toBe(0x7fff);
    expect(result.metrics.hrBpm).toBe(150);
    expect(result.diagnostics.issues).not.toContainEqual(
      expect.objectContaining({ code: "unavailable", field }),
    );
  });

  it("diagnoses reserved 16-bit flags", () => {
    const result = parseFtmsTreadmillData(flags16(0x2000, 0xe8, 0x03));
    expect(result.diagnostics.issues).toContainEqual(
      expect.objectContaining({ code: "reserved_flags", actual: 0x2000 }),
    );
  });

  it("diagnoses reserved high cross-trainer flag bytes", () => {
    const result = parseFtmsCrossTrainerData(flags24(0x010000, 0xe8, 0x03));
    expect(result.diagnostics.issues).toContainEqual(
      expect.objectContaining({ code: "reserved_flags", actual: 0x010000 }),
    );
  });

  it("diagnoses trailing measurement bytes", () => {
    const result = parseFtmsIndoorBikeMeasurement(flags16(0, 0xe8, 0x03, 0xaa));
    expect(result.diagnostics.issues).toContainEqual(
      expect.objectContaining({ code: "trailing_bytes", offset: 4 }),
    );
  });
});

describe("indoor-bike compatibility and parser registry", () => {
  it("retains the legacy flat indoor-bike projection", () => {
    const result = parseFtmsIndoorBikeData(flags16(0x0244, 0xe8, 0x03, 180, 0, 250, 0, 145));
    expect(result).toEqual({
      speedMps: 10 / 3.6,
      cadenceRpm: 90,
      powerWatts: 250,
      hrBpm: 145,
      truncated: false,
    });
  });

  it("retains average-value fallbacks in the legacy indoor-bike projection", () => {
    const result = parseFtmsIndoorBikeData(flags16(0x008b, 0xe8, 0x03, 180, 0, 250, 0));
    expect(result).toEqual({
      speedMps: 10 / 3.6,
      cadenceRpm: 90,
      powerWatts: 250,
      hrBpm: null,
      truncated: false,
    });
  });

  it("uses the complete indoor-bike parser from the registry", () => {
    const result = parseRegisteredFtmsPayload(
      FTMS_CHARACTERISTICS.INDOOR_BIKE_DATA.toUpperCase(),
      flags16(0x0004, 0xe8, 0x03, 180, 0),
    );
    expect(result?.kind).toBe("measurement");
    expect(result?.metrics.cadenceRpm).toBe(90);
  });

  it("returns null for an unknown characteristic", () => {
    expect(parseRegisteredFtmsPayload("unknown", Uint8Array.of())).toBeNull();
  });
});
