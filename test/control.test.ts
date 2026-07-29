import { describe, expect, it } from "vitest";
import {
  decodeFtmsControlResponse,
  encodeFtmsControlRequest,
  type FtmsControlRequest,
  tryEncodeFtmsControlRequest,
} from "../src/index.js";

interface ControlVector {
  name: string;
  request: FtmsControlRequest;
  expected: number[];
}

const controlVectors: readonly ControlVector[] = [
  { name: "request control", request: { op: "requestControl" }, expected: [0x00] },
  { name: "reset", request: { op: "reset" }, expected: [0x01] },
  {
    name: "target speed",
    request: { op: "setTargetSpeed", speedKph: 12.34 },
    expected: [0x02, 0xd2, 0x04],
  },
  {
    name: "target inclination",
    request: { op: "setTargetInclination", inclinationPercent: -1.2 },
    expected: [0x03, 0xf4, 0xff],
  },
  {
    name: "target resistance",
    request: { op: "setTargetResistance", resistanceLevel: -1.2 },
    expected: [0x04, 0xf4, 0xff],
  },
  {
    name: "target power",
    request: { op: "setTargetPower", powerWatts: -100 },
    expected: [0x05, 0x9c, 0xff],
  },
  {
    name: "target heart rate",
    request: { op: "setTargetHeartRate", heartRateBpm: 150 },
    expected: [0x06, 150],
  },
  { name: "start or resume", request: { op: "startResume" }, expected: [0x07] },
  {
    name: "stop",
    request: { op: "stopPause", action: "stop" },
    expected: [0x08, 0x01],
  },
  {
    name: "target energy",
    request: { op: "setTargetedExpendedEnergy", energyKcal: 500 },
    expected: [0x09, 0xf4, 0x01],
  },
  {
    name: "target steps",
    request: { op: "setTargetedSteps", steps: 600 },
    expected: [0x0a, 0x58, 0x02],
  },
  {
    name: "target strides",
    request: { op: "setTargetedStrides", strides: 700 },
    expected: [0x0b, 0xbc, 0x02],
  },
  {
    name: "target distance",
    request: { op: "setTargetedDistance", distanceMeters: 0x010203 },
    expected: [0x0c, 0x03, 0x02, 0x01],
  },
  {
    name: "target training time",
    request: { op: "setTargetedTrainingTime", seconds: 3600 },
    expected: [0x0d, 0x10, 0x0e],
  },
  {
    name: "two heart-rate zones",
    request: { op: "setTargetedTimeTwoHrZones", seconds: [10, 20] },
    expected: [0x0e, 10, 0, 20, 0],
  },
  {
    name: "three heart-rate zones",
    request: { op: "setTargetedTimeThreeHrZones", seconds: [10, 20, 30] },
    expected: [0x0f, 10, 0, 20, 0, 30, 0],
  },
  {
    name: "five heart-rate zones",
    request: { op: "setTargetedTimeFiveHrZones", seconds: [10, 20, 30, 40, 50] },
    expected: [0x10, 10, 0, 20, 0, 30, 0, 40, 0, 50, 0],
  },
  {
    name: "indoor-bike simulation",
    request: {
      op: "setIndoorBikeSimulation",
      windSpeedMps: 1,
      gradePercent: 2.5,
      crr: 0.001,
      cwKgPerM: 0.2,
    },
    expected: [0x11, 0xe8, 0x03, 0xfa, 0x00, 10, 20],
  },
  {
    name: "wheel circumference",
    request: { op: "setWheelCircumference", circumferenceMm: 2100 },
    expected: [0x12, 0x08, 0x52],
  },
  {
    name: "spin-down ignore",
    request: { op: "spinDown", action: "ignore" },
    expected: [0x13, 0x02],
  },
  {
    name: "target cadence",
    request: { op: "setTargetedCadence", cadenceRpm: 90 },
    expected: [0x14, 180, 0],
  },
];

