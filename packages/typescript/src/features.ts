// biome-ignore-all lint/style/noNonNullAssertion: fixed-size internal tables are initialized before indexed use.
import { isByteSource, toDataView } from "./binary.js";
import {
  type FTMSFeatures,
  type FtmsCapabilityDecode,
  type FtmsCapabilityDiagnostic,
  type FtmsCapabilityFeature,
  type FtmsCapabilityKnownKind,
  type FtmsCapabilityPresence,
  type FtmsCapabilityRange,
  type FtmsCapabilityRangeValue,
  type FtmsCapabilityReport,
  type FtmsCapabilitySnapshot,
  type FtmsFeaturesRaw,
  type FtmsRangeFormatOptions,
  type FtmsRangeRaw,
  RawCodecError,
} from "./types.js";

export interface FtmsDecodeErrorDetails {
  code: "kind" | "length" | "range";
  offset: number;
  expected: number;
  actual: number;
  message: string;
}

export type FtmsDecodeError = { ok: false; error: FtmsDecodeErrorDetails };
export type FtmsDecodeSuccess<T> = { ok: true; value: T };
export type FtmsDecodeResult<T> = FtmsDecodeSuccess<T> | FtmsDecodeError;

export type FtmsRangeKind = "speed" | "inclination" | "resistance" | "heartRate" | "power";

export interface FtmsRange {
  kind: FtmsRangeKind;
  min: number;
  max: number;
  increment: number;
  unit: "km/h" | "percent" | "level" | "bpm" | "watts";
}

function rawView(data: ArrayBuffer | Uint8Array): DataView {
  if (!isByteSource(data)) {
    throw new RawCodecError("null", "Raw codec input must be an ArrayBuffer or Uint8Array");
  }
  return toDataView(data);
}

function rawInteger(value: unknown, field: string, minimum: number, maximum: number): number {
  if (typeof value !== "number" || !Number.isFinite(value) || !Number.isInteger(value)) {
    throw new RawCodecError("range", `${field} must be a finite integer`);
  }
  if (value < minimum || value > maximum) {
    throw new RawCodecError("range", `${field} must be between ${minimum} and ${maximum}`);
  }
  return value;
}

/** Decode the eight-byte Feature characteristic without interpreting its bits. */
export function decodeFtmsFeaturesRaw(data: ArrayBuffer | Uint8Array): FtmsFeaturesRaw {
  const view = rawView(data);
  if (view.byteLength !== 8)
    throw new RawCodecError("length", "FTMS Features requires exactly 8 bytes");
  return { machine: view.getUint32(0, true), target: view.getUint32(4, true) };
}

/** Encode raw Feature words verbatim, including all reserved bits. */
export function encodeFtmsFeaturesRaw(features: FtmsFeaturesRaw): Uint8Array {
  if (typeof features !== "object" || features === null)
    throw new RawCodecError("null", "Raw Features value is required");
  const machine = rawInteger(features?.machine, "machine", 0, 0xffffffff);
  const target = rawInteger(features?.target, "target", 0, 0xffffffff);
  const bytes = new Uint8Array(8);
  const view = new DataView(bytes.buffer);
  view.setUint32(0, machine, true);
  view.setUint32(4, target, true);
  return bytes;
}

const rawRangeMetadata: Record<FtmsRangeRaw["kind"], readonly [number, number, number]> = {
  speed: [6, 100, 0],
  inclination: [6, 10, 1],
  resistance: [3, 1, 2],
  heartRate: [3, 1, 3],
  power: [6, 1, 4],
};

function validateRangeOptions(options?: FtmsRangeFormatOptions): void {
  if (
    options !== undefined &&
    (options === null ||
      typeof options !== "object" ||
      Array.isArray(options) ||
      Object.keys(options).some((key) => key !== "resistanceFormat"))
  )
    throw new RawCodecError("kind", "Range format options must be an options object");
  if (
    options?.resistanceFormat !== undefined &&
    !["uint8Whole", "signed16Tenths"].includes(options.resistanceFormat)
  )
    throw new RawCodecError("kind", "Unsupported resistance range format");
}

