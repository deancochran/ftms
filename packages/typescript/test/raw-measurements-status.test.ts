import { runInNewContext } from "node:vm";
import { Ajv2020 } from "ajv/dist/2020.js";
import { describe, expect, it } from "vitest";
import measurementsSchema from "../../../shared/conformance/measurements/v1/schema.json" with {
  type: "json",
};
import measurements from "../../../shared/conformance/measurements/v1/vectors.json" with {
  type: "json",
};
import statusesSchema from "../../../shared/conformance/statuses/v1/schema.json" with {
  type: "json",
};
import statuses from "../../../shared/conformance/statuses/v1/vectors.json" with { type: "json" };
import { decodeFtmsControlRequestRaw } from "../src/control.js";
import { decodeFtmsFeaturesRaw, evaluateFtmsCapabilities } from "../src/features.js";
import {
  decodeFtmsMachineStatusRaw,
  decodeFtmsMeasurementRaw,
  decodeFtmsTrainingStatusRaw,
  encodeFtmsMachineStatusRaw,
  encodeFtmsMeasurementRaw,
  encodeFtmsTrainingStatusRaw,
} from "../src/parsers.js";
import { RawCodecError } from "../src/types.js";

const hex = (b: Uint8Array) => Array.from(b);
const textBytes = (textHex: string) =>
  Uint8Array.from(
    Array.from({ length: textHex.length / 2 }, (_, i) =>
      Number.parseInt(textHex.slice(i * 2, i * 2 + 2), 16),
    ),
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
describe("raw measurement corpus", () => {
  it("validates schema, cardinality, and unique IDs", () => {
    const validate = new Ajv2020({ allErrors: true, strict: true }).compile(measurementsSchema);
    expect(validate(measurements), JSON.stringify(validate.errors)).toBe(true);
    expect(measurements.cases).toHaveLength(26);
    expect(new Set(measurements.cases.map((entry) => entry.id)).size).toBe(26);
  });
  for (const c of measurements.cases)
    it(c.id, () => {
      if ("error" in c.decoded) {
        const code = ({ 2: "length", 3: "kind", 4: "range" } as const)[
          c.decoded.error as 2 | 3 | 4
        ];
        expect(code).toBeDefined();
        expectRawError(code, () => decodeFtmsMeasurementRaw(c.kind, new Uint8Array(c.bytes)));
        return;
      }
      const actual = decodeFtmsMeasurementRaw(c.kind, new Uint8Array(c.bytes));
      expect(actual).toStrictEqual(c.decoded);
      if (c.encode)
        expect(
          hex(
            encodeFtmsMeasurementRaw(c.decoded as Parameters<typeof encodeFtmsMeasurementRaw>[0]),
          ),
        ).toEqual(c.bytes);
    });
});
describe("raw status corpus", () => {
  it("validates schema, cardinality, and unique IDs", () => {
    const validate = new Ajv2020({ allErrors: true, strict: false }).compile(statusesSchema);
    expect(validate(statuses), JSON.stringify(validate.errors)).toBe(true);
    expect(statuses.machine).toHaveLength(28);
    expect(statuses.training).toHaveLength(10);
    const ids = [...statuses.machine, ...statuses.training].map((entry) => entry.id);
    expect(new Set(ids).size).toBe(38);
  });
  for (const c of statuses.machine)
    it(c.id, () => {
      expect(decodeFtmsMachineStatusRaw(new Uint8Array(c.bytes))).toStrictEqual(c.decoded);
      if (c.encode) expect(hex(encodeFtmsMachineStatusRaw(c.decoded))).toEqual(c.bytes);
    });
  for (const c of statuses.training)
    it(c.id, () => {
      const { textHex, ...expected } = c.decoded;
      const text = textHex ? Array.from(textBytes(textHex)) : [];
      const decoded = decodeFtmsTrainingStatusRaw(new Uint8Array(c.bytes));
      expect({ ...decoded, text: Array.from(decoded.text) }).toStrictEqual({ ...expected, text });
      if (c.encode)
        expect(
          hex(
            encodeFtmsTrainingStatusRaw({
              ...expected,
              text: textHex ? textBytes(textHex) : new Uint8Array(),
            }),
          ),
        ).toEqual(c.bytes);
    });
});

describe("raw binary boundary", () => {
  it("rejects forged ArrayBuffer and typed-array tags", () => {
    const fake = { [Symbol.toStringTag]: "ArrayBuffer" };
    const wrongView = new Uint16Array(4);
    Object.defineProperty(wrongView, Symbol.toStringTag, { value: "Uint8Array" });
    for (const value of [fake, wrongView]) {
      const bytes = value as unknown as Uint8Array;
      expectRawError("null", () => decodeFtmsMeasurementRaw(0, bytes));
      expectRawError("null", () => decodeFtmsMachineStatusRaw(bytes));
      expectRawError("null", () => decodeFtmsTrainingStatusRaw(bytes));
      expectRawError("null", () => decodeFtmsFeaturesRaw(bytes));
      expectRawError("null", () => decodeFtmsControlRequestRaw(bytes));
      expectRawError("null", () =>
        evaluateFtmsCapabilities({
          discovery: 2,
          scope: 1,
          generation: 0,
          characteristics: [
            {
              uuid: "00002acc00001000800000805f9b34fb",
              properties: 2,
              readState: 1,
              reason: 0,
              bytes,
            },
          ],
        }),
      );
    }
  });
  it("accounts for every declared encode/decode direction", () => {
    expect(measurements.cases.reduce((n, c) => n + 1 + Number(c.encode), 0)).toBe(47);
    expect(
      [...statuses.machine, ...statuses.training].reduce((n, c) => n + 1 + Number(c.encode), 0),
    ).toBe(63);
  });

  it("diagnoses every incomplete prefix of all six full measurement layouts", () => {
    const full = measurements.cases.filter((c) => c.id.startsWith("equipment-"));
    expect(full).toHaveLength(6);
    for (const c of full) {
      const flagsLength = c.kind === 1 ? 3 : 2;
      for (let length = 0; length < c.bytes.length; length++) {
        const input = Uint8Array.from(c.bytes.slice(0, length));
        if (length < flagsLength) {
          expectRawError("length", () => decodeFtmsMeasurementRaw(c.kind, input));
        } else {
          const actual = decodeFtmsMeasurementRaw(c.kind, input);
          expect(actual.truncated).toBe(1);
          expect(actual.bytesRead).toBeLessThanOrEqual(length);
          expect(actual.unavailable & ~actual.present).toBe(0);
        }
      }
    }
  });

  it("retains invalid UTF-8 evidence but refuses to encode it", () => {
    for (const text of [
      [0xc0, 0x80],
      [0xed, 0xa0, 0x80],
      [0xf4, 0x90, 0x80, 0x80],
      [0xe2, 0x82],
    ]) {
      const decoded = decodeFtmsTrainingStatusRaw(Uint8Array.from([1, 13, ...text]));
      expect(decoded.invalidUtf8).toBe(1);
      expect(Array.from(decoded.text)).toStrictEqual(text);
      expectRawError("range", () => encodeFtmsTrainingStatusRaw({ ...decoded, invalidUtf8: 0 }));
    }
  });

  it("rejects fractional and nonfinite selected measurement values and masks", () => {
    const c = measurements.cases.find((c) => c.id === "bike-max-power");
    if (!c || "error" in c.decoded) throw new Error("Missing power fixture");
    const input = c.decoded as Parameters<typeof encodeFtmsMeasurementRaw>[0];
    for (const value of [NaN, Infinity, -Infinity, 1.5]) {
      expectRawError("range", () => encodeFtmsMeasurementRaw({ ...input, present: value }));
      const values = [...input.values];
      values[17] = value;
      expectRawError("range", () => encodeFtmsMeasurementRaw({ ...input, values }));
    }
  });
  it("accepts foreign-realm bytes for every raw decoder", () => {
    const foreign = (bytes: readonly number[]) =>
      runInNewContext("Uint8Array.from(bytes)", { bytes: Array.from(bytes) }) as Uint8Array;
    expect(decodeFtmsMeasurementRaw(0, foreign([0, 0, 0, 0]))).toStrictEqual(
      decodeFtmsMeasurementRaw(0, new Uint8Array([0, 0, 0, 0])),
    );
    expect(decodeFtmsMachineStatusRaw(foreign([1]))).toStrictEqual(
      decodeFtmsMachineStatusRaw(new Uint8Array([1])),
    );
    expect(decodeFtmsTrainingStatusRaw(foreign([0, 0]))).toStrictEqual(
      decodeFtmsTrainingStatusRaw(new Uint8Array([0, 0])),
    );
  });

  it("requires null parameters for action machine statuses", () => {
    for (const opcode of [2, 20])
      expectRawError("range", () =>
        encodeFtmsMachineStatusRaw({
          opcode,
          action: 1,
          parameter: { opcode: 0, operands: [] },
          unknownOpcode: 0,
          reservedValue: 0,
          truncated: 0,
          trailingBytes: 0,
        }),
      );
  });

  it("accepts foreign-realm training text", () => {
    const text = runInNewContext("Uint8Array.from([69, 82, 71])") as Uint8Array;
    expect(
      hex(
        encodeFtmsTrainingStatusRaw({
          flags: 1,
          code: 12,
          text,
          textOffset: 2,
          textSize: 3,
          textPresent: 1,
          extendedString: 0,
          reservedFlags: 0,
          reservedValue: 0,
          invalidFlags: 0,
          invalidUtf8: 0,
          truncated: 0,
          trailingBytes: 0,
        }),
      ),
    ).toStrictEqual([1, 12, 69, 82, 71]);
  });
});
