import { toBytes } from "./binary.js";
import { FTMS_OPCODES, FTMS_RESULT_CODES } from "./constants.js";
import type { FTMSResponse } from "./types.js";

export type FtmsControlRequest =
  | { op: "requestControl" }
  | { op: "reset" }
  | { op: "setTargetSpeed"; speedKph: number }
  | { op: "setTargetInclination"; inclinationPercent: number }
  | { op: "setTargetResistance"; resistanceLevel: number }
  | { op: "setTargetPower"; powerWatts: number }
  | { op: "setTargetHeartRate"; heartRateBpm: number }
  | { op: "startResume" }
  | { op: "stopPause"; action: "stop" | "pause" }
  | { op: "setTargetedExpendedEnergy"; energyKcal: number }
  | { op: "setTargetedSteps"; steps: number }
  | { op: "setTargetedStrides"; strides: number }
  | { op: "setTargetedDistance"; distanceMeters: number }
  | { op: "setTargetedTrainingTime"; seconds: number }
  | { op: "setTargetedTimeTwoHrZones"; seconds: readonly [number, number] }
  | { op: "setTargetedTimeThreeHrZones"; seconds: readonly [number, number, number] }
  | {
      op: "setTargetedTimeFiveHrZones";
      seconds: readonly [number, number, number, number, number];
    }
  | {
      op: "setIndoorBikeSimulation";
      windSpeedMps: number;
      gradePercent: number;
      crr: number;
      cwKgPerM: number;
    }
  | { op: "setWheelCircumference"; circumferenceMm: number }
  | { op: "spinDown"; action: "start" | "ignore" }
  | { op: "setTargetedCadence"; cadenceRpm: number };

export interface FtmsEncodeError {
  code: "invalid_request" | "invalid_number" | "out_of_range" | "invalid_resolution";
  field: string;
  message: string;
  value: unknown;
}

export type FtmsEncodeResult =
  | { ok: true; value: Uint8Array }
  | { ok: false; error: FtmsEncodeError };

interface NumericSuccess {
  ok: true;
  value: number;
}

type NumericResult = NumericSuccess | { ok: false; error: FtmsEncodeError };

function encodeError(
  code: FtmsEncodeError["code"],
  field: string,
  message: string,
  value: unknown,
): { ok: false; error: FtmsEncodeError } {
  return { ok: false, error: { code, field, message, value } };
}

function encodeNumber(
  value: unknown,
  field: string,
  minimumRaw: number,
  maximumRaw: number,
  resolution = 1,
): NumericResult {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return encodeError("invalid_number", field, "Value must be a finite number", value);
  }

  const raw = Math.round(value / resolution);
  if (Math.abs(raw * resolution - value) > 1e-9) {
    return encodeError(
      "invalid_resolution",
      field,
      `Value must align to a resolution of ${resolution}`,
      value,
    );
  }

  if (!Number.isInteger(raw) || raw < minimumRaw || raw > maximumRaw) {
    return encodeError(
      "out_of_range",
      field,
      `Encoded value must be between ${minimumRaw} and ${maximumRaw}`,
      value,
    );
  }

  return { ok: true, value: raw };
}

function encodeUint16(opcode: number, value: number): FtmsEncodeResult {
  const bytes = new Uint8Array(3);
  bytes[0] = opcode;
  new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength).setUint16(1, value, true);
  return { ok: true, value: bytes };
}

function encodeInt16(opcode: number, value: number): FtmsEncodeResult {
  const bytes = new Uint8Array(3);
  bytes[0] = opcode;
  new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength).setInt16(1, value, true);
  return { ok: true, value: bytes };
}

function encodeUint16Request(
  opcode: number,
  value: unknown,
  field: string,
  minimumRaw = 0,
  maximumRaw = 0xffff,
  resolution = 1,
): FtmsEncodeResult {
  const encoded = encodeNumber(value, field, minimumRaw, maximumRaw, resolution);
  return encoded.ok ? encodeUint16(opcode, encoded.value) : encoded;
}

