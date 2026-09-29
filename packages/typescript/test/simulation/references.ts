import { Ajv2020 } from "ajv/dist/2020.js";
import capabilitySchema from "../../../../shared/conformance/capabilities/v1/schema.json" with {
  type: "json",
};
import capabilities from "../../../../shared/conformance/capabilities/v1/vectors.json" with {
  type: "json",
};
import controlSchema from "../../../../shared/conformance/controls/v1/schema.json" with {
  type: "json",
};
import controls from "../../../../shared/conformance/controls/v1/vectors.json" with {
  type: "json",
};
import {
  decodeFtmsControlRequestRaw,
  decodeFtmsControlResponseRaw,
  encodeFtmsControlRequestRaw,
  encodeFtmsControlResponseRaw,
} from "../../src/control.js";
import { evaluateFtmsCapabilities } from "../../src/features.js";
import type { Json } from "./types.js";

type Expansion = {
  template: string;
  edits: {
    path: (string | number | "*" | number[])[];
    op?: "replace" | "append" | "remove";
    value?: Json;
  }[];
};
const clone = <T>(value: T): T => structuredClone(value);
const capabilityAjv = new Ajv2020({ strict: false });
const capabilityCorpusValid = capabilityAjv.compile(capabilitySchema);
const controlCorpusValid = new Ajv2020({ strict: true }).compile(controlSchema);
const snapshotValid = capabilityAjv.compile({
  $ref: "urn:ftms:capabilities:conformance:v1#/$defs/snapshot",
});
const reportValid = capabilityAjv.compile({
  $ref: "urn:ftms:capabilities:conformance:v1#/$defs/report",
});

function edit(
  root: Json,
  path: Expansion["edits"][number]["path"],
  op: string,
  value: Json | undefined,
): void {
  const walk = (node: Json, position: number): void => {
    const segment = path[position];
    if (segment === undefined) throw new Error("empty edit path");
    const apply = (parent: Json, key: string | number): void => {
      if (position === path.length - 1) {
        if (op === "remove") {
          if (Array.isArray(parent) && typeof key === "number") parent.splice(key, 1);
          else if (!Array.isArray(parent) && parent) delete (parent as Record<string, Json>)[key];
          else throw new Error("invalid remove");
        } else if (op === "append") {
          const target = (parent as Record<string | number, Json>)[key];
          if (!Array.isArray(target)) throw new Error("append target");
          target.push(clone(value as Json));
        } else (parent as Record<string | number, Json>)[key] = clone(value as Json);
        return;
      }
      const child = (parent as Record<string | number, Json>)[key];
      if (child === undefined) throw new Error("missing edit path");
      walk(child, position + 1);
    };
    if (segment === "*" || Array.isArray(segment)) {
      if (!Array.isArray(node)) throw new Error("array selection target");
      for (const key of segment === "*" ? node.map((_, index) => index) : segment) {
        if (key < 0 || key >= node.length) throw new Error("selection index");
        apply(node, key);
      }
    } else {
      if (Array.isArray(node) && typeof segment !== "number") throw new Error("array key");
      if (
        !Array.isArray(node) &&
        (!node || typeof node !== "object" || typeof segment !== "string")
      )
        throw new Error("object key");
      apply(node, segment);
    }
  };
  walk(root, 0);
}
function expand(templates: Record<string, Json>, expansion: Expansion): Json {
  const result = clone(templates[expansion.template]);
  if (result === undefined) throw new Error(`unknown template ${expansion.template}`);
  for (const entry of expansion.edits) edit(result, entry.path, entry.op ?? "replace", entry.value);
  return result;
}
function snapshot(value: Json): Parameters<typeof evaluateFtmsCapabilities>[0] {
  const input = value as {
    c7?: { bondingSupported: 0 | 1 | 2; featureMayChangeOverLifetime: 0 | 1 | 2 };
    characteristics: { bytes: string }[];
  };
  const { c7, ...rest } = input;
  return {
    ...rest,
    ...(c7 === undefined
      ? {}
      : {
          c7: {
            ...(c7.bondingSupported === 0 ? {} : { bondingSupported: c7.bondingSupported === 2 }),
            ...(c7.featureMayChangeOverLifetime === 0
              ? {}
              : { featureMayChangeOverLifetime: c7.featureMayChangeOverLifetime === 2 }),
          },
        }),
    characteristics: input.characteristics.map((item) => ({
      ...item,
      bytes: Uint8Array.from(
        item.bytes.match(/../g)?.map((byte) => Number.parseInt(byte, 16)) ?? [],
      ),
    })),
  } as unknown as Parameters<typeof evaluateFtmsCapabilities>[0];
}
export function reference(
  caseId: string,
  kind: "capabilities" | "control" | "response",
  execute = true,
): Json {
  if (!capabilityCorpusValid(capabilities) || !controlCorpusValid(controls))
    throw new Error("invalid referenced canonical corpus");
  for (const ids of [
    capabilities.cases.map((c) => c.id),
    [...controls.requests, ...controls.responses, ...controls.invalid].map((c) => c.id),
  ])
    if (new Set(ids).size !== ids.length) throw new Error("duplicate canonical case ID");
  if (kind === "capabilities") {
    const entry = capabilities.cases.find((item) => item.id === caseId);
    if (!entry) throw new Error(`missing capabilities case ${caseId}`);
    const input = expand(capabilities.snapshots as Record<string, Json>, entry.input as Expansion);
    const expected = expand(
      capabilities.reports as Record<string, Json>,
      entry.expected as Expansion,
    );
    if (!snapshotValid(input) || !reportValid(expected))
      throw new Error("invalid canonical capability expansion");
    return {
      actual: execute ? (evaluateFtmsCapabilities(snapshot(input)) as unknown as Json) : null,
      expected,
    };
  }
  if (kind === "control") {
    const entry = controls.requests.find((item) => item.id === caseId);
    if (!entry) throw new Error(`missing control case ${caseId}`);
    if (!execute)
      return {
        actual: null,
        expected: { decoded: entry.decoded, encoded: entry.bytes },
      } as unknown as Json;
    const options =
      entry.format === "signed16Tenths" || entry.format === "uint8Tenths"
        ? ({ resistanceFormat: entry.format } as const)
        : undefined;
    const decoded = decodeFtmsControlRequestRaw(Uint8Array.from(entry.bytes), options);
    return {
      actual: { decoded, encoded: Array.from(encodeFtmsControlRequestRaw(entry.decoded, options)) },
      expected: { decoded: entry.decoded, encoded: entry.bytes },
    } as unknown as Json;
  }
  const entry = controls.responses.find((item) => item.id === caseId) as
    | { id: string; bytes: number[]; decoded: Json; encode?: false }
    | undefined;
  if (!entry) throw new Error(`missing response case ${caseId}`);
  if (!execute) return { actual: null, expected: entry.decoded };
  const decoded = decodeFtmsControlResponseRaw(Uint8Array.from(entry.bytes));
  return {
    actual:
      entry.encode === false
        ? { decoded }
        : {
            decoded,
            encoded: Array.from(
              encodeFtmsControlResponseRaw(
                entry.decoded as unknown as Parameters<typeof encodeFtmsControlResponseRaw>[0],
              ),
            ),
          },
    expected:
      entry.encode === false
        ? { decoded: entry.decoded }
        : { decoded: entry.decoded, encoded: entry.bytes },
  } as unknown as Json;
}