/** Decode a Supported Range into its exact raw integer numerators and metadata. */
export function decodeFtmsRangeRaw(
  kind: FtmsRangeRaw["kind"],
  data: ArrayBuffer | Uint8Array,
  options?: FtmsRangeFormatOptions,
): FtmsRangeRaw {
  validateRangeOptions(options);
  if (options?.resistanceFormat === "signed16Tenths" && kind !== "resistance")
    throw new RawCodecError("kind", "Signed resistance format applies only to resistance");
  const alternateResistance =
    kind === "resistance" && options?.resistanceFormat === "signed16Tenths";
  const metadata = Object.hasOwn(rawRangeMetadata, kind) ? rawRangeMetadata[kind] : undefined;
  if (!metadata) throw new RawCodecError("kind", `Unsupported FTMS range kind: ${String(kind)}`);
  const view = rawView(data);
  const [baseLength, baseScaleDivisor, unit] = metadata;
  const length = alternateResistance ? 6 : baseLength;
  const scaleDivisor = alternateResistance ? 10 : baseScaleDivisor;
  if (view.byteLength !== length)
    throw new RawCodecError("length", `FTMS ${kind} range requires exactly ${length} bytes`);
  const signed = kind === "inclination" || kind === "power" || alternateResistance;
  const minimum =
    length === 3 ? view.getUint8(0) : signed ? view.getInt16(0, true) : view.getUint16(0, true);
  const maximum =
    length === 3 ? view.getUint8(1) : signed ? view.getInt16(2, true) : view.getUint16(2, true);
  const increment = length === 3 ? view.getUint8(2) : view.getUint16(4, true);
  if (minimum > maximum || increment === 0)
    throw new RawCodecError(
      "range",
      "Range minimum must not exceed maximum and increment must be positive",
    );
  return { kind, minimum, maximum, increment, scaleDivisor, unit };
}

/** Encode a Supported Range from exact raw integer numerators and required metadata. */
export function encodeFtmsRangeRaw(
  range: FtmsRangeRaw,
  options?: FtmsRangeFormatOptions,
): Uint8Array {
  if (typeof range !== "object" || range === null)
    throw new RawCodecError("null", "Raw range value is required");
  validateRangeOptions(options);
  if (options?.resistanceFormat === "signed16Tenths") {
    if (range.kind !== "resistance")
      throw new RawCodecError("kind", "Signed resistance format applies only to resistance");
    if (range.scaleDivisor !== 10 || range.unit !== 2)
      throw new RawCodecError("range", "Signed resistance uses divisor 10 and level unit");
    const min = rawInteger(range.minimum, "minimum", -32768, 32767),
      max = rawInteger(range.maximum, "maximum", -32768, 32767),
      increment = rawInteger(range.increment, "increment", 1, 65535);
    if (min > max) throw new RawCodecError("range", "Range minimum must not exceed maximum");
    const bytes = new Uint8Array(6),
      view = new DataView(bytes.buffer);
    view.setInt16(0, min, true);
    view.setInt16(2, max, true);
    view.setUint16(4, increment, true);
    return bytes;
  }
  const metadata = Object.hasOwn(rawRangeMetadata, range?.kind)
    ? rawRangeMetadata[range.kind]
    : undefined;
  if (!metadata)
    throw new RawCodecError("kind", `Unsupported FTMS range kind: ${String(range?.kind)}`);
  const [length, scaleDivisor, unit] = metadata;
  if (
    rawInteger(range.scaleDivisor, "scaleDivisor", 0, 0xffff) !== scaleDivisor ||
    rawInteger(range.unit, "unit", 0, 4) !== unit
  ) {
    throw new RawCodecError("range", "Range unit and scaleDivisor must match its kind");
  }
  const signed = range.kind === "inclination" || range.kind === "power";
  const minimum = rawInteger(
    range.minimum,
    "minimum",
    signed ? -0x8000 : 0,
    length === 3 ? 0xff : signed ? 0x7fff : 0xffff,
  );
  const maximum = rawInteger(
    range.maximum,
    "maximum",
    signed ? -0x8000 : 0,
    length === 3 ? 0xff : signed ? 0x7fff : 0xffff,
  );
  const increment = rawInteger(range.increment, "increment", 1, length === 3 ? 0xff : 0xffff);
  if (minimum > maximum) throw new RawCodecError("range", "Range minimum must not exceed maximum");
  const bytes = new Uint8Array(length);
  const view = new DataView(bytes.buffer);
  if (length === 3) {
    bytes[0] = minimum;
    bytes[1] = maximum;
    bytes[2] = increment;
  } else {
    if (signed) {
      view.setInt16(0, minimum, true);
      view.setInt16(2, maximum, true);
    } else {
      view.setUint16(0, minimum, true);
      view.setUint16(2, maximum, true);
    }
    view.setUint16(4, increment, true);
  }
  return bytes;
}