function encodeInt16Request(
  opcode: number,
  value: unknown,
  field: string,
  resolution = 1,
): FtmsEncodeResult {
  const encoded = encodeNumber(value, field, -0x8000, 0x7fff, resolution);
  return encoded.ok ? encodeInt16(opcode, encoded.value) : encoded;
}

function encodeHrZones(opcode: number, value: unknown, expectedCount: number): FtmsEncodeResult {
  if (!Array.isArray(value) || value.length !== expectedCount) {
    return encodeError(
      "invalid_request",
      "seconds",
      `Expected exactly ${expectedCount} heart-rate zone durations`,
      value,
    );
  }

  const encodedDurations: number[] = [];
  for (let index = 0; index < value.length; index += 1) {
    const encoded = encodeNumber(value[index], `seconds[${index}]`, 0, 0xffff);
    if (!encoded.ok) {
      return encoded;
    }
    encodedDurations.push(encoded.value);
  }

  const bytes = new Uint8Array(1 + expectedCount * 2);
  bytes[0] = opcode;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  for (let index = 0; index < encodedDurations.length; index += 1) {
    const duration = encodedDurations[index];
    if (duration !== undefined) {
      view.setUint16(1 + index * 2, duration, true);
    }
  }
  return { ok: true, value: bytes };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function encodeUnknownControlRequest(request: unknown): FtmsEncodeResult {
  if (!isRecord(request) || typeof request.op !== "string") {
    return encodeError("invalid_request", "op", "Expected an FTMS control request", request);
  }

  switch (request.op) {
    case "requestControl":
      return { ok: true, value: Uint8Array.of(FTMS_OPCODES.REQUEST_CONTROL) };
    case "reset":
      return { ok: true, value: Uint8Array.of(FTMS_OPCODES.RESET) };
    case "setTargetSpeed":
      return encodeUint16Request(
        FTMS_OPCODES.SET_TARGET_SPEED,
        request.speedKph,
        "speedKph",
        0,
        0xffff,
        0.01,
      );
    case "setTargetInclination":
      return encodeInt16Request(
        FTMS_OPCODES.SET_TARGET_INCLINATION,
        request.inclinationPercent,
        "inclinationPercent",
        0.1,
      );
    case "setTargetResistance":
      return encodeInt16Request(
        FTMS_OPCODES.SET_TARGET_RESISTANCE,
        request.resistanceLevel,
        "resistanceLevel",
        0.1,
      );
    case "setTargetPower":
      return encodeInt16Request(FTMS_OPCODES.SET_TARGET_POWER, request.powerWatts, "powerWatts");
    case "setTargetHeartRate": {
      const encoded = encodeNumber(request.heartRateBpm, "heartRateBpm", 0, 0xff);
      return encoded.ok
        ? { ok: true, value: Uint8Array.of(FTMS_OPCODES.SET_TARGET_HEART_RATE, encoded.value) }
        : encoded;
    }
    case "startResume":
      return { ok: true, value: Uint8Array.of(FTMS_OPCODES.START_RESUME) };
    case "stopPause":
      if (request.action !== "stop" && request.action !== "pause") {
        return encodeError(
          "invalid_request",
          "action",
          "Action must be stop or pause",
          request.action,
        );
      }
      return {
        ok: true,
        value: Uint8Array.of(FTMS_OPCODES.STOP_PAUSE, request.action === "stop" ? 0x01 : 0x02),
      };
    case "setTargetedExpendedEnergy":
      return encodeUint16Request(
        FTMS_OPCODES.SET_TARGETED_EXPENDED_ENERGY,
        request.energyKcal,
        "energyKcal",
      );
    case "setTargetedSteps":
      return encodeUint16Request(FTMS_OPCODES.SET_TARGETED_STEPS, request.steps, "steps");
    case "setTargetedStrides":
      return encodeUint16Request(FTMS_OPCODES.SET_TARGETED_STRIDES, request.strides, "strides");
    case "setTargetedDistance": {
      const encoded = encodeNumber(request.distanceMeters, "distanceMeters", 0, 0xffffff);
      if (!encoded.ok) {
        return encoded;
      }
      return {
        ok: true,
        value: Uint8Array.of(
          FTMS_OPCODES.SET_TARGETED_DISTANCE,
          encoded.value & 0xff,
          (encoded.value >>> 8) & 0xff,
          (encoded.value >>> 16) & 0xff,
        ),
      };
    }
    case "setTargetedTrainingTime":
      return encodeUint16Request(
        FTMS_OPCODES.SET_TARGETED_TRAINING_TIME,
        request.seconds,
        "seconds",
      );
    // biome-ignore lint/security/noSecrets: FTMS operation identifier from the Bluetooth specification.
    case "setTargetedTimeTwoHrZones":
      return encodeHrZones(FTMS_OPCODES.SET_TARGETED_TIME_TWO_HR_ZONES, request.seconds, 2);
    case "setTargetedTimeThreeHrZones":
      return encodeHrZones(FTMS_OPCODES.SET_TARGETED_TIME_THREE_HR_ZONES, request.seconds, 3);
    // biome-ignore lint/security/noSecrets: FTMS operation identifier from the Bluetooth specification.
    case "setTargetedTimeFiveHrZones":
      return encodeHrZones(FTMS_OPCODES.SET_TARGETED_TIME_FIVE_HR_ZONES, request.seconds, 5);
    case "setIndoorBikeSimulation": {
      const wind = encodeNumber(request.windSpeedMps, "windSpeedMps", -0x8000, 0x7fff, 0.001);
      if (!wind.ok) return wind;
      const grade = encodeNumber(request.gradePercent, "gradePercent", -0x8000, 0x7fff, 0.01);
      if (!grade.ok) return grade;
      const crr = encodeNumber(request.crr, "crr", 0, 0xff, 0.0001);
      if (!crr.ok) return crr;
      const windResistance = encodeNumber(request.cwKgPerM, "cwKgPerM", 0, 0xff, 0.01);
      if (!windResistance.ok) return windResistance;

      const bytes = new Uint8Array(7);
      bytes[0] = FTMS_OPCODES.SET_INDOOR_BIKE_SIMULATION;
      const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
      view.setInt16(1, wind.value, true);
      view.setInt16(3, grade.value, true);
      bytes[5] = crr.value;
      bytes[6] = windResistance.value;
      return { ok: true, value: bytes };
    }
    case "setWheelCircumference":
      return encodeUint16Request(
        FTMS_OPCODES.SET_WHEEL_CIRCUMFERENCE,
        request.circumferenceMm,
        "circumferenceMm",
        0,
        0xffff,
        0.1,
      );
    case "spinDown":
      if (request.action !== "start" && request.action !== "ignore") {
        return encodeError(
          "invalid_request",
          "action",
          "Action must be start or ignore",
          request.action,
        );
      }
      return {
        ok: true,
        value: Uint8Array.of(
          FTMS_OPCODES.SPIN_DOWN_CONTROL,
          request.action === "start" ? 0x01 : 0x02,
        ),
      };
    case "setTargetedCadence":
      return encodeUint16Request(
        FTMS_OPCODES.SET_TARGETED_CADENCE,
        request.cadenceRpm,
        "cadenceRpm",
        0,
        0xffff,
        0.5,
      );
    default:
      return encodeError("invalid_request", "op", "Unknown FTMS control operation", request.op);
  }
}

export function tryEncodeFtmsControlRequest(request: unknown): FtmsEncodeResult {
  return encodeUnknownControlRequest(request);
}

export function encodeFtmsControlRequest(request: FtmsControlRequest): Uint8Array {
  const result = tryEncodeFtmsControlRequest(request);
  if (result.ok) {
    return result.value;
  }
  throw new RangeError(`${result.error.field}: ${result.error.message}`);
}

export interface FtmsResponseDecodeError {
  code: "malformed_response";
  offset: number;
  expected: number;
  actual: number;
  message: string;
}

export type FtmsResponseDecodeResult =
  | { ok: true; value: FTMSResponse }
  | { ok: false; error: FtmsResponseDecodeError };

export interface FtmsControlResponseContext {
  spinDownAction?: "start" | "ignore";
}

export function getFtmsResultCodeName(resultCode: number): string {
  switch (resultCode) {
    case FTMS_RESULT_CODES.SUCCESS:
      return "success";
    case FTMS_RESULT_CODES.NOT_SUPPORTED:
      return "not_supported";
    case FTMS_RESULT_CODES.INVALID_PARAMETER:
      return "invalid_parameter";
    case FTMS_RESULT_CODES.OPERATION_FAILED:
      return "operation_failed";
    case FTMS_RESULT_CODES.CONTROL_NOT_PERMITTED:
      return "control_not_permitted";
    default:
      return `unknown_0x${resultCode.toString(16).padStart(2, "0")}`;
  }
}

export function decodeFtmsControlResponse(
  data: ArrayBuffer | Uint8Array,
  context: FtmsControlResponseContext = {},
): FtmsResponseDecodeResult {
  const bytes = toBytes(data);
  if (bytes.byteLength < 3) {
    return {
      ok: false,
      error: {
        code: "malformed_response",
        offset: bytes.byteLength,
        expected: 3,
        actual: bytes.byteLength,
        message: "FTMS Control Point response requires at least three bytes",
      },
    };
  }

  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const responseOpcode = view.getUint8(0);
  if (responseOpcode !== FTMS_OPCODES.RESPONSE_CODE) {
    return {
      ok: false,
      error: {
        code: "malformed_response",
        offset: 0,
        expected: FTMS_OPCODES.RESPONSE_CODE,
        actual: responseOpcode,
        message: "Payload is not an FTMS Control Point response",
      },
    };
  }

  const requestOpCode = view.getUint8(1);
  if (requestOpCode > FTMS_OPCODES.SET_TARGETED_CADENCE) {
    return {
      ok: false,
      error: {
        code: "malformed_response",
        offset: 1,
        expected: FTMS_OPCODES.SET_TARGETED_CADENCE,
        actual: requestOpCode,
        message: "FTMS Control Point response references a reserved request opcode",
      },
    };
  }

  const resultCode = view.getUint8(2);
  const success = resultCode === FTMS_RESULT_CODES.SUCCESS;
  const issues: FTMSResponse["issues"] =
    resultCode === 0 || resultCode > FTMS_RESULT_CODES.CONTROL_NOT_PERMITTED
      ? [{ code: "reserved_value", field: "resultCode", offset: 2, actual: resultCode }]
      : [];

  if (!success || requestOpCode !== FTMS_OPCODES.SPIN_DOWN_CONTROL) {
    if (bytes.byteLength !== 3) {
      return {
        ok: false,
        error: {
          code: "malformed_response",
          offset: 3,
          expected: 3,
          actual: bytes.byteLength,
          message: "This FTMS Control Point response must not contain response parameters",
        },
      };
    }

    return {
      ok: true,
      value: {
        requestOpCode,
        resultCode,
        resultCodeName: getFtmsResultCodeName(resultCode),
        success,
        parameter: { kind: "none" },
        issues,
      },
    };
  }

  const expectedLength = context.spinDownAction === "start" ? 7 : 3;
  const validLength =
    context.spinDownAction === undefined
      ? bytes.byteLength === 3 || bytes.byteLength === 7
      : bytes.byteLength === expectedLength;
  if (!validLength) {
    return {
      ok: false,
      error: {
        code: "malformed_response",
        offset: 3,
        expected: context.spinDownAction === undefined ? 7 : expectedLength,
        actual: bytes.byteLength,
        message:
          context.spinDownAction === undefined
            ? "A successful Spin Down response must contain either zero or four parameter bytes"
            : `A successful Spin Down ${context.spinDownAction} response has an invalid length`,
      },
    };
  }

  const parameter: FTMSResponse["parameter"] =
    bytes.byteLength === 7
      ? {
          kind: "spin_down_speeds",
          targetSpeedLowKph: view.getUint16(3, true) / 100,
          targetSpeedHighKph: view.getUint16(5, true) / 100,
        }
      : { kind: "none" };
  return {
    ok: true,
    value: {
      requestOpCode,
      resultCode,
      resultCodeName: getFtmsResultCodeName(resultCode),
      success,
      parameter,
      issues,
    },
  };
}