describe("FTMS Control Point request encoding", () => {
  it.each(controlVectors)("encodes $name with exact bytes", ({ request, expected }) => {
    expect(Array.from(encodeFtmsControlRequest(request))).toEqual(expected);
  });

  it("encodes pause distinctly from stop", () => {
    expect(Array.from(encodeFtmsControlRequest({ op: "stopPause", action: "pause" }))).toEqual([
      0x08, 0x02,
    ]);
  });

  it("encodes spin-down start distinctly from ignore", () => {
    expect(Array.from(encodeFtmsControlRequest({ op: "spinDown", action: "start" }))).toEqual([
      0x13, 0x01,
    ]);
  });

  it.each([
    { name: "a null request", request: null, code: "invalid_request" },
    { name: "an unknown operation", request: { op: "unknown" }, code: "invalid_request" },
    {
      name: "non-finite speed",
      request: { op: "setTargetSpeed", speedKph: Number.POSITIVE_INFINITY },
      code: "invalid_number",
    },
    {
      name: "misaligned speed",
      request: { op: "setTargetSpeed", speedKph: 1.001 },
      code: "invalid_resolution",
    },
    {
      name: "speed overflow",
      request: { op: "setTargetSpeed", speedKph: 655.36 },
      code: "out_of_range",
    },
    {
      name: "misaligned inclination",
      request: { op: "setTargetInclination", inclinationPercent: 0.05 },
      code: "invalid_resolution",
    },
    {
      name: "non-finite resistance",
      request: { op: "setTargetResistance", resistanceLevel: Number.NaN },
      code: "invalid_number",
    },
    {
      name: "power overflow",
      request: { op: "setTargetPower", powerWatts: 32768 },
      code: "out_of_range",
    },
    {
      name: "fractional power",
      request: { op: "setTargetPower", powerWatts: 100.5 },
      code: "invalid_resolution",
    },
    {
      name: "heart-rate overflow",
      request: { op: "setTargetHeartRate", heartRateBpm: 256 },
      code: "out_of_range",
    },
    {
      name: "invalid stop action",
      request: { op: "stopPause", action: "wait" },
      code: "invalid_request",
    },
    {
      name: "fractional distance",
      request: { op: "setTargetedDistance", distanceMeters: 1.5 },
      code: "invalid_resolution",
    },
    {
      name: "distance overflow",
      request: { op: "setTargetedDistance", distanceMeters: 0x1000000 },
      code: "out_of_range",
    },
    {
      name: "wrong two-zone count",
      request: { op: "setTargetedTimeTwoHrZones", seconds: [1] },
      code: "invalid_request",
    },
    {
      name: "invalid zone duration",
      request: { op: "setTargetedTimeThreeHrZones", seconds: [1, -1, 3] },
      code: "out_of_range",
    },
    {
      name: "misaligned wind speed",
      request: {
        op: "setIndoorBikeSimulation",
        windSpeedMps: 0.0005,
        gradePercent: 0,
        crr: 0,
        cwKgPerM: 0,
      },
      code: "invalid_resolution",
    },
    {
      name: "rolling resistance overflow",
      request: {
        op: "setIndoorBikeSimulation",
        windSpeedMps: 0,
        gradePercent: 0,
        crr: 0.0256,
        cwKgPerM: 0,
      },
      code: "out_of_range",
    },
    {
      name: "misaligned circumference",
      request: { op: "setWheelCircumference", circumferenceMm: 1.05 },
      code: "invalid_resolution",
    },
    {
      name: "invalid spin-down action",
      request: { op: "spinDown", action: "cancel" },
      code: "invalid_request",
    },
    {
      name: "misaligned cadence",
      request: { op: "setTargetedCadence", cadenceRpm: 90.25 },
      code: "invalid_resolution",
    },
  ])("rejects $name", ({ request, code }) => {
    expect(tryEncodeFtmsControlRequest(request)).toMatchObject({ ok: false, error: { code } });
  });

  it("throws from the convenience encoder when validation fails", () => {
    expect(() =>
      encodeFtmsControlRequest({ op: "setTargetPower", powerWatts: Number.NaN }),
    ).toThrow(RangeError);
  });
});

