import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { Ajv2020 } from "ajv/dist/2020.js";
import { afterAll, describe, expect, it } from "vitest";
import schema from "../../../shared/conformance/v1/schema.json" with { type: "json" };
import vectors from "../../../shared/conformance/v1/vectors.json" with { type: "json" };
import {
  decodeFtmsControlResponse,
  decodeFtmsFeatures,
  decodeFtmsRange,
  type FtmsRangeKind,
  parseRegisteredFtmsPayload,
  tryEncodeFtmsControlRequest,
} from "../src/index.js";
import { expectV1Exact, expectV1Metrics, expectV1Subset } from "./conformance-comparison.js";

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
const conformanceRoot = resolve(repositoryRoot, "shared/conformance");
const v1Categories = [
  "features",
  "ranges",
  "controls",
  "controlResponses",
  "measurements",
  "statuses",
  "diagnostics",
] as const;
type V1Category = (typeof v1Categories)[number];
type V1Outcome = { category: V1Category; id: string; outcome: "passed" | "failed"; error?: string };

const outcomes: V1Outcome[] = [];
const runnerErrors: string[] = [];
let completedRunnerChecks = 0;

function describeError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function runV1Case(category: V1Category, id: string, assertion: () => void): void {
  try {
    assertion();
    outcomes.push({ category, id, outcome: "passed" });
  } catch (error) {
    outcomes.push({ category, id, outcome: "failed", error: describeError(error) });
    throw error;
  }
}

function runRunnerCheck(assertion: () => void): void {
  try {
    assertion();
    completedRunnerChecks += 1;
  } catch (error) {
    runnerErrors.push(describeError(error));
    throw error;
  }
}

