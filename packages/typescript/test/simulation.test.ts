import { describe, expect, it } from "vitest";
import corpus from "../../../shared/simulation/v1/scenarios.json" with { type: "json" };
import { runCorpus, runSimulation, validateCorpus } from "./simulation/runner.js";
import type { Corpus, Feed } from "./simulation/types.js";

const copy = (): Corpus => structuredClone(corpus) as unknown as Corpus;
function firstFeed(data: Corpus): Feed {
  const step = data.scenarios[0]?.steps[0];
  if (step?.type !== "feed") throw new Error("first fixture must be a feed");
  return step;
}

describe("deterministic simulation v1", () => {
  it("accounts for every scenario and reproduces the full trace", () => {
    const before = structuredClone(corpus);
    const a = runSimulation(),
      b = runSimulation();
    console.log(JSON.stringify({ simulation: a }));
    expect(a).toStrictEqual(b);
    expect(a.complete).toBe(true);
    expect(a.runnerErrors).toEqual([]);
    expect(a.passed).toBe(corpus.scenarios.length);
    expect(a.steps).toBe(corpus.scenarios.reduce((n, s) => n + s.steps.length, 0));
    expect(a.trace).toHaveLength(a.steps);
    expect(corpus).toStrictEqual(before);
    expect(a.sourceCommit).toMatch(/^[0-9a-f]{40}$/);
    expect(Object.values(a.identity).every((hash) => /^[0-9a-f]{64}$/.test(hash))).toBe(true);
  });

  it("detects a wrong literal value and continues accounting", () => {
    const changed = copy();
    const expected = firstFeed(changed).expected;
    if (expected.status !== "complete") throw new Error("complete fixture required");
    const raw = expected.raw as { values: number[] };
    raw.values[0] = (raw.values[0] ?? 0) + 1;
    const report = runCorpus(changed);
    expect(report.complete).toBe(false);
    expect(report.failed).toBe(1);
    expect(report.failedSteps).toBe(1);
    expect(report.trace[0]?.outcome).toBe("failed");
    expect(report.steps).toBe(corpus.scenarios.reduce((n, s) => n + s.steps.length, 0));
  });

  it("rejects malformed inputs, unknown keys and unresolved references", () => {
    for (const input of [null, [], 1, "bad", { scenarios: null }]) {
      const report = runCorpus(input);
      expect(report.complete).toBe(false);
      expect(report.runnerErrors.length).toBeGreaterThan(0);
    }
    const mutations: ((data: Corpus) => void)[] = [
      (data) => {
        data.profiles.push({ ...data.profiles[0] } as Corpus["profiles"][number]);
      },
      (data) => {
        data.scenarios.push(structuredClone(data.scenarios[0]) as Corpus["scenarios"][number]);
      },
      (data) => {
        const scenario = data.scenarios[0];
        if (scenario) scenario.profile = "absent";
      },
      (data) => {
        Object.assign(firstFeed(data), { bytes: [true] });
      },
      (data) => {
        Object.assign(firstFeed(data), { unknown: 1 });
      },
      (data) => {
        Object.assign(firstFeed(data), { type: "capabilities", caseId: "absent" });
      },
      (data) => {
        data.scenarios = [];
      },
    ];
    for (const mutate of mutations) {
      const data = copy();
      mutate(data);
      expect(validateCorpus(data).length).toBeGreaterThan(0);
    }
    const missing = copy();
    missing.scenarios[0]?.steps.push({ at: 1, type: "capabilities", caseId: "absent" });
    expect(validateCorpus(missing).length).toBeGreaterThan(0);
  });

  it("sorts virtual time stably and does not depend on JSON key order", () => {
    const data = copy();
    const scenario = data.scenarios.find((s) => s.id === "bike-signed-split");
    if (!scenario) throw new Error("missing fixture");
    scenario.steps.reverse();
    expect(runCorpus(data).complete).toBe(true);
    const expected = firstFeed(data).expected;
    if (expected.status !== "complete") throw new Error("complete fixture required");
    expected.raw = Object.fromEntries(Object.entries(expected.raw as object).reverse());
    expect(runCorpus(data).complete).toBe(true);
  });
});
