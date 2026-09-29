// biome-ignore-all lint/style/noNonNullAssertion: schema-valid fixture edits always supply a value when required.
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { Ajv2020 } from "ajv/dist/2020.js";
import { describe, expect, it } from "vitest";
import { evaluateFtmsCapabilities } from "../src/features.js";
import type { FtmsRangeFormatOptions } from "../src/types.js";

type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
const corpus = JSON.parse(
  readFileSync(
    new URL("../../../shared/conformance/capabilities/v1/vectors.json", import.meta.url),
    "utf8",
  ),
) as {
  snapshots: Record<string, Json>;
  reports: Record<string, Json>;
  cases: readonly { id: string; input: Expansion; expected: Expansion }[];
};
const schema = JSON.parse(
  readFileSync(
    new URL("../../../shared/conformance/capabilities/v1/schema.json", import.meta.url),
    "utf8",
  ),
) as object;
const ajv = new Ajv2020({ strict: false });
const validateCorpus = ajv.compile(schema);
const validateSnapshot = ajv.compile({
  $ref: "urn:ftms:capabilities:conformance:v1#/$defs/snapshot",
});
const validateReport = ajv.compile({ $ref: "urn:ftms:capabilities:conformance:v1#/$defs/report" });
type Expansion = {
  template: string;
  edits: readonly {
    path: readonly (string | number | "*" | readonly number[])[];
    op?: "replace" | "append" | "remove";
    value?: Json;
  }[];
};
const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

function edit(
  root: Json,
  path: readonly (string | number | "*" | readonly number[])[],
  op: string,
  value: Json | undefined,
): void {
  const walk = (node: Json, position: number): void => {
    const segment = path[position];
    if (segment === undefined) throw new Error("invalid empty edit path");
    const last = position === path.length - 1;
    const apply = (parent: Json, key: string | number): void => {
      if (last) {
        if (op === "remove") {
          if (Array.isArray(parent) && typeof key === "number") parent.splice(key, 1);
          else if (!Array.isArray(parent) && typeof parent === "object" && parent)
            delete parent[key];
          else throw new Error("invalid remove");
        } else if (op === "append") {
          const target = (parent as Record<string | number, Json>)[key];
          if (!Array.isArray(target)) throw new Error("append target");
          target.push(copy(value!));
        } else (parent as Record<string | number, Json>)[key] = copy(value!);
        return;
      }
      const child = (parent as Record<string | number, Json>)[key];
      if (child === undefined) throw new Error("missing edit path");
      walk(child, position + 1);
    };
    if (segment === "*" || Array.isArray(segment)) {
      if (!Array.isArray(node)) throw new Error("array selection target");
      const selected = segment === "*" ? node.map((_, i) => i) : segment;
      for (const index of selected) {
        if (index < 0 || index >= node.length) throw new Error("selection index");
        apply(node, index);
      }
    } else if (Array.isArray(node) && typeof segment !== "number") throw new Error("array key");
    else if (
      !Array.isArray(node) &&
      (typeof node !== "object" || node === null || typeof segment !== "string")
    )
      throw new Error("object key");
    else apply(node, segment as string | number);
  };
  if (path.length === 0) throw new Error("root edits are not used by this corpus");
  walk(root, 0);
}
function expand(source: Record<string, Json>, expansion: Expansion): Json {
  const result = copy(source[expansion.template]);
  if (result === undefined) throw new Error("unknown template");
  for (const entry of expansion.edits) edit(result, entry.path, entry.op ?? "replace", entry.value);
  return result;
}
function snapshot(json: Json) {
  const value = json as {
    discovery: 0 | 1 | 2 | 3;
    scope: 0 | 1 | 2 | 3;
    generation: number;
    characteristics: {
      uuid: string;
      properties: number;
      readState: 0 | 1 | 2;
      reason: 0 | 1 | 2 | 3 | 4 | 5;
      bytes: string;
    }[];
  };
  return {
    ...value,
    characteristics: value.characteristics.map((c) => ({
      ...c,
      bytes: Uint8Array.from(c.bytes.match(/../g)?.map((pair) => Number.parseInt(pair, 16)) ?? []),
    })),
  };
}

describe("capability conformance corpus", () => {
  it("propagates resistance format through complete evidence without changing other ranges", () => {
    const entry = corpus.cases.find((c) => c.id === "all-static-prerequisites")!;
    const input = snapshot(expand(corpus.snapshots, entry.input));
    const characteristic = input.characteristics.find(
      (c) => c.uuid === "00002ad600001000800000805f9b34fb",
    )!;
    characteristic.bytes = Uint8Array.of(0, 0, 100, 0, 1, 0);
    const expected = expand(corpus.reports, entry.expected) as Record<string, Json>;
    const ranges = expected.ranges as Json[][];
    ranges[2]![3] = [2, 0, 100, 1, 10, 2];
    const observations = expected.observations as Json[][];
    observations.find((row) => row[1] === characteristic.uuid)![6] = 6;
    expect(evaluateFtmsCapabilities(input, { resistanceFormat: "signed16Tenths" })).toStrictEqual(
      expected,
    );
    const historical = evaluateFtmsCapabilities(input);
    expect(historical.ranges[2]?.[1]).toBe(2);
    expect(evaluateFtmsCapabilities(input, { resistanceFormat: "uint8Whole" })).toStrictEqual(
      historical,
    );
    for (const value of [-1, 256, "guess"]) {
      expect(() =>
        evaluateFtmsCapabilities(input, {
          resistanceFormat: value,
        } as unknown as FtmsRangeFormatOptions),
      ).toThrow();
    }
    for (const options of [null, 1, "signed16Tenths", [], { typo: "signed16Tenths" }]) {
      expect(() =>
        evaluateFtmsCapabilities(input, options as unknown as FtmsRangeFormatOptions),
      ).toThrow();
    }
  });

  it("executes every canonical case with exact report equality", () => {
    expect(validateCorpus(corpus), JSON.stringify(validateCorpus.errors)).toBe(true);
    expect(corpus.cases).toHaveLength(49);
    expect(new Set(corpus.cases.map((entry) => entry.id)).size).toBe(corpus.cases.length);
    for (const entry of corpus.cases) {
      const input = expand(corpus.snapshots, entry.input);
      const expected = expand(corpus.reports, entry.expected);
      expect(validateSnapshot(input), JSON.stringify(validateSnapshot.errors)).toBe(true);
      expect(validateReport(expected), JSON.stringify(validateReport.errors)).toBe(true);
      expect(evaluateFtmsCapabilities(snapshot(input))).toStrictEqual(expected);
    }
  });

  it("accepts foreign-realm characteristic bytes", () => {
    const entry = corpus.cases[0]!;
    const input = snapshot(expand(corpus.snapshots, entry.input));
    const foreign = input.characteristics.map((characteristic) => ({
      ...characteristic,
      bytes: runInNewContext("Uint8Array.from(bytes)", {
        bytes: Array.from(characteristic.bytes),
      }) as Uint8Array,
    }));
    expect(evaluateFtmsCapabilities({ ...input, characteristics: foreign })).toStrictEqual(
      evaluateFtmsCapabilities(input),
    );
  });
});
