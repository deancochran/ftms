import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { isDeepStrictEqual } from "node:util";
import { Ajv2020 } from "ajv/dist/2020.js";
import corpus from "../../../../shared/simulation/v1/scenarios.json" with { type: "json" };
import schema from "../../../../shared/simulation/v1/schema.json" with { type: "json" };
import { reference } from "./references.js";
import { type SimulationProfile, SimulationSession } from "./session.js";
import type { Corpus, Json, Report } from "./types.js";

const canonical = corpus as unknown as Corpus;
const json = (value: unknown): Json => JSON.parse(JSON.stringify(value)) as Json;
const hash = (value: string | Uint8Array): string =>
  createHash("sha256").update(value).digest("hex");
const validate = new Ajv2020({ allErrors: true, strict: true }).compile(schema);
export function validateCorpus(input: unknown = corpus): string[] {
  if (!validate(input))
    return (validate.errors ?? []).map(
      (error) => `${error.instancePath || "/"} ${error.message ?? "invalid"}`,
    );
  const data = input as Corpus,
    errors: string[] = [],
    profiles = new Set<string>(),
    scenarios = new Set<string>();
  for (const profile of data.profiles) {
    if (profiles.has(profile.id)) errors.push(`duplicate profile ${profile.id}`);
    profiles.add(profile.id);
  }
  for (const scenario of data.scenarios) {
    if (scenarios.has(scenario.id)) errors.push(`duplicate scenario ${scenario.id}`);
    scenarios.add(scenario.id);
    if (!profiles.has(scenario.profile)) errors.push(`missing profile ${scenario.profile}`);
    for (const step of scenario.steps)
      if (step.type === "control" || step.type === "response" || step.type === "capabilities") {
        try {
          reference(step.caseId, step.type, false);
        } catch (error) {
          errors.push(`scenario ${scenario.id}: ${(error as Error).message}`);
        }
      }
  }
  return errors;
}
export function runCorpus(input: unknown = canonical): Report {
  const errors = validateCorpus(input);
  const data = input && typeof input === "object" ? (input as Partial<Corpus>) : {};
  const files = [
    "shared/simulation/README.md",
    "shared/simulation/v1/schema.json",
    "shared/simulation/v1/scenarios.json",
    "shared/protocol/wire-compatibility.md",
    "shared/protocol/capability-discovery.md",
    "shared/conformance/capabilities/v1/schema.json",
    "shared/conformance/capabilities/v1/vectors.json",
    "shared/conformance/capabilities/README.md",
    "shared/conformance/controls/v1/schema.json",
    "shared/conformance/controls/v1/vectors.json",
    "shared/conformance/controls/README.md",
  ];
  const report: Report = {
    implementation: "typescript-session-harness",
    total: Array.isArray(data.scenarios) ? data.scenarios.length : 0,
    passed: 0,
    failed: 0,
    unsupported: 0,
    skipped: 0,
    steps: 0,
    passedSteps: 0,
    failedSteps: 0,
    complete: false,
    runnerErrors: errors,
    scenarios: [],
    trace: [],
    identity: {},
    inputSha256: hash(JSON.stringify(input) ?? "undefined"),
  };
  try {
    report.identity = Object.fromEntries(
      files.map((file) => [
        file,
        hash(readFileSync(new URL(`../../../../${file}`, import.meta.url))),
      ]),
    );
    const cwd = fileURLToPath(new URL("../../../../", import.meta.url));
    report.sourceCommit = execFileSync("git", ["rev-parse", "HEAD"], {
      cwd,
      encoding: "utf8",
    }).trim();
    report.dirty =
      execFileSync("git", ["status", "--porcelain"], { cwd, encoding: "utf8" }).trim().length > 0;
  } catch (error) {
    errors.push(`identity failure: ${String(error)}`);
  }
  if (errors.length) return report;
  const whole = data as Corpus,
    profiles = new Map(whole.profiles.map((profile) => [profile.id, profile as SimulationProfile]));
  for (const scenario of whole.scenarios) {
    const profile = profiles.get(scenario.profile);
    if (!profile) throw new Error(`validated profile disappeared: ${scenario.profile}`);
    const session = new SimulationSession(profile, scenario.generation);
    let connected = true,
      ok = true;
    for (const { step, index } of [...scenario.steps]
      .map((step, index) => ({ step, index }))
      .sort((a, b) => a.step.at - b.step.at || a.index - b.index)) {
      const tick = ((whole.baseTick ?? 0) + step.at) >>> 0;
      let actual: unknown;
      let expected: unknown = "expected" in step ? step.expected : undefined;
      let reason: string | undefined;
      try {
        if (step.type === "feed")
          actual = connected
            ? session.feed(step.bytes, step.generation, tick)
            : { status: "disconnected" };
        else if (step.type === "drop") actual = { status: "dropped" };
        else if (step.type === "disconnect") {
          session.reset();
          connected = false;
          actual = { status: "pending" };
        } else if (step.type === "connect" || step.type === "reconnect") {
          connected = true;
          actual = { status: session.reconnect(step.generation) };
        } else if (step.type === "reset") actual = { status: session.reset() };
        else if (
          step.type === "capabilities" ||
          step.type === "control" ||
          step.type === "response"
        ) {
          const outcome = reference(step.caseId, step.type);
          actual = (outcome as Record<string, unknown>).actual;
          expected = (outcome as Record<string, unknown>).expected;
        }
      } catch (error) {
        actual = { exception: (error as Error).message };
        reason = "exception";
      }
      const passed = reason === undefined && isDeepStrictEqual(actual, expected);
      if (!passed && !reason) reason = "actual does not equal expected";
      report.steps++;
      passed ? report.passedSteps++ : report.failedSteps++;
      if (!passed) ok = false;
      report.trace.push({
        scenario: scenario.id,
        profile: scenario.profile,
        index,
        scheduledAt: step.at,
        at: tick,
        kind: step.type,
        actual: json(actual),
        ...(expected === undefined ? {} : { expected: json(expected) }),
        outcome: passed ? "passed" : "failed",
        ...(reason ? { reason } : {}),
      });
    }
    report.scenarios.push({
      id: scenario.id,
      outcome: ok ? "passed" : "failed",
      steps: scenario.steps.length,
    });
    if (ok) report.passed++;
    else report.failed++;
  }
  report.complete =
    report.total > 0 &&
    report.total === report.passed + report.failed + report.unsupported + report.skipped &&
    report.steps === report.passedSteps + report.failedSteps &&
    report.failed === 0 &&
    report.failedSteps === 0 &&
    report.runnerErrors.length === 0;
  return report;
}
export const runSimulation = (input: unknown = canonical): Report => runCorpus(input);
