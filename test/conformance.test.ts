import { Ajv2020 } from "ajv/dist/2020.js";
import { describe, expect, it } from "vitest";
import schema from "../conformance/schema.json" with { type: "json" };
import vectors from "../conformance/v1/vectors.json" with { type: "json" };
import { parseRegisteredFtmsPayload, tryEncodeFtmsControlRequest } from "../src/index.js";

describe("language-neutral conformance corpus", () => {
  it("validates against its published JSON Schema", () => {
    const validate = new Ajv2020({ allErrors: true, strict: true }).compile(schema);
    const valid = validate(vectors);
    expect(valid, JSON.stringify(validate.errors)).toBe(true);
  });

  it("uses a versioned corpus with primary-source provenance", () => {
    expect(vectors.schemaVersion).toBe(1);
    expect(vectors.sources).toHaveLength(3);
  });

  it.each(vectors.controls)("matches control vector $id", ({ request, expectedBytes }) => {
    const result = tryEncodeFtmsControlRequest(request);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(Array.from(result.value)).toEqual(expectedBytes);
    }
  });

  it.each(vectors.measurements)("matches measurement vector $id", ({
    characteristicUuid,
    bytes,
    expectedMetrics,
  }) => {
    const result = parseRegisteredFtmsPayload(characteristicUuid, Uint8Array.from(bytes));
    expect(result).not.toBeNull();
    for (const [name, expected] of Object.entries(expectedMetrics)) {
      expect(Reflect.get(result?.metrics ?? {}, name)).toBeCloseTo(expected);
    }
  });

  it.each(vectors.statuses)("matches status vector $id", ({
    characteristicUuid,
    bytes,
    expectedCode,
  }) => {
    const result = parseRegisteredFtmsPayload(characteristicUuid, Uint8Array.from(bytes));
    expect(result?.status?.code).toBe(expectedCode);
  });
});
