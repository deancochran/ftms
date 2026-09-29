import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { inspectFtmsRangeRaw } from "../src/features.js";
import {
  type FtmsRangeFormatOptions,
  type FtmsRangeInspection,
  type FtmsRangeRaw,
  RawCodecError,
} from "../src/types.js";

type Fixture = {
  id: string;
  kind: FtmsRangeRaw["kind"];
  bytes: number[];
  options?: FtmsRangeFormatOptions;
  expected: FtmsRangeInspection;
};
const fixtures = JSON.parse(
  readFileSync(
    new URL("../../../shared/conformance/inspection/v1/fixtures.json", import.meta.url),
    "utf8",
  ),
) as { cases: Fixture[] };

describe("range inspection", () => {
  it.each(fixtures.cases)("reports synthetic fixture $id", (fixture) => {
    const result = inspectFtmsRangeRaw(
      fixture.kind,
      Uint8Array.from(fixture.bytes),
      fixture.options,
    );
    expect(result).toStrictEqual(fixture.expected);
  });
  it("preserves caller selection when a structural alternative succeeds", () => {
    const result = inspectFtmsRangeRaw("resistance", Uint8Array.of(0, 0, 100, 0, 1, 0));
    expect(result.status).toBe("length");
    expect(result.value).toBeNull();
    expect(result.candidates).toMatchObject([
      { profile: "uint8Whole", status: "length", value: null },
      {
        profile: "signed16Tenths",
        status: "valid",
        value: { minimum: 0, maximum: 100, increment: 1 },
      },
    ]);
  });
  it("accounts for every fixture and copies selected value independently", () => {
    expect(fixtures.cases).toHaveLength(9);
    expect(new Set(fixtures.cases.map((c) => c.id)).size).toBe(9);
    const result = inspectFtmsRangeRaw("resistance", Uint8Array.of(1, 100, 1));
    expect(result.value).not.toBe(result.candidates[0]?.value);
  });
  it("keeps caller configuration errors distinct from packet diagnostics", () => {
    for (const options of [
      null,
      { resistanceFormat: "auto" },
      Object.create({ resistanceFormat: "signed16Tenths" }),
    ]) {
      expect(() =>
        inspectFtmsRangeRaw("resistance", new Uint8Array(), options as FtmsRangeFormatOptions),
      ).toThrow(RawCodecError);
    }
    expect(() =>
      inspectFtmsRangeRaw("power", new Uint8Array(6), { resistanceFormat: "signed16Tenths" }),
    ).toThrow(RawCodecError);
    expect(() => inspectFtmsRangeRaw("resistance", null as unknown as Uint8Array)).toThrow(
      RawCodecError,
    );
    expect(inspectFtmsRangeRaw("resistance", new Uint8Array()).status).toBe("length");
  });
});
