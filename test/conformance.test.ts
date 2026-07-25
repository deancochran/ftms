import { Ajv2020 } from "ajv/dist/2020.js";
import { describe, expect, it } from "vitest";
import schema from "../conformance/v1/schema.json" with { type: "json" };
import vectors from "../conformance/v1/vectors.json" with { type: "json" };
import {
  decodeFtmsControlResponse,
  decodeFtmsFeatures,
  decodeFtmsRange,
  type FtmsRangeKind,
  parseRegisteredFtmsPayload,
  tryEncodeFtmsControlRequest,
} from "../src/index.js";

function expectMetrics(actual: object, expected: Record<string, number | string | null>): void {
  for (const [name, value] of Object.entries(expected)) {
    if (typeof value === "number") {
      expect(Reflect.get(actual, name), name).toBeCloseTo(value);
    } else {
      expect(Reflect.get(actual, name), name).toBe(value);
    }
  }
}

describe("language-neutral conformance corpus v1", () => {
  it("is coupled to its immutable versioned schema", () => {
    expect(vectors.$schema).toBe("./schema.json");
    expect(vectors.schemaVersion).toBe(1);
    expect(schema.$id).toMatch(/\/v0\.2\.0\/conformance\/v1\/schema\.json$/);
    const validate = new Ajv2020({ allErrors: true, strict: true }).compile(schema);
    expect(validate(vectors), JSON.stringify(validate.errors, null, 2)).toBe(true);
  });

  it("has resolvable provenance, mandatory errata, and globally unique IDs", () => {
    const sourceIds = new Set(vectors.provenance.map(({ id }) => id));
    expect(vectors.errata.map(({ id }) => id)).toEqual(expect.arrayContaining(["E8991", "E9135"]));

    const categories = [
      vectors.features,
      vectors.ranges,
      vectors.controls,
      vectors.controlResponses,
      vectors.measurements,
      vectors.statuses,
      vectors.diagnostics,
    ];
    const allVectors = categories.flat();
    expect(categories.every((category) => category.length > 0)).toBe(true);
    expect(new Set(allVectors.map(({ id }) => id)).size).toBe(allVectors.length);
    for (const vector of [...allVectors, ...vectors.errata]) {
      expect(vector.source.length, "source attribution must not be empty").toBeGreaterThan(0);
      for (const source of vector.source) expect(sourceIds.has(source), source).toBe(true);
    }
  });

  it.each(vectors.features)("matches feature vector $id", (vector) => {
    const result = decodeFtmsFeatures(Uint8Array.from(vector.bytes));
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    if ("expected" in vector) {
      expect(result.value).toEqual(vector.expected);
    } else {
      const actualTrue = Object.entries(result.value)
        .filter(([, value]) => value === true)
        .map(([name]) => name)
        .sort();
      expect(actualTrue).toEqual([...vector.expectedTrue].sort());
    }
  });

  it.each(vectors.ranges)("matches supported-range vector $id", (vector) => {
    const result = decodeFtmsRange(vector.kind as FtmsRangeKind, Uint8Array.from(vector.bytes));
    if ("expectedError" in vector) {
      expect(result).toMatchObject({ ok: false, error: { code: vector.expectedError } });
    } else {
      expect(result.ok).toBe(true);
      if (result.ok) expect(result.value).toEqual({ kind: vector.kind, ...vector.expected });
    }
  });

  it.each(vectors.controls)("matches control request vector $id", ({ request, expectedBytes }) => {
    const result = tryEncodeFtmsControlRequest(request);
    expect(result.ok).toBe(true);
    if (result.ok) expect(Array.from(result.value)).toEqual(expectedBytes);
  });

  it.each(vectors.controlResponses)("matches control response vector $id", (vector) => {
    const result = decodeFtmsControlResponse(Uint8Array.from(vector.bytes));
    if ("expectedError" in vector) {
      expect(result).toMatchObject({ ok: false, error: { code: vector.expectedError } });
    } else {
      expect(result.ok).toBe(true);
      if (result.ok) {
        expect({
          ...result.value,
          parameters: Array.from(result.value.parameters ?? []),
        }).toEqual(vector.expected);
      }
    }
  });

  it.each(vectors.measurements)("matches measurement vector $id", (vector) => {
    const result = parseRegisteredFtmsPayload(
      vector.characteristicUuid,
      Uint8Array.from(vector.bytes),
    );
    expect(result?.kind).toBe("measurement");
    expectMetrics(result?.metrics ?? {}, vector.expectedMetrics);
  });

  it.each(vectors.statuses)("matches status vector $id", (vector) => {
    const result = parseRegisteredFtmsPayload(
      vector.characteristicUuid,
      Uint8Array.from(vector.bytes),
    );
    expect(result?.status).toMatchObject(vector.expectedStatus);
  });

  it.each(vectors.diagnostics)("matches diagnostic vector $id", (vector) => {
    const result = parseRegisteredFtmsPayload(
      vector.characteristicUuid,
      Uint8Array.from(vector.bytes),
    );
    expect(result).not.toBeNull();
    expect(result?.diagnostics.truncated).toBe(vector.expectedTruncated);
    const codes = result?.diagnostics.issues.map(({ code }) => code) ?? [];
    for (const code of vector.expectedIssues) expect(codes).toContain(code);
    if ("expectedMetrics" in vector) expectMetrics(result?.metrics ?? {}, vector.expectedMetrics);
    if ("expectedStatusCode" in vector)
      expect(result?.status?.code).toBe(vector.expectedStatusCode);
  });
});