/** Encode with an explicit nonstandard resistance layout selection. */

function lengthError(actual: number, expected: number): FtmsDecodeError {
  return {
    ok: false,
    error: {
      code: "length",
      offset: 0,
      expected,
      actual,
      message: `Expected exactly ${expected} bytes, received ${actual}`,
    },
  };
}

function isBitSet(word: number, bit: number): boolean {
  return (word & (2 ** bit)) !== 0;
}

export function decodeFtmsFeatures(data: ArrayBuffer | Uint8Array): FtmsDecodeResult<FTMSFeatures> {
  const view = toDataView(data);
  if (view.byteLength !== 8) {
    return lengthError(view.byteLength, 8);
  }

  const machine = view.getUint32(0, true);
  const target = view.getUint32(4, true);
  const powerTargetSettingSupported = isBitSet(target, 3);
  const indoorBikeSimulationSupported = isBitSet(target, 13);
  const resistanceTargetSettingSupported = isBitSet(target, 2);

  return {
    ok: true,
    value: {
      averageSpeedSupported: isBitSet(machine, 0),
      cadenceSupported: isBitSet(machine, 1),
      totalDistanceSupported: isBitSet(machine, 2),
      inclinationSupported: isBitSet(machine, 3),
      elevationGainSupported: isBitSet(machine, 4),
      paceSupported: isBitSet(machine, 5),
      stepCountSupported: isBitSet(machine, 6),
      resistanceLevelSupported: isBitSet(machine, 7),
      strideCountSupported: isBitSet(machine, 8),
      expendedEnergySupported: isBitSet(machine, 9),
      heartRateMeasurementSupported: isBitSet(machine, 10),
      metabolicEquivalentSupported: isBitSet(machine, 11),
      elapsedTimeSupported: isBitSet(machine, 12),
      remainingTimeSupported: isBitSet(machine, 13),
      powerMeasurementSupported: isBitSet(machine, 14),
      forceOnBeltSupported: isBitSet(machine, 15),
      userDataRetentionSupported: isBitSet(machine, 16),
      speedTargetSettingSupported: isBitSet(target, 0),
      inclinationTargetSettingSupported: isBitSet(target, 1),
      resistanceTargetSettingSupported,
      powerTargetSettingSupported,
      heartRateTargetSettingSupported: isBitSet(target, 4),
      targetedExpendedEnergySupported: isBitSet(target, 5),
      targetedStepNumberSupported: isBitSet(target, 6),
      targetedStrideNumberSupported: isBitSet(target, 7),
      targetedDistanceSupported: isBitSet(target, 8),
      targetedTrainingTimeSupported: isBitSet(target, 9),
      targetedTimeTwoHRZonesSupported: isBitSet(target, 10),
      targetedTimeThreeHRZonesSupported: isBitSet(target, 11),
      targetedTimeFiveHRZonesSupported: isBitSet(target, 12),
      indoorBikeSimulationSupported,
      wheelCircumferenceSupported: isBitSet(target, 14),
      spinDownControlSupported: isBitSet(target, 15),
      targetedCadenceSupported: isBitSet(target, 16),
      supportsERG: powerTargetSettingSupported,
      supportsSIM: indoorBikeSimulationSupported,
      supportsResistance: resistanceTargetSettingSupported,
    },
  };
}

