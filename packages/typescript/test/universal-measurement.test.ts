import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, expectTypeOf, it } from "vitest";
import type { FtmsMeasurementRaw, FtmsUniversalMeasurementRaw } from "../src/index.js";
import { decodeFtmsMeasurement, FTMS_CHARACTERISTICS, RawCodecError } from "../src/index.js";

type Vector = {
  characteristicUuid: string;
  bytes: number[];
  expectedMetrics: Record<string, number | string>;
};
const vectors = JSON.parse(
  readFileSync(resolve(import.meta.dirname, "../../../shared/conformance/v1/vectors.json"), "utf8"),
) as { measurements: Vector[] };

describe("decodeFtmsMeasurement", () => {
  it("maps every named raw field and diagnostic against the canonical raw corpus", () => {
    const corpus = JSON.parse(
      readFileSync(
        resolve(import.meta.dirname, "../../../shared/conformance/measurements/v1/vectors.json"),
        "utf8",
      ),
    ) as {
      fieldOrder: string[];
      cases: {
        id: string;
        kind: number;
        bytes: number[];
        decoded: FtmsMeasurementRaw | { error: number };
      }[];
    };
    const names: Record<keyof FtmsUniversalMeasurementRaw, string> = {
      speedHundredthsKph: "speed",
      averageSpeedHundredthsKph: "averageSpeed",
      distanceMeters: "distance",
      inclinationTenthsPercent: "inclination",
      rampAngleTenthsDegrees: "rampAngle",
      positiveElevationRaw: "positiveElevation",
      negativeElevationRaw: "negativeElevation",
      instantaneousPaceRaw: "instantaneousPace",
      averagePaceRaw: "averagePace",
      energyKcal: "energy",
      energyPerHourKcal: "energyPerHour",
      energyPerMinuteKcal: "energyPerMinute",
      heartRateBpm: "heartRate",
      metabolicEquivalentTenths: "met",
      elapsedTimeSeconds: "elapsed",
      remainingTimeSeconds: "remaining",
      forceOnBeltNewtons: "force",
      powerWatts: "power",
      stepRateSpm: "stepRate",
      averageStepRateSpm: "averageStepRate",
      strideCountRaw: "strideCount",
      resistance: "resistance",
      averagePowerWatts: "averagePower",
      floorCount: "floorCount",
      stepCount: "stepCount",
      strokeRateHalfSpm: "strokeRate",
      strokeCount: "strokeCount",
      averageStrokeRateHalfSpm: "averageStrokeRate",
      cadenceHalfRpm: "cadence",
      averageCadenceHalfRpm: "averageCadence",
    };
    const uuids = ["2acd", "2ace", "2acf", "2ad0", "2ad1", "2ad2"];
    const families = new Set<number>();
    for (const fixture of corpus.cases) {
      if ("error" in fixture.decoded) continue;
      const expected = fixture.decoded;
      const result = decodeFtmsMeasurement(
        uuids[fixture.kind] as string,
        Uint8Array.from(fixture.bytes),
      );
      if (result.status !== "known") throw new Error(fixture.id);
      families.add(fixture.kind);
      const unavailable: string[] = [];
      for (const [name, canonical] of Object.entries(names)) {
        const index = corpus.fieldOrder.indexOf(canonical);
        expect(index).toBeGreaterThanOrEqual(0);
        const present = !!(expected.present & (1 << index));
        const missing = !!(expected.unavailable & (1 << index));
        expect(
          result.raw[name as keyof FtmsUniversalMeasurementRaw],
          `${fixture.id}: ${name}`,
        ).toBe(present && !missing ? expected.values[index] : null);
        if (missing) unavailable.push(name);
      }
      expect(result.diagnostics).toEqual({
        flags: expected.flags,
        moreData: !!expected.moreData,
        backward: fixture.kind === 1 ? !!expected.backward : null,
        truncated: !!expected.truncated,
        reservedFlags: !!expected.reservedFlags,
        trailingBytes: expected.trailingBytes ? fixture.bytes.length - expected.bytesRead : 0,
        bytesRead: expected.bytesRead,
        byteLength: fixture.bytes.length,
        unavailableFields: unavailable,
      });
    }
    expect(families.size).toBe(6);
  });
  it("preserves exact bike arithmetic and supplies typed shared metrics", () => {
    const result = decodeFtmsMeasurement("2AD2", Uint8Array.of(0x20, 4, 0x18, 1, 3, 0, 3), {
      resistanceFormat: "signed16Tenths",
    });
    expect(result.status).toBe("known");
    if (result.status !== "known") throw new Error("Expected known");
    expect(result.metrics.speedKph).toBe(280 * 0.01);
    expect(result.metrics.speedMps).toBe(280 / 360);
    expect(result.metrics.resistanceLevel).toBe(3 * 0.1);
    expect(result.metrics.metabolicEquivalent).toBe(3 * 0.1);
    expectTypeOf(result.raw.powerWatts).toEqualTypeOf<number | null>();
    expectTypeOf(result.metrics.heartRateBpm).toEqualTypeOf<number | null>();
    // @ts-expect-error Misspelled fields are not accepted by the public interface.
    result.raw.powerWats;
  });

  it("retains unavailable, trailing, reserved and directional evidence", () => {
    expect(
      decodeFtmsMeasurement("2ad2", Uint8Array.of(1, 0x23, 255, 255, 255, 255, 255, 145, 99)),
    ).toMatchObject({
      status: "known",
      metrics: { energyKcal: null, heartRateBpm: 145 },
      diagnostics: {
        flags: 0x2301,
        moreData: true,
        backward: null,
        reservedFlags: true,
        truncated: false,
        bytesRead: 8,
        trailingBytes: 1,
        unavailableFields: ["energyKcal", "energyPerHourKcal", "energyPerMinuteKcal"],
      },
    });
    expect(decodeFtmsMeasurement("2ace", Uint8Array.of(1, 0x80, 0))).toMatchObject({
      metrics: { movementDirection: "backward" },
      diagnostics: { backward: true, truncated: false, bytesRead: 3 },
    });
    expect(decodeFtmsMeasurement("2ace", Uint8Array.of(1, 0))).toMatchObject({
      metrics: { movementDirection: null },
      diagnostics: { flags: null, backward: null, truncated: true, bytesRead: 0 },
    });
  });

  it("supports explicit legacy treadmill pace without layout guessing", () => {
    const packet = Uint8Array.of(0x21, 1, 120, 145);
    expect(
      decodeFtmsMeasurement("2acd", packet, { treadmillPaceFormat: "uint8Legacy" }),
    ).toMatchObject({
      metrics: { instantaneousPaceSecondsPer500m: null, heartRateBpm: 145 },
      raw: { instantaneousPaceRaw: 120 },
      diagnostics: { truncated: false },
    });
    expect(decodeFtmsMeasurement("2acd", packet)).toMatchObject({
      metrics: { instantaneousPaceSecondsPer500m: 37240, heartRateBpm: null },
      diagnostics: { truncated: true },
    });
  });

  it("does not reinterpret incomplete fields as later metrics", () => {
    expect(
      decodeFtmsMeasurement("2ad2", Uint8Array.of(0x44, 2, 0x10, 0x0e, 0xb4, 0, 0xfa)),
    ).toMatchObject({
      metrics: { speedKph: 36, cadenceRpm: 90, powerWatts: null, heartRateBpm: null },
      raw: { powerWatts: null, heartRateBpm: null },
      diagnostics: { truncated: true, bytesRead: 6, trailingBytes: 0 },
    });
  });
  it("projects every canonical measurement fixture through one UUID-selected decoder", () => {
    for (const vector of vectors.measurements) {
      const result = decodeFtmsMeasurement(
        vector.characteristicUuid,
        Uint8Array.from(vector.bytes),
      );
      expect(result.status).toBe("known");
      if (result.status !== "known") continue;
      for (const [name, value] of Object.entries(vector.expectedMetrics))
        expect(result.metrics[name as keyof typeof result.metrics]).toBe(value);
    }
  });

  it("uses independently checked physical conversions and named raw values", () => {
    const treadmill = decodeFtmsMeasurement(
      FTMS_CHARACTERISTICS.TREADMILL_DATA,
      Uint8Array.of(
        0xfe,
        0x1f,
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
      ),
    );
    expect(treadmill).toMatchObject({ status: "known", family: "treadmill" });
    if (treadmill.status === "known") {
      expect(treadmill.metrics.speedKph).toBe(10);
      expect(treadmill.metrics.speedMps).toBeCloseTo(10 / 3.6);
      expect(treadmill.metrics.inclinationPercent).toBe(-1.5);
      expect(treadmill.metrics.positiveElevationGainMeters).toBe(12.3);
      expect(treadmill.raw.positiveElevationRaw).toBe(123);
    }
    const rower = decodeFtmsMeasurement(
      FTMS_CHARACTERISTICS.ROWER_DATA,
      Uint8Array.of(0xfe, 0x1f, 0x40, 0x2c, 0x01),
    );
    expect(rower.status).toBe("known");
    if (rower.status === "known") expect(rower.metrics.strokeRateSpm).toBe(32);
  });

  it("keeps every prefix as partial evidence, including Cross Trainer's three-byte flags", () => {
    for (const vector of vectors.measurements) {
      for (let length = 0; length <= vector.bytes.length; length += 1) {
        const result = decodeFtmsMeasurement(
          vector.characteristicUuid,
          Uint8Array.from(vector.bytes.slice(0, length)),
        );
        expect(result.status).toBe("known");
        if (result.status === "known") expect(result.diagnostics.byteLength).toBe(length);
      }
    }
  });

  it("normalizes standard aliases and explicitly rejects non-measurement/unknown UUIDs", () => {
    expect(decodeFtmsMeasurement("0x2ad2", Uint8Array.of(0, 0, 0, 0))).toMatchObject({
      status: "known",
      family: "bike",
    });
    expect(decodeFtmsMeasurement("2ad3", Uint8Array.of())).toEqual({
      status: "unsupported",
      characteristicUuid: FTMS_CHARACTERISTICS.TRAINING_STATUS,
    });
    expect(
      decodeFtmsMeasurement("00000000-0000-1000-8000-00805f9b34fb", Uint8Array.of()),
    ).toMatchObject({ status: "unsupported" });
    expect(() =>
      decodeFtmsMeasurement(FTMS_CHARACTERISTICS.INDOOR_BIKE_DATA, {} as Uint8Array),
    ).toThrow(RawCodecError);
    expect(() =>
      decodeFtmsMeasurement(FTMS_CHARACTERISTICS.INDOOR_BIKE_DATA, Uint8Array.of(0, 0), {
        resistanceFormat: "bad",
      } as never),
    ).toThrow(RawCodecError);
  });

  it("honors caller-selected resistance layouts and offset byte views", () => {
    const bytes = Uint8Array.of(0xaa, 0x20, 0x00, 0x00, 0x00, 0xf6, 0xff, 0xbb).subarray(1, 7);
    const signed = decodeFtmsMeasurement(FTMS_CHARACTERISTICS.INDOOR_BIKE_DATA, bytes, {
      resistanceFormat: "signed16Tenths",
    });
    expect(signed).toMatchObject({ status: "known" });
    if (signed.status === "known") expect(signed.metrics.resistanceLevel).toBe(-1);
    const whole = decodeFtmsMeasurement(
      FTMS_CHARACTERISTICS.INDOOR_BIKE_DATA,
      Uint8Array.of(0x20, 0x00, 0x00, 0x00, 0x0a),
    );
    if (whole.status === "known") expect(whole.metrics.resistanceLevel).toBe(10);
  });
});
