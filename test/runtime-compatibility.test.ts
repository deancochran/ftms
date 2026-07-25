import { runInNewContext } from "node:vm";
import { describe, expect, it } from "vitest";
import {
  decodeFtmsControlResponse,
  decodeFtmsFeatures,
  decodeSupportedPowerRange,
  FTMS_CHARACTERISTICS,
  parseFtmsIndoorBikeMeasurement,
  parseFtmsMachineStatus,
  parseFtmsTrainingStatus,
  parseRegisteredFtmsPayload,
} from "../src/index.js";

type BinaryInput = ArrayBuffer | Uint8Array;

interface CompatibilityCase {
  name: string;
  payload: readonly number[];
  evaluate: (input: BinaryInput) => unknown;
  expected: unknown;
}

const compatibilityCases: readonly CompatibilityCase[] = [
  {
    name: "feature decoder",
    payload: [0x02, 0, 0, 0, 0x08, 0, 0, 0],
    evaluate: (input) => {
      const result = decodeFtmsFeatures(input);
      return (
        result.ok && {
          cadenceSupported: result.value.cadenceSupported,
          powerTargetSettingSupported: result.value.powerTargetSettingSupported,
        }
      );
    },
    expected: { cadenceSupported: true, powerTargetSettingSupported: true },
  },
  {
    name: "range decoder",
    payload: [0x9c, 0xff, 0xa0, 0x0f, 0x05, 0],
    evaluate: decodeSupportedPowerRange,
    expected: {
      ok: true,
      value: { kind: "power", min: -100, max: 4000, increment: 5, unit: "watts" },
    },
  },
  {
    name: "control response decoder",
    payload: [0x80, 0x05, 0x01, 0xaa],
    evaluate: (input) => {
      const result = decodeFtmsControlResponse(input);
      return (
        result.ok && {
          requestOpCode: result.value.requestOpCode,
          success: result.value.success,
          parameters: Array.from(result.value.parameters ?? []),
        }
      );
    },
    expected: { requestOpCode: 0x05, success: true, parameters: [0xaa] },
  },
  {
    name: "measurement parser",
    payload: [0x44, 0, 0xe8, 0x03, 0xb4, 0, 0xfa, 0],
    evaluate: (input) => {
      const result = parseFtmsIndoorBikeMeasurement(input);
      return {
        speedMps: result.metrics.speedMps,
        cadenceRpm: result.metrics.cadenceRpm,
        powerWatts: result.metrics.powerWatts,
        byteLength: result.diagnostics.byteLength,
      };
    },
    expected: { speedMps: 10 / 3.6, cadenceRpm: 90, powerWatts: 250, byteLength: 8 },
  },
  {
    name: "training status parser",
    payload: [0x01, 0x0c, 0x45, 0x52, 0x47],
    evaluate: (input) => {
      const result = parseFtmsTrainingStatus(input);
      const details = result.status?.details;
      return {
        label: result.status?.label,
        trainingStatusString:
          details?.kind === "training_status" ? details.trainingStatusString : undefined,
        byteLength: result.diagnostics.byteLength,
      };
    },
    expected: { label: "watt_control", trainingStatusString: "ERG", byteLength: 5 },
  },
  {
    name: "machine status parser",
    payload: [0x08, 0xfa, 0],
    evaluate: (input) => {
      const result = parseFtmsMachineStatus(input);
      return {
        label: result.status?.label,
        details: result.status?.details,
        byteLength: result.diagnostics.byteLength,
      };
    },
    expected: {
      label: "target_power_changed",
      details: { kind: "power", powerWatts: 250 },
      byteLength: 3,
    },
  },
  {
    name: "registered parser",
    payload: [0, 0, 0xe8, 0x03],
    evaluate: (input) => {
      const result = parseRegisteredFtmsPayload(FTMS_CHARACTERISTICS.INDOOR_BIKE_DATA, input);
      return { kind: result?.kind, speedMps: result?.metrics.speedMps };
    },
    expected: { kind: "measurement", speedMps: 10 / 3.6 },
  },
];

function plainArrayBuffer(payload: readonly number[]): ArrayBuffer {
  return Uint8Array.from(payload).buffer;
}

function offsetView(payload: readonly number[]): Uint8Array {
  const storage = new Uint8Array(payload.length + 7);
  storage.fill(0xa5);
  const view = new Uint8Array(storage.buffer, 3, payload.length);
  view.set(payload);
  return view;
}

function foreignUint8Array(payload: readonly number[]): Uint8Array {
  return runInNewContext(
    `const storage = new Uint8Array(payload.length + 7);
storage.fill(0xa5);
const view = new Uint8Array(storage.buffer, 3, payload.length);
view.set(payload);
view;`,
    {
      payload: Array.from(payload),
    },
  ) as Uint8Array;
}

function foreignArrayBuffer(payload: readonly number[]): ArrayBuffer {
  return runInNewContext("Uint8Array.from(payload).buffer", {
    payload: Array.from(payload),
  }) as ArrayBuffer;
}

describe("runtime-neutral binary input contracts", () => {
  describe.each([
    { inputKind: "plain ArrayBuffer", createInput: plainArrayBuffer },
    { inputKind: "offset Uint8Array view", createInput: offsetView },
    { inputKind: "foreign-realm ArrayBuffer", createInput: foreignArrayBuffer },
    { inputKind: "foreign-realm Uint8Array", createInput: foreignUint8Array },
  ])("$inputKind", ({ createInput }) => {
    it.each(compatibilityCases)("works with the $name", ({ payload, evaluate, expected }) => {
      expect(evaluate(createInput(payload))).toEqual(expected);
    });
  });
});