function rangeError(
  min: number,
  max: number,
  increment: number,
  incrementOffset: number,
): FtmsDecodeError {
  const invalidMinimum = min > max;
  return {
    ok: false,
    error: {
      code: "range",
      offset: invalidMinimum ? 0 : incrementOffset,
      expected: 1,
      actual: invalidMinimum ? min - max : increment,
      message: invalidMinimum
        ? "Minimum must not exceed maximum"
        : "Increment must be greater than zero",
    },
  };
}

export function decodeFtmsRange(
  kind: FtmsRangeKind,
  data: ArrayBuffer | Uint8Array,
  options?: FtmsRangeFormatOptions,
): FtmsDecodeResult<FtmsRange> {
  if (!(["speed", "inclination", "resistance", "heartRate", "power"] as const).includes(kind)) {
    return {
      ok: false,
      error: {
        code: "kind",
        offset: 0,
        expected: 0,
        actual: 0,
        message: `Unsupported FTMS range kind: ${String(kind)}`,
      },
    };
  }

  // Keep normalized callers subject to the same explicit, caller-owned format
  // validation as raw callers; selections are never inferred from bytes.
  validateRangeOptions(options);
  if (options?.resistanceFormat === "signed16Tenths" && kind !== "resistance")
    throw new RawCodecError("kind", "Signed resistance format applies only to resistance");
  const view = toDataView(data);
  const alternateResistance =
    kind === "resistance" && options?.resistanceFormat === "signed16Tenths";
  const expectedLength = alternateResistance
    ? 6
    : kind === "heartRate" || kind === "resistance"
      ? 3
      : 6;
  if (view.byteLength !== expectedLength) {
    return lengthError(view.byteLength, expectedLength);
  }

  let min: number;
  let max: number;
  let increment: number;
  let unit: FtmsRange["unit"];

  switch (kind) {
    case "speed":
      min = view.getUint16(0, true) / 100;
      max = view.getUint16(2, true) / 100;
      increment = view.getUint16(4, true) / 100;
      unit = "km/h";
      break;
    case "inclination":
      min = view.getInt16(0, true) / 10;
      max = view.getInt16(2, true) / 10;
      increment = view.getUint16(4, true) / 10;
      unit = "percent";
      break;
    case "power":
      min = view.getInt16(0, true);
      max = view.getInt16(2, true);
      increment = view.getUint16(4, true);
      unit = "watts";
      break;
    case "heartRate":
      min = view.getUint8(0);
      max = view.getUint8(1);
      increment = view.getUint8(2);
      unit = "bpm";
      break;
    case "resistance":
      min = alternateResistance ? view.getInt16(0, true) / 10 : view.getUint8(0);
      max = alternateResistance ? view.getInt16(2, true) / 10 : view.getUint8(1);
      increment = alternateResistance ? view.getUint16(4, true) / 10 : view.getUint8(2);
      unit = "level";
      break;
  }

  if (min > max || increment <= 0) {
    return rangeError(min, max, increment, expectedLength === 3 ? 2 : 4);
  }

  return { ok: true, value: { kind, min, max, increment, unit } };
}

export function decodeSupportedSpeedRange(
  data: ArrayBuffer | Uint8Array,
): FtmsDecodeResult<FtmsRange> {
  return decodeFtmsRange("speed", data);
}

export function decodeSupportedInclinationRange(
  data: ArrayBuffer | Uint8Array,
): FtmsDecodeResult<FtmsRange> {
  return decodeFtmsRange("inclination", data);
}

