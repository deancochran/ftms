import { runInNewContext } from "node:vm";
import { Ajv2020 } from "ajv/dist/2020.js";
import { describe, expect, it } from "vitest";
import controlsSchema from "../../../shared/conformance/controls/v1/schema.json" with {
  type: "json",
};
import controls from "../../../shared/conformance/controls/v1/vectors.json" with { type: "json" };
import valuesSchema from "../../../shared/conformance/values/v1/schema.json" with { type: "json" };
import values from "../../../shared/conformance/values/v1/vectors.json" with { type: "json" };
import {
  decodeFtmsControlRequestRaw,
  decodeFtmsControlResponseRaw,
  decodeFtmsFeaturesRaw,
  decodeFtmsRangeRaw,
  encodeFtmsControlRequestRaw,
  encodeFtmsControlResponseRaw,
  encodeFtmsFeaturesRaw,
  encodeFtmsRangeRaw,
  type FtmsFeaturesRaw,
  type FtmsRangeRaw,
  RawCodecError,
} from "../src/index.js";

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

describe("raw feature and supported-range conformance", () => {
  it("validates the canonical values corpus schema", () => {
    const validate = new Ajv2020({ allErrors: true, strict: true }).compile(valuesSchema);
    expect(validate(values), JSON.stringify(validate.errors)).toBe(true);
  });

  for (const vector of values.cases) {
    it(`${vector.id} encodes literal raw values`, () => {
      const actual =
        vector.operation === "features"
          ? encodeFtmsFeaturesRaw({
              machine: vector.machine as number,
              target: vector.target as number,
            })
          : encodeFtmsRangeRaw(vector as FtmsRangeRaw);
      expect(Array.from(actual)).toEqual(vector.expectedBytes);
    });
    it(`${vector.id} decodes literal raw values`, () => {
      const actual =
        vector.operation === "features"
          ? decodeFtmsFeaturesRaw(new Uint8Array(vector.expectedBytes))
          : decodeFtmsRangeRaw(
              vector.kind as FtmsRangeRaw["kind"],
              new Uint8Array(vector.expectedBytes).buffer,
            );
      const expected =
        vector.operation === "features"
          ? ({ machine: vector.machine, target: vector.target } as FtmsFeaturesRaw)
          : ({
              kind: vector.kind,
              minimum: vector.minimum,
              maximum: vector.maximum,
              increment: vector.increment,
              scaleDivisor: vector.scaleDivisor,
              unit: vector.unit,
            } as FtmsRangeRaw);
      expect(actual).toEqual(expected);
    });
  }

  it("rejects non-integral and out-of-width raw values before DataView conversion", () => {
    expectRawError("range", () => encodeFtmsFeaturesRaw({ machine: 1.5, target: 0 }));
    expectRawError("range", () => encodeFtmsFeaturesRaw({ machine: Number.NaN, target: 0 }));
    expectRawError("range", () => encodeFtmsFeaturesRaw({ machine: Infinity, target: 0 }));
    expectRawError("range", () => encodeFtmsFeaturesRaw({ machine: 0x1_0000_0000, target: 0 }));
    expectRawError("range", () =>
      encodeFtmsRangeRaw({
        kind: "speed",
        minimum: -1,
        maximum: 1,
        increment: 1,
        scaleDivisor: 100,
        unit: 0,
      }),
    );
    expectRawError("range", () =>
      encodeFtmsRangeRaw({
        kind: "inclination",
        minimum: -32769,
        maximum: 1,
        increment: 1,
        scaleDivisor: 10,
        unit: 1,
      }),
    );
    expectRawError("range", () =>
      encodeFtmsRangeRaw({
        kind: "power",
        minimum: -1,
        maximum: 32768,
        increment: 1,
        scaleDivisor: 1,
        unit: 4,
      }),
    );
  });

  it("accepts foreign-realm byte containers and rejects other views", () => {
    const foreignBytes = runInNewContext("Uint8Array.from([1, 0, 0, 0, 2, 0, 0, 0])") as Uint8Array;
    const foreignBuffer = runInNewContext(
      "Uint8Array.from([1, 0, 0, 0, 2, 0, 0, 0]).buffer",
    ) as ArrayBuffer;
    expect(decodeFtmsFeaturesRaw(foreignBytes)).toStrictEqual({ machine: 1, target: 2 });
    expect(decodeFtmsFeaturesRaw(foreignBuffer)).toStrictEqual({ machine: 1, target: 2 });
    for (const invalid of [new DataView(new ArrayBuffer(8)), new Uint16Array(4)])
      expectRawError("null", () => decodeFtmsFeaturesRaw(invalid as never));
  });

  it("classifies prototype-named range kinds as raw kind errors", () => {
    for (const kind of ["__proto__", "constructor"])
      expectRawError("kind", () => {
        decodeFtmsRangeRaw(kind as never, new Uint8Array(6));
      });
    for (const kind of ["__proto__", "constructor"])
      expectRawError("kind", () => {
        encodeFtmsRangeRaw({
          kind: kind as never,
          minimum: 0,
          maximum: 1,
          increment: 1,
          scaleDivisor: 1,
          unit: 0,
        });
      });
  });
});