function sha256(path: string): string {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function gitOutput(...args: string[]): string {
  return execFileSync("git", args, { cwd: repositoryRoot, encoding: "utf8" }).trim();
}

afterAll(() => {
  const expectedCategoryCounts = Object.fromEntries(
    v1Categories.map((category) => [category, vectors[category].length]),
  );
  const categoryCounts = Object.fromEntries(
    v1Categories.map((category) => [
      category,
      outcomes.filter((outcome) => outcome.category === category).length,
    ]),
  );
  const failures = outcomes.filter((outcome) => outcome.outcome === "failed");
  const skippedCases = v1Categories.flatMap((category) =>
    vectors[category]
      .filter(
        (vector) =>
          !outcomes.some((outcome) => outcome.category === category && outcome.id === vector.id),
      )
      .map(({ id }) => ({
        category,
        id,
        reason: "Case did not execute (filtered, skipped, or interrupted)",
      })),
  );
  if (completedRunnerChecks !== 2 && runnerErrors.length === 0) {
    runnerErrors.push("Corpus validation/provenance checks did not both execute successfully");
  }
  const total = Object.values(expectedCategoryCounts).reduce((sum, count) => sum + count, 0);
  const report = {
    runner: "TypeScript Vitest v1 consumer",
    sourceCommit: gitOutput("rev-parse", "HEAD"),
    dirty: gitOutput("status", "--porcelain") !== "",
    schemaVersion: vectors.schemaVersion,
    schemaSha256: sha256(resolve(conformanceRoot, "v1/schema.json")),
    vectorsSha256: sha256(resolve(conformanceRoot, "v1/vectors.json")),
    contractSha256: sha256(resolve(conformanceRoot, "README.md")),
    expectedCategoryCounts,
    categoryCounts,
    total,
    passed: outcomes.filter((outcome) => outcome.outcome === "passed").length,
    failed: failures.length,
    unsupported: 0,
    skipped: skippedCases.length,
    skippedCases,
    failures,
    runnerErrors,
    complete: outcomes.length === total && failures.length === 0 && runnerErrors.length === 0,
  };
  console.info(`[ftms conformance summary] ${JSON.stringify(report)}`);
});

describe("language-neutral conformance corpus v1", () => {
  it("is coupled to its immutable versioned schema", () => {
    runRunnerCheck(() => {
      expect(vectors.$schema).toBe("./schema.json");
      expect(vectors.schemaVersion).toBe(1);
      expect(schema.$id).toMatch(/\/v0\.2\.0\/conformance\/v1\/schema\.json$/);
      const validate = new Ajv2020({ allErrors: true, strict: true }).compile(schema);
      expect(validate(vectors), JSON.stringify(validate.errors, null, 2)).toBe(true);
    });
  });

  it("has resolvable provenance, mandatory errata, and globally unique IDs", () => {
    runRunnerCheck(() => {
      const sourceIds = new Set(vectors.provenance.map(({ id }) => id));
      expect(vectors.errata.map(({ id }) => id)).toEqual(
        expect.arrayContaining(["E8991", "E9135", "EC23224"]),
      );

      const categories = v1Categories.map((category) => vectors[category]);
      const allVectors = categories.flat();
      expect(categories.every((category) => category.length > 0)).toBe(true);
      expect(new Set(allVectors.map(({ id }) => id)).size).toBe(allVectors.length);
      for (const vector of [...allVectors, ...vectors.errata]) {
        expect(vector.source.length, "source attribution must not be empty").toBeGreaterThan(0);
        for (const source of vector.source) expect(sourceIds.has(source), source).toBe(true);
      }
    });
  });

  it.each(vectors.features)("matches feature vector $id", (vector) => {
    runV1Case("features", vector.id, () => {
      const result = decodeFtmsFeatures(Uint8Array.from(vector.bytes));
      expect(result.ok).toBe(true);
      if (!result.ok) return;
      if ("expected" in vector) {
        expectV1Exact(result.value, vector.expected, "feature object");
      } else {
        const actualTrue = Object.entries(result.value)
          .filter(([, value]) => value === true)
          .map(([name]) => name)
          .sort();
        expectV1Exact(actualTrue, [...vector.expectedTrue].sort(), "feature true set");
      }
    });
  });

  it.each(vectors.ranges)("matches supported-range vector $id", (vector) => {
    runV1Case("ranges", vector.id, () => {
      const result = decodeFtmsRange(vector.kind as FtmsRangeKind, Uint8Array.from(vector.bytes));
      if ("expectedError" in vector) {
        expectV1Subset(result, { ok: false, error: { code: vector.expectedError } }, "range error");
      } else {
        expect(result.ok).toBe(true);
        if (result.ok)
          expectV1Exact(result.value, { kind: vector.kind, ...vector.expected }, "range");
      }
    });
  });

  it.each(vectors.controls)("matches control request vector $id", (vector) => {
    runV1Case("controls", vector.id, () => {
      const result = tryEncodeFtmsControlRequest(vector.request);
      expect(result.ok).toBe(true);
      if (result.ok) expectV1Exact(Array.from(result.value), vector.expectedBytes, "control bytes");
    });
  });

  it.each(vectors.controlResponses)("matches control response vector $id", (vector) => {
    runV1Case("controlResponses", vector.id, () => {
      const result = decodeFtmsControlResponse(Uint8Array.from(vector.bytes));
      if ("expectedError" in vector) {
        expectV1Subset(
          result,
          { ok: false, error: { code: vector.expectedError } },
          "control response error",
        );
      } else {
        expect(result.ok).toBe(true);
        if (result.ok) {
          expectV1Exact(
            { ...result.value, issues: result.value.issues.map(({ code }) => code) },
            vector.expected,
            "control response",
          );
        }
      }
    });
  });

  it.each(vectors.measurements)("matches measurement vector $id", (vector) => {
    runV1Case("measurements", vector.id, () => {
      const result = parseRegisteredFtmsPayload(
        vector.characteristicUuid,
        Uint8Array.from(vector.bytes),
      );
      expect(result?.kind).toBe("measurement");
      expectV1Metrics(result?.metrics ?? {}, vector.expectedMetrics);
    });
  });

  it.each(vectors.statuses)("matches status vector $id", (vector) => {
    runV1Case("statuses", vector.id, () => {
      const result = parseRegisteredFtmsPayload(
        vector.characteristicUuid,
        Uint8Array.from(vector.bytes),
      );
      expectV1Subset(result?.status, vector.expectedStatus, "status");
    });
  });

  it.each(vectors.diagnostics)("matches diagnostic vector $id", (vector) => {
    runV1Case("diagnostics", vector.id, () => {
      const result = parseRegisteredFtmsPayload(
        vector.characteristicUuid,
        Uint8Array.from(vector.bytes),
      );
      expect(result).not.toBeNull();
      expect(result?.diagnostics.truncated).toBe(vector.expectedTruncated);
      const codes = result?.diagnostics.issues.map(({ code }) => code) ?? [];
      for (const code of vector.expectedIssues) expect(codes).toContain(code);
      if ("expectedMetrics" in vector)
        expectV1Metrics(result?.metrics ?? {}, vector.expectedMetrics);
      if ("expectedStatusCode" in vector)
        expect(result?.status?.code).toBe(vector.expectedStatusCode);
    });
  });
});
