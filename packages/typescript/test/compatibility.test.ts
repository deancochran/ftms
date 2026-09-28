import { Ajv2020 } from "ajv/dist/2020.js";
import { describe, expect, it } from "vitest";
import schema from "../../../shared/conformance/compatibility/v1/schema.json" with { type: "json" };
import vectors from "../../../shared/conformance/compatibility/v1/vectors.json" with {
  type: "json",
};
import { decodeFtmsRangeRaw, encodeFtmsRangeRaw } from "../src/features.js";
import { decodeFtmsMeasurementRaw, encodeFtmsMeasurementRaw } from "../src/parsers.js";
import type {
  FtmsMeasurementFormatOptions,
  FtmsMeasurementRaw,
  FtmsRangeFormatOptions,
  FtmsRangeRaw,
} from "../src/types.js";
import { RawCodecError } from "../src/types.js";

type MeasurementCase = {
  id: string;
  kind: number;
  area: "measurement";
  options: FtmsMeasurementFormatOptions;
  bytes: number[];
  expected: FtmsMeasurementRaw;
  encode: boolean;
};
type RangeCase = {
  id: string;
  kind: "resistance";
  area: "range";
  options: FtmsRangeFormatOptions;
  bytes: number[];
  expected: FtmsRangeRaw;
  encode: boolean;
};
type CompatibilityCase = MeasurementCase | RangeCase;
const cases = (vectors as unknown as { cases: CompatibilityCase[] }).cases;

describe("explicit wire-format compatibility corpus", () => {
  function rejectsKind(action: () => unknown) {
    try {
      action();
      throw new Error("Expected format rejection");
    } catch (error) {
      expect(error).toBeInstanceOf(RawCodecError);
      expect((error as RawCodecError).code).toBe("kind");
    }
  }

  it("rejects malformed options instead of silently choosing a layout", () => {
    const range = {
      kind: "speed",
      minimum: 0,
      maximum: 100,
      increment: 1,
      scaleDivisor: 100,
      unit: 0,
    } as const;
    const measurement = cases.find((c) => c.area === "measurement");
    if (!measurement || measurement.area !== "measurement") throw new Error("Missing fixture");
    for (const value of [null, 0, "bad", false, [], { unknownFormat: true }]) {
      const rangeOptions = value as FtmsRangeFormatOptions;
      const measurementOptions = value as FtmsMeasurementFormatOptions;
      rejectsKind(() =>
        decodeFtmsRangeRaw("speed", Uint8Array.of(0, 0, 100, 0, 1, 0), rangeOptions),
      );
      rejectsKind(() => encodeFtmsRangeRaw(range, rangeOptions));
      rejectsKind(() =>
        decodeFtmsMeasurementRaw(
          measurement.kind,
          Uint8Array.from(measurement.bytes),
          measurementOptions,
        ),
      );
      rejectsKind(() => encodeFtmsMeasurementRaw(measurement.expected, measurementOptions));
    }
  });

  it("rejects a signed-resistance range format for unrelated range kinds in both directions", () => {
    const range = {
      kind: "speed",
      minimum: 0,
      maximum: 100,
      increment: 1,
      scaleDivisor: 100,
      unit: 0,
    } as const;
    const options = { resistanceFormat: "signed16Tenths" } as const;
    rejectsKind(() => decodeFtmsRangeRaw("speed", Uint8Array.of(0, 0, 100, 0, 1, 0), options));
    rejectsKind(() => encodeFtmsRangeRaw(range, options));
  });

  it("documents default objects and family-specific measurement settings without inference", () => {
    const bytes = Uint8Array.of(0, 0, 232, 3);
    const expected = decodeFtmsMeasurementRaw(0, bytes);
    expect(decodeFtmsMeasurementRaw(0, bytes, {})).toStrictEqual(expected);
    const options = { resistanceFormat: "signed16Tenths" } as const;
    expect(decodeFtmsMeasurementRaw(0, bytes, options)).toStrictEqual(expected);
    expect(encodeFtmsMeasurementRaw(expected, options)).toStrictEqual(bytes);
  });
  it("requires explicit range selection and rejects wrong width or invalid formats", () => {
    const captured = new Uint8Array([0, 0, 100, 0, 1, 0]);
    expect(() => decodeFtmsRangeRaw("resistance", captured)).toThrow();
    expect(() =>
      decodeFtmsRangeRaw("resistance", new Uint8Array([0, 100, 1]), {
        resistanceFormat: "signed16Tenths",
      }),
    ).toThrow();
    for (const value of [-1, 256, Number.NaN, 0.5, "guess"]) {
      const options = { resistanceFormat: value } as unknown as FtmsRangeFormatOptions;
      expect(() => decodeFtmsRangeRaw("resistance", captured, options)).toThrow();
      expect(() => decodeFtmsMeasurementRaw(5, new Uint8Array([1, 0]), options)).toThrow();
    }
  });

  it("checks selected measurement bounds and preserves signed extrema", () => {
    const c = cases.find((entry) => entry.id === "bike-known-resistance-power-elapsed");
    if (!c || c.area !== "measurement") throw new Error("Missing fixture");
    for (const value of [-32768, 32767]) {
      const values = [...c.expected.values];
      values[21] = value;
      const raw = { ...c.expected, values };
      const bytes = encodeFtmsMeasurementRaw(raw, c.options);
      expect(Array.from(bytes.slice(4, 6))).toEqual(value === -32768 ? [0, 128] : [255, 127]);
      expect(decodeFtmsMeasurementRaw(5, bytes, c.options).values[21]).toBe(value);
    }
    for (const value of [-32769, 32768, Number.NaN, 0.5]) {
      const values = [...c.expected.values];
      values[21] = value;
      expect(() => encodeFtmsMeasurementRaw({ ...c.expected, values }, c.options)).toThrow();
    }
  });

  it("validates the strict schema and unique IDs", () => {
    const validate = new Ajv2020({ allErrors: true, strict: true }).compile(schema);
    expect(validate(vectors), JSON.stringify(validate.errors)).toBe(true);
    expect(cases).toHaveLength(9);
    expect(new Set(cases.map((entry) => entry.id)).size).toBe(9);
  });

  for (const c of cases)
    it(c.id, () => {
      const bytes = new Uint8Array(c.bytes);
      if (c.area === "measurement") {
        expect.soft(decodeFtmsMeasurementRaw(c.kind, bytes, c.options)).toStrictEqual(c.expected);
        if (
          c.options.resistanceFormat === "uint8Whole" &&
          c.options.treadmillPaceFormat === "uint16"
        ) {
          expect(decodeFtmsMeasurementRaw(c.kind, bytes)).toStrictEqual(c.expected);
          expect(Array.from(encodeFtmsMeasurementRaw(c.expected))).toStrictEqual(c.bytes);
        }
        expect
          .soft(Array.from(encodeFtmsMeasurementRaw(c.expected, c.options)))
          .toStrictEqual(c.bytes);
      } else {
        expect.soft(decodeFtmsRangeRaw(c.kind, bytes, c.options)).toStrictEqual(c.expected);
        if (c.options.resistanceFormat === "uint8Whole") {
          expect(decodeFtmsRangeRaw(c.kind, bytes)).toStrictEqual(c.expected);
          expect(Array.from(encodeFtmsRangeRaw(c.expected))).toStrictEqual(c.bytes);
        }
        expect.soft(Array.from(encodeFtmsRangeRaw(c.expected, c.options))).toStrictEqual(c.bytes);
      }
    });
});