export function decodeSupportedResistanceRange(
  data: ArrayBuffer | Uint8Array,
  options?: FtmsRangeFormatOptions,
): FtmsDecodeResult<FtmsRange> {
  return decodeFtmsRange("resistance", data, options);
}

export function decodeSupportedHeartRateRange(
  data: ArrayBuffer | Uint8Array,
): FtmsDecodeResult<FtmsRange> {
  return decodeFtmsRange("heartRate", data);
}

export function decodeSupportedPowerRange(
  data: ArrayBuffer | Uint8Array,
): FtmsDecodeResult<FtmsRange> {
  return decodeFtmsRange("power", data);
}

const CAP_BASE = "00001000800000805f9b34fb";
const TARGET_FOR_OPCODE = [
  255, 255, 0, 1, 2, 3, 4, 255, 255, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
] as const;
const RANGE_FOR_TARGET = [0, 1, 2, 4, 3] as const;
const REQUIRED_PROPERTIES = [0, 2, 16, 16, 16, 16, 16, 16, 18, 2, 2, 2, 2, 2, 40, 16] as const;
const INVALID_REASONS = 0x008 | 0x020 | 0x080 | 0x200;

function capabilityKind(uuid: string): FtmsCapabilityKnownKind {
  if (!/^[0-9a-f]{32}$/.test(uuid) || uuid.slice(0, 4) !== "0000" || uuid.slice(8) !== CAP_BASE)
    return 0;
  const value = Number.parseInt(uuid.slice(4, 8), 16);
  return value >= 0x2acc && value <= 0x2ada ? ((value - 0x2acc + 1) as FtmsCapabilityKnownKind) : 0;
}
function capabilityBytes(value: Uint8Array | ArrayBuffer): Uint8Array {
  if (!isByteSource(value))
    throw new RawCodecError("null", "Capability bytes must be an ArrayBuffer or Uint8Array");
  if (ArrayBuffer.isView(value))
    return new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
  if (Object.prototype.toString.call(value) === "[object ArrayBuffer]")
    return new Uint8Array(value);
  throw new RawCodecError("null", "Capability bytes must be an ArrayBuffer or Uint8Array");
}
function validateSnapshot(snapshot: FtmsCapabilitySnapshot): void {
  if (!snapshot || typeof snapshot !== "object")
    throw new RawCodecError("null", "Capability snapshot is required");
  if (
    ![0, 1, 2, 3].includes(snapshot.discovery) ||
    ![0, 1, 2, 3].includes(snapshot.scope) ||
    !Number.isSafeInteger(snapshot.generation) ||
    snapshot.generation < 0 ||
    snapshot.generation > 0xffffffff ||
    !Array.isArray(snapshot.characteristics)
  )
    throw new RawCodecError("kind", "Invalid capability snapshot");
  for (const c of snapshot.characteristics) {
    if (
      !c ||
      typeof c !== "object" ||
      !/^[0-9a-f]{32}$/.test(c.uuid) ||
      !Number.isSafeInteger(c.properties) ||
      c.properties < 0 ||
      c.properties > 0xffff ||
      ![0, 1, 2].includes(c.readState) ||
      ![0, 1, 2, 3, 4, 5].includes(c.reason) ||
      (c.readState !== 2 && c.reason !== 0) ||
      (c.readState !== 1 && capabilityBytes(c.bytes).length !== 0)
    )
      throw new RawCodecError("kind", "Invalid capability characteristic");
  }
}

/** Evaluate static FTMS declarations and protocol prerequisites. This does not
 * authorize a control procedure or perform BLE/GATT I/O. */