describe("raw Control Point conformance", () => {
  it("validates the canonical controls corpus schema and unique IDs", () => {
    const validate = new Ajv2020({ allErrors: true, strict: true }).compile(controlsSchema);
    expect(validate(controls), JSON.stringify(validate.errors)).toBe(true);
    const cases = [...controls.requests, ...controls.responses, ...controls.invalid];
    expect(new Set(cases.map((vector) => vector.id)).size).toBe(cases.length);
  });

  for (const vector of controls.requests) {
    it(`${vector.id} encodes its literal bytes`, () =>
      expect(Array.from(encodeFtmsControlRequestRaw(vector.decoded))).toEqual(vector.bytes));
    it(`${vector.id} decodes its literal bytes`, () =>
      expect(decodeFtmsControlRequestRaw(new Uint8Array(vector.bytes))).toEqual(vector.decoded));
  }
  for (const vector of controls.responses) {
    it(`${vector.id} decodes its literal bytes`, () =>
      expect(decodeFtmsControlResponseRaw(new Uint8Array(vector.bytes))).toEqual(vector.decoded));
    if (vector.encode !== false)
      it(`${vector.id} encodes its literal bytes`, () =>
        expect(Array.from(encodeFtmsControlResponseRaw(vector.decoded))).toEqual(vector.bytes));
  }
  for (const vector of controls.invalid) {
    it(`${vector.id} rejects with its canonical error`, () =>
      expectRawError(vector.error as RawCodecError["code"], () =>
        vector.operation === "request"
          ? decodeFtmsControlRequestRaw(new Uint8Array(vector.bytes))
          : decodeFtmsControlResponseRaw(new Uint8Array(vector.bytes)),
      ));
  }

  it("rejects invalid raw request and response encoders", () => {
    expectRawError("range", () => encodeFtmsControlRequestRaw({ opcode: 2, operands: [1.5] }));
    expectRawError("range", () =>
      encodeFtmsControlRequestRaw({ opcode: 2, operands: [Number.NaN] }),
    );
    expectRawError("range", () => encodeFtmsControlRequestRaw({ opcode: 2, operands: [Infinity] }));
    expectRawError("range", () =>
      encodeFtmsControlRequestRaw({ opcode: 12, operands: [0x1000000] }),
    );
    expectRawError("range", () => encodeFtmsControlRequestRaw({ opcode: 8, operands: [256] }));
    expectRawError("range", () => encodeFtmsControlRequestRaw({ opcode: 19, operands: [257] }));
    expectRawError("range", () => encodeFtmsControlRequestRaw({ opcode: 3, operands: [-32769] }));
    expectRawError("range", () => encodeFtmsControlRequestRaw({ opcode: 3, operands: [32768] }));
    expectRawError("kind", () =>
      encodeFtmsControlResponseRaw({
        requestOpcode: 250,
        resultCode: 1,
        parameter: 0,
        low: 0,
        high: 0,
        unknownRequest: 1,
        unknownResult: 0,
        unexpectedParameters: 0,
      }),
    );
    expectRawError("range", () =>
      encodeFtmsControlResponseRaw({
        requestOpcode: 2,
        resultCode: 6,
        parameter: 0,
        low: 0,
        high: 0,
        unknownRequest: 0,
        unknownResult: 0,
        unexpectedParameters: 0,
      }),
    );
  });

  it("accepts byte views with non-zero offsets and ArrayBuffers", () => {
    const padded = new Uint8Array([99, 2, 0xd2, 4, 99]).subarray(1, 4);
    expect(decodeFtmsControlRequestRaw(padded)).toEqual({ opcode: 2, operands: [1234] });
    expect(
      decodeFtmsControlRequestRaw(
        padded.buffer.slice(padded.byteOffset, padded.byteOffset + padded.byteLength),
      ),
    ).toEqual({ opcode: 2, operands: [1234] });
  });

  it("accepts foreign-realm bytes and rejects non-byte views", () => {
    const foreign = runInNewContext("Uint8Array.from([2, 0xd2, 4])") as Uint8Array;
    expect(decodeFtmsControlRequestRaw(foreign)).toStrictEqual({ opcode: 2, operands: [1234] });
    for (const invalid of [new DataView(new ArrayBuffer(3)), new Uint16Array(2)])
      expectRawError("null", () => decodeFtmsControlRequestRaw(invalid as never));
  });
});
