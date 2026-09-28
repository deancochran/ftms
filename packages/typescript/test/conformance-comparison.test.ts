import { describe, expect, it } from "vitest";
import {
  expectV1Exact,
  expectV1Metric,
  expectV1Subset,
  V1_METRIC_ABSOLUTE_TOLERANCE,
} from "./conformance-comparison.js";

describe("v1 conformance metric comparison", () => {
  it("uses finite absolute difference strictly below 0.005", () => {
    expectV1Metric(10.004999, 10, "below positive boundary");
    expectV1Metric(-10.004999, -10, "below negative boundary");
    expectV1Metric(0, 0, "zero");

    expect(() => expectV1Metric(10.005, 10, "positive boundary")).toThrow();
    expect(() => expectV1Metric(-10.005, -10, "negative boundary")).toThrow();
    expect(V1_METRIC_ABSOLUTE_TOLERANCE).toBe(0.005);
  });

  it("rejects non-finite and absent numeric actual values", () => {
    for (const actual of [
      Number.NaN,
      Number.POSITIVE_INFINITY,
      Number.NEGATIVE_INFINITY,
      undefined,
      null,
    ]) {
      expect(() => expectV1Metric(actual, 0, "numeric metric")).toThrow();
    }
  });

  it("compares null and string values exactly", () => {
    expectV1Metric(null, null, "unavailable");
    expectV1Metric("running", "running", "status label");
    expect(() => expectV1Metric(undefined, null, "missing unavailable")).toThrow();
    expect(() => expectV1Metric(0, "0", "numeric string")).toThrow();
  });

  it("uses strict equality for exact objects and dense arrays", () => {
    expectV1Exact({ value: 0 }, { value: 0 }, "plain object");
    expectV1Exact([0, 1], [0, 1], "dense array");

    expect(() =>
      expectV1Exact({ value: 0, extra: undefined }, { value: 0 }, "extra key"),
    ).toThrow();
    const sparse = Array<number | undefined>(3);
    sparse[0] = 0;
    sparse[2] = 1;
    expect(() => expectV1Exact(sparse, [0, undefined, 1], "sparse array")).toThrow();
  });

  it("uses recursive subset objects with equal-length ordered arrays", () => {
    expectV1Subset(
      { nested: { expected: true, extra: "permitted" }, entries: [{ id: "first", extra: 1 }] },
      { nested: { expected: true }, entries: [{ id: "first" }] },
      "nested subset",
    );

    expect(() =>
      expectV1Subset([{ id: "first" }, { id: "second" }], [{ id: "first" }], "extra entry"),
    ).toThrow();
    expect(() =>
      expectV1Subset(
        [{ id: "second" }, { id: "first" }],
        [{ id: "first" }, { id: "second" }],
        "reordered entries",
      ),
    ).toThrow();
  });
});
