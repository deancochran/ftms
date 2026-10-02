import { describe, expect, it } from "vitest";
import { decodeIndoorBikeData } from "../src/index.js";
import { RawCodecError } from "../src/types.js";

const allFields = Uint8Array.of(
  0xfe,
  0x1f,
  0x10,
  0x0e, // mandatory speed: 36.00 km/h
  0xb4,
  0x0c, // average speed: 32.52 km/h
  0xb5,
  0x00, // cadence: 90.5 rpm
  0x78,
  0x00, // average cadence: 60 rpm
  0x03,
  0x02,
  0x01, // distance: 66051 m
  0x2a, // default resistance: 42 whole levels
  0xfa,
  0xff, // power: -6 W
  0xfa,
  0x00, // average power: 250 W
  0xf4,
  0x01, // energy: 500 kcal
  0x58,
  0x02, // energy/hour: 600 kcal
  0x0a, // energy/minute: 10 kcal
  0x96, // heart rate: 150 bpm
  0x55, // MET: 8.5
  0x10,
  0x0e, // elapsed: 3600 s
  0x58,
  0x02, // remaining: 600 s
);

function expectRawError(code: RawCodecError["code"], action: () => unknown): void {
  try {
    action();
  } catch (error) {
    expect(error).toBeInstanceOf(RawCodecError);
    expect((error as RawCodecError).code).toBe(code);
    return;
  }
  throw new Error(`Expected RawCodecError(${code})`);
}

describe("decodeIndoorBikeData", () => {
  it("names every Indoor Bike field in raw and physical units", () => {
    const decoded = decodeIndoorBikeData(allFields);

    expect(decoded.raw).toStrictEqual({
      speedHundredthsKph: 3600,
      averageSpeedHundredthsKph: 3252,
      cadenceHalfRpm: 181,
      averageCadenceHalfRpm: 120,
      distanceMeters: 0x010203,
      resistance: 42,
      powerWatts: -6,
      averagePowerWatts: 250,
      energyKcal: 500,
      energyPerHourKcal: 600,
      energyPerMinuteKcal: 10,
      heartRateBpm: 150,
      metabolicEquivalentTenths: 85,
      elapsedTimeSeconds: 3600,
      remainingTimeSeconds: 600,
    });
    expect(decoded.measurement).toStrictEqual({
      speedKph: 36,
      speedMps: 10,
      averageSpeedKph: 32.52,
      averageSpeedMps: 9.033333333333333,
      cadenceRpm: 90.5,
      averageCadenceRpm: 60,
      distanceMeters: 0x010203,
      resistanceLevel: 42,
      powerWatts: -6,
      averagePowerWatts: 250,
      energyKcal: 500,
      energyPerHourKcal: 600,
      energyPerMinuteKcal: 10,
      heartRateBpm: 150,
      metabolicEquivalent: 8.5,
      elapsedTimeSeconds: 3600,
      remainingTimeSeconds: 600,
    });
    expect(decoded.diagnostics).toStrictEqual({
      flags: 0x1ffe,
      moreData: false,
      truncated: false,
      reservedFlags: false,
      trailingBytes: 0,
      bytesRead: allFields.length,
      byteLength: allFields.length,
      unavailableFields: [],
    });
  });

  it("uses the caller-selected signed resistance layout without inferring it", () => {
    const signed = Uint8Array.of(...allFields.slice(0, 13), 0xd3, 0xff, ...allFields.slice(14));
    const defaultFormat = decodeIndoorBikeData(signed);
    const selected = decodeIndoorBikeData(signed, { resistanceFormat: "signed16Tenths" });

    expect(defaultFormat.measurement.resistanceLevel).toBe(211);
    expect(defaultFormat.diagnostics.trailingBytes).toBe(1);
    expect(selected.raw.resistance).toBe(-45);
    expect(selected.measurement.resistanceLevel).toBe(-4.5);
    expect(selected.diagnostics).toMatchObject({ truncated: false, trailingBytes: 0 });
  });

  it("retains unavailable energy evidence without fabricating values", () => {
    const unavailable = Uint8Array.from(allFields);
    unavailable.set([0xff, 0xff, 0xff, 0xff, 0xff], 18);
    const decoded = decodeIndoorBikeData(unavailable);

    expect(decoded.raw.energyKcal).toBeNull();
    expect(decoded.raw.energyPerHourKcal).toBeNull();
    expect(decoded.raw.energyPerMinuteKcal).toBeNull();
    expect(decoded.measurement.energyKcal).toBeNull();
    expect(decoded.diagnostics.unavailableFields).toStrictEqual([
      "energyKcal",
      "energyPerHourKcal",
      "energyPerMinuteKcal",
    ]);
  });

  it("preserves flag, More Data, reserved-bit, trailing-byte, and byte-offset diagnostics", () => {
    const input = Uint8Array.of(0x01, 0xe0, 0xaa);
    const padded = Uint8Array.of(0x99, ...input, 0x99);
    const decoded = decodeIndoorBikeData(new Uint8Array(padded.buffer, 1, input.length));

    expect(decoded.measurement.speedKph).toBeNull();
    expect(decoded.diagnostics).toStrictEqual({
      flags: 0xe001,
      moreData: true,
      truncated: false,
      reservedFlags: true,
      trailingBytes: 1,
      bytesRead: 2,
      byteLength: 3,
      unavailableFields: [],
    });
  });

  it("returns the complete prefix and diagnostics at every truncation boundary", () => {
    for (let length = 0; length < allFields.length; length += 1) {
      const decoded = decodeIndoorBikeData(allFields.slice(0, length));
      expect(decoded.diagnostics.byteLength).toBe(length);
      expect(decoded.diagnostics.truncated).toBe(true);
      if (length < 2) {
        expect(decoded.diagnostics).toMatchObject({
          flags: null,
          moreData: null,
          bytesRead: 0,
          reservedFlags: false,
        });
      } else {
        expect(decoded.diagnostics.flags).toBe(0x1ffe);
        expect(decoded.diagnostics.bytesRead).toBeLessThanOrEqual(length);
      }
    }
  });

  it("uses default semantics for omitted fields and validates input before truncated flags", () => {
    const defaults = decodeIndoorBikeData(Uint8Array.of(0, 0, 0x34, 0x12));
    expect(defaults.raw).toStrictEqual({
      speedHundredthsKph: 0x1234,
      averageSpeedHundredthsKph: null,
      cadenceHalfRpm: null,
      averageCadenceHalfRpm: null,
      distanceMeters: null,
      resistance: null,
      powerWatts: null,
      averagePowerWatts: null,
      energyKcal: null,
      energyPerHourKcal: null,
      energyPerMinuteKcal: null,
      heartRateBpm: null,
      metabolicEquivalentTenths: null,
      elapsedTimeSeconds: null,
      remainingTimeSeconds: null,
    });
    expect(defaults.measurement.speedKph).toBe(46.6);
    expect(defaults.measurement.speedMps).toBeCloseTo(46.6 / 3.6);

    for (const invalid of [null, {}, new Uint16Array(1)])
      expectRawError("null", () => decodeIndoorBikeData(invalid as Uint8Array));
    for (const options of [null, { resistanceFormat: "automatic" }, { extra: true }])
      expectRawError("kind", () =>
        decodeIndoorBikeData(
          Uint8Array.of(0),
          options as Parameters<typeof decodeIndoorBikeData>[1],
        ),
      );
  });
});