export function evaluateFtmsCapabilities(
  snapshot: FtmsCapabilitySnapshot,
  rangeOptions?: FtmsRangeFormatOptions,
): FtmsCapabilityReport {
  // Invalid caller format is an API error, not malformed device evidence.
  validateRangeOptions(rangeOptions);
  validateSnapshot(snapshot);
  const characteristics = snapshot.characteristics;
  const kinds = characteristics.map((c) => capabilityKind(c.uuid));
  const first = Array<number>(16).fill(-1);
  const counts = Array<number>(16).fill(0);
  kinds.forEach((kind, index) => {
    if (kind) {
      if (first[kind]! < 0) first[kind] = index;
      counts[kind] = Math.min(2, counts[kind]! + 1);
    }
  });
  const scopeOk = snapshot.scope === 1;
  const presence = Array<FtmsCapabilityPresence>(16).fill(0);
  const diagnostics: FtmsCapabilityDiagnostic[] = [];
  for (let kind = 1; kind < 16; kind++) {
    if (counts[kind]! > 1) {
      presence[kind] = 3;
      diagnostics.push([3, kind as FtmsCapabilityKnownKind, first[kind]!]);
    } else if (counts[kind]! === 1) presence[kind] = 2;
    else if (snapshot.discovery === 2 && scopeOk) presence[kind] = 1;
  }
  if (!scopeOk) diagnostics.push([0, 0, null]);
  const absent = snapshot.scope === 2 && snapshot.discovery === 2 && characteristics.length === 0;
  if (snapshot.scope === 2 && !absent) diagnostics.push([11, 0, null]);
  if (snapshot.discovery !== 2) diagnostics.push([snapshot.discovery === 3 ? 2 : 1, 0, null]);
  for (let i = 0; i < characteristics.length; i++) {
    const kind = kinds[i]!;
    const c = characteristics[i]!;
    if (!kind || !scopeOk) continue;
    const required = REQUIRED_PROPERTIES[kind]!;
    if ((c.properties & required) !== required) diagnostics.push([5, kind, i]);
    if ((c.properties & ~required) !== 0) diagnostics.push([6, kind, i]);
    if (c.readState === 2) diagnostics.push([c.reason === 2 ? 8 : 7, kind, i]);
  }
  let machine = 0;
  let target = 0;
  let machineUnknown = 0;
  let targetUnknown = 0;
  const decode = (
    kind: number,
    range?: 0 | 1 | 2 | 3 | 4,
  ): [FtmsCapabilityDecode, FtmsCapabilityRangeValue | null] => {
    if (!scopeOk || presence[kind]! !== 2) return [0, null];
    const c = characteristics[first[kind]!]!;
    if (c.readState === 2) return [3, null];
    if (c.readState !== 1) return [0, null];
    try {
      if (range === undefined) {
        const raw = decodeFtmsFeaturesRaw(capabilityBytes(c.bytes));
        machine = raw.machine;
        target = raw.target;
        machineUnknown = (machine & ~0x1ffff) >>> 0;
        targetUnknown = (target & ~0x1ffff) >>> 0;
        return [1, null];
      }
      const raw = decodeFtmsRangeRaw(
        (["speed", "inclination", "resistance", "heartRate", "power"] as const)[range],
        capabilityBytes(c.bytes),
        range === 2 ? rangeOptions : undefined,
      );
      return [
        1,
        [
          range,
          raw.minimum,
          raw.maximum,
          raw.increment,
          raw.scaleDivisor as 1 | 10 | 100,
          raw.unit as 0 | 1 | 2 | 3 | 4,
        ],
      ];
    } catch {
      return [2, null];
    }
  };
  const featureDecode = decode(1)[0];
  const feature: FtmsCapabilityFeature = [
    presence[1]!,
    featureDecode,
    scopeOk && presence[1] === 2 ? first[1]! : null,
    machine,
    target,
    machineUnknown,
    targetUnknown,
  ];
  if (featureDecode === 2) diagnostics.push([9, 1, first[1]!]);
  const ranges: FtmsCapabilityRange[] = [0, 1, 2, 3, 4].map((range) => {
    const kind = 9 + range;
    const result = decode(kind, range as 0 | 1 | 2 | 3 | 4);
    if (result[0] === 2) diagnostics.push([9, kind as FtmsCapabilityKnownKind, first[kind]!]);
    return [
      presence[kind]!,
      result[0],
      scopeOk && presence[kind] === 2 ? first[kind]! : null,
      result[1],
    ];
  });
  if (scopeOk) {
    if (presence[1] === 1) diagnostics.push([4, 1, null]);
    if ((presence[14] === 2 || presence[14] === 3) && presence[15] === 1)
      diagnostics.push([4, 15, null]);
    if (featureDecode === 1) {
      if (target & 0x1ffff && presence[14] === 1) diagnostics.push([4, 14, null]);
      for (let bit = 0; bit < 5; bit++) {
        const range = RANGE_FOR_TARGET[bit]!;
        if (target & (2 ** bit) && presence[9 + range] === 1)
          diagnostics.push([10, (9 + range) as FtmsCapabilityKnownKind, null]);
      }
    }
  }
  const characteristicReasons = (kind: number, unavailable: number, invalid: number) =>
    presence[kind] === 0
      ? unavailable
      : presence[kind] !== 2 ||
          characteristics[first[kind]!]!.properties !== REQUIRED_PROPERTIES[kind]!
        ? invalid
        : 0;
  const operations = TARGET_FOR_OPCODE.map((bit, opcode) => {
    let declaration: 0 | 1 | 2 = 0;
    let prerequisite: 0 | 1 | 2 | 3 = 2;
    let reasons = 0;
    if (!scopeOk) {
      reasons = 1;
      if (absent) {
        declaration = 1;
        prerequisite = 0;
      } else if (snapshot.scope === 2) prerequisite = 3;
      return [
        opcode,
        bit,
        (opcode === 18 || opcode === 19 ? 1 : 0) as 0 | 1,
        declaration,
        prerequisite,
        reasons,
      ] as const;
    }
    if (bit === 255) declaration = presence[14] === 2 ? 2 : presence[14] === 1 ? 1 : 0;
    else if (featureDecode === 1) declaration = target & (2 ** bit) ? 2 : 1;
    if (declaration === 1)
      return [
        opcode,
        bit,
        (opcode === 18 || opcode === 19 ? 1 : 0) as 0 | 1,
        declaration,
        0,
        0,
      ] as const;
    if (snapshot.discovery !== 2) reasons |= 2;
    reasons |= characteristicReasons(1, 4, 8);
    if (bit !== 255 && presence[1] === 2)
      reasons |= featureDecode === 2 ? 8 : featureDecode === 1 ? 0 : 4;
    reasons |= characteristicReasons(14, 16, 32) | characteristicReasons(15, 64, 128);
    if (bit !== 255 && bit < 5 && declaration === 2) {
      const range = (RANGE_FOR_TARGET as readonly number[])[bit]!;
      const kind = 9 + range;
      reasons |= characteristicReasons(kind, 256, 512);
      if (presence[kind] === 2)
        reasons |= ranges[range]![1] === 2 ? 512 : ranges[range]![1] === 1 ? 0 : 256;
    }
    prerequisite = reasons & INVALID_REASONS ? 3 : reasons === 0 ? 1 : 2;
    return [
      opcode,
      bit,
      (opcode === 18 || opcode === 19 ? 1 : 0) as 0 | 1,
      declaration,
      prerequisite,
      reasons,
    ] as const;
  });
  const observations = characteristics.map(
    (c, index) =>
      [
        index,
        c.uuid,
        c.properties,
        kinds[index]!,
        c.readState,
        c.reason,
        capabilityBytes(c.bytes).length,
      ] as const,
  );
  return {
    generation: snapshot.generation,
    discovery: snapshot.discovery,
    scope: snapshot.scope,
    observationCount: observations.length,
    diagnosticCount: diagnostics.length,
    presence,
    feature,
    ranges,
    operations,
    observations,
    diagnostics,
  };
}
