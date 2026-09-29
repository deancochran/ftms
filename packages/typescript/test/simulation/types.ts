export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };
export type Status =
  | "pending"
  | "complete"
  | "invalid"
  | "expired"
  | "generation"
  | "dropped"
  | "disconnected";
export type Expected = { status: Exclude<Status, "complete"> } | { status: "complete"; raw: Json };
export type Feed = {
  at: number;
  type: "feed";
  generation: number;
  bytes: number[];
  expected: Expected;
};
export type Lifecycle = {
  at: number;
  type: "reset" | "disconnect";
  expected: { status: "pending" };
};
export type Connect = {
  at: number;
  type: "connect" | "reconnect";
  generation: number;
  expected: { status: "pending" };
};
export type Drop = { at: number; type: "drop"; bytes: number[]; expected: { status: "dropped" } };
export type Reference = {
  at: number;
  type: "capabilities" | "control" | "response";
  caseId: string;
};
export type Step = Feed | Lifecycle | Connect | Drop | Reference;
export type Profile = {
  id: string;
  kind: number;
  origin: "synthetic-contract-ref";
  maxAge: number;
  format: { resistance: 0 | 1; pace: 0 | 1 };
};
export type Scenario = { id: string; profile: string; generation: number; steps: Step[] };
export type Corpus = {
  schemaVersion: 1;
  baseTick?: number;
  profiles: Profile[];
  scenarios: Scenario[];
};
export type Trace = {
  scenario: string;
  profile: string;
  kind: Step["type"];
  index: number;
  scheduledAt: number;
  at: number;
  actual: Json;
  expected?: Json;
  outcome: "passed" | "failed";
  reason?: string;
};
export type Report = {
  implementation: "typescript-session-harness";
  total: number;
  passed: number;
  failed: number;
  unsupported: number;
  skipped: number;
  steps: number;
  passedSteps: number;
  failedSteps: number;
  complete: boolean;
  runnerErrors: string[];
  scenarios: { id: string; outcome: "passed" | "failed"; steps: number }[];
  trace: Trace[];
  identity: Record<string, string>;
  inputSha256: string;
  sourceCommit?: string;
  dirty?: boolean;
};
