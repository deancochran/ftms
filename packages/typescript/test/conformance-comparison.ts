import { expect } from "vitest";

/**
 * The v1 corpus inherited Vitest's default `toBeCloseTo` precision (2): finite
 * numeric metrics are accepted only when their absolute difference is < 0.005.
 * Keep that policy visible instead of relying on a matcher default.
 */
export const V1_METRIC_ABSOLUTE_TOLERANCE = 0.005;

export function expectV1Exact(actual: unknown, expected: unknown, name: string): void {
  expect(actual, name).toStrictEqual(expected);
}

/**
 * v1 subset comparisons use Vitest's recursive `toMatchObject` semantics:
 * expected object keys are required, arrays have equal length and ordered
 * recursively matching elements, and actual object keys may be additional.
 */
export function expectV1Subset(actual: unknown, expected: unknown, name: string): void {
  expect(actual as object, name).toMatchObject(expected as object);
}

export function expectV1Metric(
  actual: unknown,
  expected: number | string | null,
  name: string,
): void {
  if (typeof expected !== "number") {
    expect(actual, name).toBe(expected);
    return;
  }

  expect(typeof actual, name).toBe("number");
  expect(Number.isFinite(actual), name).toBe(true);
  expect(Math.abs((actual as number) - expected), name).toBeLessThan(V1_METRIC_ABSOLUTE_TOLERANCE);
}

export function expectV1Metrics(
  actual: object,
  expected: Record<string, number | string | null>,
): void {
  for (const [name, value] of Object.entries(expected)) {
    expectV1Metric(Reflect.get(actual, name), value, name);
  }
}
