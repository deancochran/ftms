import { isByteSource, toBytes } from "./binary.js";
import { FTMS_OPCODES, FTMS_RESULT_CODES } from "./constants.js";
import {
  type FTMSResponse,
  type FtmsControlFormatOptions,
  type FtmsControlRequestRaw,
  type FtmsControlResponseRaw,
  RawCodecError,
} from "./types.js";

function rawBytes(data: ArrayBuffer | Uint8Array): Uint8Array {
  if (!isByteSource(data))
    throw new RawCodecError("null", "Raw codec input must be an ArrayBuffer or Uint8Array");
  return toBytes(data);
}

function rawInteger(value: unknown, field: string, minimum: number, maximum: number): number {
  if (
    typeof value !== "number" ||
    !Number.isFinite(value) ||
    !Number.isInteger(value) ||
    value < minimum ||
    value > maximum
  ) {
    throw new RawCodecError(
      "range",
      `${field} must be an integer between ${minimum} and ${maximum}`,
    );
  }
  return value;
}

const rawRequestLengths = [1, 1, 3, 3, 3, 3, 2, 1, 2, 3, 3, 3, 4, 3, 5, 7, 11, 7, 3, 2, 3] as const;
const rawOperandCounts = [0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 2, 3, 5, 4, 1, 1, 1] as const;

function validateControlFormatOptions(options?: FtmsControlFormatOptions): void {
  if (
    options !== undefined &&
    (options === null ||
      typeof options !== "object" ||
      Array.isArray(options) ||
      Object.keys(options).some((key) => key !== "resistanceFormat"))
  )
    throw new RawCodecError("kind", "Control format options must be an options object");
  if (
    options?.resistanceFormat !== undefined &&
    !["signed16Tenths", "uint8Tenths"].includes(options.resistanceFormat)
  )
    throw new RawCodecError("kind", "Unsupported Control Point resistance format");
}

function controlRequestLength(
  opcode: number,
  options?: FtmsControlFormatOptions,
): number | undefined {
  return opcode === 4 && options?.resistanceFormat === "uint8Tenths"
    ? 2
    : rawRequestLengths[opcode];
}

/** Decode an exact-length Control Point request to raw opcode and operands. */
export function decodeFtmsControlRequestRaw(
  data: ArrayBuffer | Uint8Array,
  options?: FtmsControlFormatOptions,
): FtmsControlRequestRaw {
  validateControlFormatOptions(options);
  const bytes = rawBytes(data);
  if (bytes.length < 1)
    throw new RawCodecError("length", "Control Point request requires an opcode");
  const opcode = bytes[0] as number;
  const length = controlRequestLength(opcode, options);
  if (length === undefined) throw new RawCodecError("kind", "Unknown Control Point request opcode");
  if (bytes.length !== length)
    throw new RawCodecError("length", `Opcode ${opcode} requires exactly ${length} bytes`);
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let operands: number[] = [];
  if ([2, 9, 10, 11, 13, 18, 20].includes(opcode)) operands = [view.getUint16(1, true)];
  else if ([3, 5].includes(opcode)) operands = [view.getInt16(1, true)];
  else if (opcode === 4)
    operands = [
      options?.resistanceFormat === "uint8Tenths" ? (bytes[1] as number) : view.getInt16(1, true),
    ];
  else if ([6, 8, 19].includes(opcode)) operands = [bytes[1] as number];
  else if (opcode === 12)
    operands = [(bytes[1] as number) | ((bytes[2] as number) << 8) | ((bytes[3] as number) << 16)];
  else if ([14, 15, 16].includes(opcode))
    operands = Array.from({ length: rawOperandCounts[opcode] as number }, (_, index) =>
      view.getUint16(1 + index * 2, true),
    );
  else if (opcode === 17)
    operands = [
      view.getInt16(1, true),
      view.getInt16(3, true),
      bytes[5] as number,
      bytes[6] as number,
    ];
  if ((opcode === 8 || opcode === 19) && operands[0] !== 1 && operands[0] !== 2)
    throw new RawCodecError("range", "Control Point action must be 1 or 2");
  return { opcode, operands };
}