describe("FTMS Control Point response decoding", () => {
  it.each([
    { code: 0x00, name: "unknown_0x00", success: false, reserved: true },
    { code: 0x01, name: "success", success: true, reserved: false },
    { code: 0x02, name: "not_supported", success: false, reserved: false },
    { code: 0x03, name: "invalid_parameter", success: false, reserved: false },
    { code: 0x04, name: "operation_failed", success: false, reserved: false },
    { code: 0x05, name: "control_not_permitted", success: false, reserved: false },
    { code: 0x06, name: "unknown_0x06", success: false, reserved: true },
    { code: 0xff, name: "unknown_0xff", success: false, reserved: true },
  ])("decodes result code 0x$code", ({ code, name, success, reserved }) => {
    const result = decodeFtmsControlResponse(Uint8Array.of(0x80, 0x05, code));
    expect(result).toMatchObject({
      ok: true,
      value: {
        requestOpCode: 0x05,
        resultCode: code,
        resultCodeName: name,
        success,
        parameter: { kind: "none" },
      },
    });
    if (result.ok) {
      expect(result.value.issues.map(({ code: issueCode }) => issueCode)).toEqual(
        reserved ? ["reserved_value"] : [],
      );
    }
  });

  it("decodes successful Spin Down target speeds", () => {
    expect(
      decodeFtmsControlResponse(Uint8Array.of(0x80, 0x13, 0x01, 0xe8, 0x03, 0x88, 0x13), {
        spinDownAction: "start",
      }),
    ).toEqual({
      ok: true,
      value: {
        requestOpCode: 0x13,
        resultCode: 0x01,
        resultCodeName: "success",
        success: true,
        parameter: {
          kind: "spin_down_speeds",
          targetSpeedLowKph: 10,
          targetSpeedHighKph: 50,
        },
        issues: [],
      },
    });
  });

  it("decodes a successful ignored Spin Down without parameters", () => {
    expect(
      decodeFtmsControlResponse(Uint8Array.of(0x80, 0x13, 0x01), {
        spinDownAction: "ignore",
      }),
    ).toMatchObject({
      ok: true,
      value: { parameter: { kind: "none" } },
    });
  });

  it("accepts every assigned request opcode and rejects every reserved value", () => {
    for (let requestOpCode = 0x00; requestOpCode <= 0x14; requestOpCode += 1) {
      expect(decodeFtmsControlResponse(Uint8Array.of(0x80, requestOpCode, 0x01))).toMatchObject({
        ok: true,
        value: { requestOpCode },
      });
    }
    for (let requestOpCode = 0x15; requestOpCode <= 0xff; requestOpCode += 1) {
      expect(decodeFtmsControlResponse(Uint8Array.of(0x80, requestOpCode, 0x01))).toMatchObject({
        ok: false,
        error: { code: "malformed_response", offset: 1, actual: requestOpCode },
      });
    }
  });

  it.each([
    { name: "ordinary success with parameters", bytes: [0x80, 0x05, 0x01, 0xaa] },
    { name: "error with parameters", bytes: [0x80, 0x05, 0x03, 0xaa] },
    { name: "short Spin Down parameters", bytes: [0x80, 0x13, 0x01, 0x02, 0x03] },
    {
      name: "long Spin Down parameters",
      bytes: [0x80, 0x13, 0x01, 0xe8, 0x03, 0x88, 0x13, 0],
    },
  ])("rejects $name", ({ bytes }) => {
    expect(decodeFtmsControlResponse(Uint8Array.from(bytes))).toMatchObject({
      ok: false,
      error: { code: "malformed_response" },
    });
  });

  it("uses request context to distinguish Spin Down Start from Ignore", () => {
    expect(
      decodeFtmsControlResponse(Uint8Array.of(0x80, 0x13, 0x01), {
        spinDownAction: "start",
      }),
    ).toMatchObject({ ok: false, error: { code: "malformed_response", expected: 7 } });
    expect(
      decodeFtmsControlResponse(Uint8Array.of(0x80, 0x13, 0x01, 0xe8, 0x03, 0x88, 0x13), {
        spinDownAction: "ignore",
      }),
    ).toMatchObject({ ok: false, error: { code: "malformed_response", expected: 3 } });
  });

  it.each([
    { bytes: [] },
    { bytes: [0x80] },
    { bytes: [0x80, 0x05] },
  ])("rejects a short response $bytes", ({ bytes }) => {
    expect(decodeFtmsControlResponse(Uint8Array.from(bytes))).toMatchObject({
      ok: false,
      error: { code: "malformed_response" },
    });
  });

  it("rejects a non-response opcode", () => {
    expect(decodeFtmsControlResponse(Uint8Array.of(0x81, 0x05, 0x01))).toMatchObject({
      ok: false,
      error: { code: "malformed_response", offset: 0, actual: 0x81 },
    });
  });
});