/** Encode a raw Control Point request after strict integer, opcode, and arity validation. */
export function encodeFtmsControlRequestRaw(
  request: FtmsControlRequestRaw,
  options?: FtmsControlFormatOptions,
): Uint8Array {
  validateControlFormatOptions(options);
  if (typeof request !== "object" || request === null)
    throw new RawCodecError("null", "Raw Control Point request is required");
  const opcode = rawInteger(request?.opcode, "opcode", 0, 0xff);
  const length = controlRequestLength(opcode, options);
  if (length === undefined) throw new RawCodecError("kind", "Unknown Control Point request opcode");
  if (!Array.isArray(request.operands) || request.operands.length !== rawOperandCounts[opcode])
    throw new RawCodecError("length", "Control Point request has the wrong operand count");
  const operands = request.operands;
  const ranges: readonly (readonly [number, number])[] =
    opcode === 17
      ? [
          [-0x8000, 0x7fff],
          [-0x8000, 0x7fff],
          [0, 0xff],
          [0, 0xff],
        ]
      : opcode === 12
        ? [[0, 0xffffff]]
        : opcode === 4
          ? [
              options?.resistanceFormat === "uint8Tenths"
                ? ([0, 0xff] as const)
                : ([-0x8000, 0x7fff] as const),
            ]
          : [3, 5].includes(opcode)
            ? [[-0x8000, 0x7fff]]
            : [6, 8, 19].includes(opcode)
              ? [[0, 0xff]]
              : Array.from({ length: operands.length }, () => [0, 0xffff] as const);
  const values = operands.map((value, index) =>
    rawInteger(value, `operands[${index}]`, ...(ranges[index] as [number, number])),
  );
  if ((opcode === 8 || opcode === 19) && values[0] !== 1 && values[0] !== 2)
    throw new RawCodecError("range", "Control Point action must be 1 or 2");
  const bytes = new Uint8Array(length);
  bytes[0] = opcode;
  const view = new DataView(bytes.buffer);
  if ([2, 9, 10, 11, 13, 18, 20].includes(opcode)) view.setUint16(1, values[0] as number, true);
  else if ([3, 5].includes(opcode)) view.setInt16(1, values[0] as number, true);
  else if (opcode === 4 && options?.resistanceFormat === "uint8Tenths")
    bytes[1] = values[0] as number;
  else if (opcode === 4) view.setInt16(1, values[0] as number, true);
  else if ([6, 8, 19].includes(opcode)) bytes[1] = values[0] as number;
  else if (opcode === 12) {
    bytes[1] = values[0] as number;
    bytes[2] = (values[0] as number) >>> 8;
    bytes[3] = (values[0] as number) >>> 16;
  } else if ([14, 15, 16].includes(opcode)) {
    values.forEach((value, index) => {
      view.setUint16(1 + index * 2, value, true);
    });
  } else if (opcode === 17) {
    view.setInt16(1, values[0] as number, true);
    view.setInt16(3, values[1] as number, true);
    bytes[5] = values[2] as number;
    bytes[6] = values[3] as number;
  }
  return bytes;
}

/** Decode raw Control Point response evidence, retaining unknown values and diagnostics. */
export function decodeFtmsControlResponseRaw(
  data: ArrayBuffer | Uint8Array,
): FtmsControlResponseRaw {
  const bytes = rawBytes(data);
  if (bytes.length < 3)
    throw new RawCodecError("length", "Control Point response requires at least three bytes");
  if (bytes[0] !== 0x80) throw new RawCodecError("kind", "Payload is not a Control Point response");
  const requestOpcode = bytes[1] as number;
  const resultCode = bytes[2] as number;
  const unknownRequest = requestOpcode > 20 ? 1 : 0;
  const unknownResult = resultCode < 1 || resultCode > 5 ? 1 : 0;
  if (requestOpcode === 19 && resultCode === 1 && bytes.length !== 3 && bytes.length !== 7)
    throw new RawCodecError("length", "Successful Spin Down response must be 3 or 7 bytes");
  if (requestOpcode === 19 && resultCode === 1 && bytes.length === 7) {
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    return {
      requestOpcode,
      resultCode,
      parameter: 1,
      low: view.getUint16(3, true),
      high: view.getUint16(5, true),
      unknownRequest,
      unknownResult,
      unexpectedParameters: 0,
    };
  }
  return {
    requestOpcode,
    resultCode,
    parameter: 0,
    low: 0,
    high: 0,
    unknownRequest,
    unknownResult,
    unexpectedParameters: bytes.length > 3 ? 1 : 0,
  };
}

/** Encode a canonical raw Control Point response; decode-only diagnostics are rejected. */
export function encodeFtmsControlResponseRaw(response: FtmsControlResponseRaw): Uint8Array {
  if (typeof response !== "object" || response === null)
    throw new RawCodecError("null", "Raw Control Point response is required");
  const requestOpcode = rawInteger(response?.requestOpcode, "requestOpcode", 0, 0xff);
  const resultCode = rawInteger(response?.resultCode, "resultCode", 1, 5);
  const parameter = rawInteger(response.parameter, "parameter", 0, 1);
  const low = rawInteger(response.low, "low", 0, 0xffff);
  const high = rawInteger(response.high, "high", 0, 0xffff);
  const unknownRequest = rawInteger(response.unknownRequest, "unknownRequest", 0, 1);
  const unknownResult = rawInteger(response.unknownResult, "unknownResult", 0, 1);
  const unexpectedParameters = rawInteger(
    response.unexpectedParameters,
    "unexpectedParameters",
    0,
    1,
  );
  if (
    unknownResult !== 0 ||
    unexpectedParameters !== 0 ||
    unknownRequest !== (requestOpcode > 20 ? 1 : 0)
  )
    throw new RawCodecError(
      "range",
      "Response diagnostic flags must describe a canonical encodable response",
    );
  if (requestOpcode > 20 && resultCode !== 2)
    throw new RawCodecError("kind", "Unknown request opcodes may only be Not Supported");
  if (parameter === 1 && (requestOpcode !== 19 || resultCode !== 1))
    throw new RawCodecError(
      "range",
      "Spin Down speed parameters require a successful Spin Down response",
    );
  if (parameter === 0 && (low !== 0 || high !== 0))
    throw new RawCodecError(
      "range",
      "Responses without parameters must have zero low and high values",
    );
  const bytes = new Uint8Array(parameter === 1 ? 7 : 3);
  bytes[0] = 0x80;
  bytes[1] = requestOpcode;
  bytes[2] = resultCode;
  if (parameter === 1) {
    const view = new DataView(bytes.buffer);
    view.setUint16(3, low, true);
    view.setUint16(5, high, true);
  }
  return bytes;
}

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

function encodeUnknownControlRequest(
  request: unknown,
  options?: FtmsControlFormatOptions,
): FtmsEncodeResult {
  try {
    validateControlFormatOptions(options);
  } catch (error) {
    return encodeError("invalid_request", "options", (error as Error).message, options);
  }
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
      return options?.resistanceFormat === "uint8Tenths"
        ? (() => {
            const encoded = encodeNumber(request.resistanceLevel, "resistanceLevel", 0, 0xff, 0.1);
            return encoded.ok
              ? {
                  ok: true as const,
                  value: Uint8Array.of(FTMS_OPCODES.SET_TARGET_RESISTANCE, encoded.value),
                }
              : encoded;
          })()
        : encodeInt16Request(
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

export function tryEncodeFtmsControlRequest(
  request: unknown,
  options?: FtmsControlFormatOptions,
): FtmsEncodeResult {
  return encodeUnknownControlRequest(request, options);
}

export function encodeFtmsControlRequest(
  request: FtmsControlRequest,
  options?: FtmsControlFormatOptions,
): Uint8Array {
  const result = tryEncodeFtmsControlRequest(request, options);
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
