export type FtmsMachineType =
  | "bike"
  | "treadmill"
  | "rower"
  | "cross_trainer"
  | "step_climber"
  | "stair_climber"
  | "unknown";

export interface FtmsSupportedRange {
  min: number;
  max: number;
  increment: number;
}

/** Error thrown by the strict raw wire codecs. `null` denotes a non-byte input. */
export class RawCodecError extends RangeError {
  readonly code: "null" | "length" | "kind" | "range";

  constructor(code: RawCodecError["code"], message: string) {
    super(message);
    this.name = "RawCodecError";
    this.code = code;
  }
}

/** Uninterpreted FTMS Feature characteristic words, including reserved bits. */
export interface FtmsFeaturesRaw {
  readonly machine: number;
  readonly target: number;
}

export type FtmsRangeRawKind = "speed" | "inclination" | "resistance" | "heartRate" | "power";
export interface FtmsRangeRaw {
  readonly kind: FtmsRangeRawKind;
  readonly minimum: number;
  readonly maximum: number;
  readonly increment: number;
  readonly scaleDivisor: number;
  readonly unit: number;
}
/** Compatibility selections are caller-owned evidence, never manufacturer inference. */
export interface FtmsMeasurementFormatOptions {
  readonly resistanceFormat?: "uint8Whole" | "signed16Tenths";
  readonly treadmillPaceFormat?: "uint16" | "uint8Legacy";
}
export interface FtmsRangeFormatOptions {
  readonly resistanceFormat?: "uint8Whole" | "signed16Tenths";
}
/** A selected range layout and the structurally possible alternatives.
 * A valid alternative is byte-layout evidence only: it neither proves a physical
 * unit nor selects a profile or authorizes a control. */
export type FtmsRangeProfile =
  | "uint16Hundredths"
  | "signed16Tenths"
  | "uint8Whole"
  | "uint8Bpm"
  | "signed16Watts";
export type FtmsRangeInspectionStatus = "valid" | "length" | "range";
export interface FtmsRangeInspectionCandidate {
  readonly profile: FtmsRangeProfile;
  readonly expectedLength: number;
  readonly status: FtmsRangeInspectionStatus;
  readonly value: FtmsRangeRaw | null;
}
export interface FtmsRangeInspection {
  readonly selectedProfile: FtmsRangeProfile;
  readonly actualLength: number;
  readonly expectedLength: number;
  readonly status: FtmsRangeInspectionStatus;
  readonly value: FtmsRangeRaw | null;
  readonly candidates: readonly FtmsRangeInspectionCandidate[];
}
/** Caller-owned C.7 facts. Undefined means unknown; false is distinct from unknown. */
export interface FtmsCapabilityC7Evidence {
  readonly bondingSupported?: boolean;
  readonly featureMayChangeOverLifetime?: boolean;
}
/** Caller-selected Control Point resistance wire format; it is never inferred. */
export interface FtmsControlFormatOptions {
  readonly resistanceFormat?: "signed16Tenths" | "uint8Tenths";
}

/** A pure, caller-owned FTMS service-discovery snapshot. UUIDs are 32 lowercase
 * hexadecimal digits in Bluetooth display/network byte order. */
export type FtmsCapabilityDiscovery = 0 | 1 | 2 | 3;
export type FtmsCapabilityScope = 0 | 1 | 2 | 3;
export type FtmsCapabilityPresence = 0 | 1 | 2 | 3;
export type FtmsCapabilityReadState = 0 | 1 | 2;
export type FtmsCapabilityReadReason = 0 | 1 | 2 | 3 | 4 | 5;
export type FtmsCapabilityDecode = 0 | 1 | 2 | 3;
export type FtmsCapabilityDeclaration = 0 | 1 | 2;
export type FtmsCapabilityPrerequisite = 0 | 1 | 2 | 3;
export type FtmsCapabilityKnownKind =
  | 0
  | 1
  | 2
  | 3
  | 4
  | 5
  | 6
  | 7
  | 8
  | 9
  | 10
  | 11
  | 12
  | 13
  | 14
  | 15;

export interface FtmsCapabilityCharacteristic {
  readonly uuid: string;
  readonly properties: number;
  readonly readState: FtmsCapabilityReadState;
  readonly reason: FtmsCapabilityReadReason;
  readonly bytes: Uint8Array | ArrayBuffer;
}
export interface FtmsCapabilitySnapshot {
  readonly discovery: FtmsCapabilityDiscovery;
  readonly scope: FtmsCapabilityScope;
  /** An opaque unsigned 32-bit discovery generation; it is not ordered here. */
  readonly generation: number;
  readonly characteristics: readonly FtmsCapabilityCharacteristic[];
  /** C.7 compatibility evidence; this does not assert security or authorization. */
  readonly c7?: FtmsCapabilityC7Evidence;
}
export type FtmsCapabilityFeature = readonly [
  FtmsCapabilityPresence,
  FtmsCapabilityDecode,
  number | null,
  number,
  number,
  number,
  number,
];
export type FtmsCapabilityRangeValue = readonly [
  0 | 1 | 2 | 3 | 4,
  number,
  number,
  number,
  1 | 10 | 100,
  0 | 1 | 2 | 3 | 4,
];
export type FtmsCapabilityRange = readonly [
  FtmsCapabilityPresence,
  FtmsCapabilityDecode,
  number | null,
  FtmsCapabilityRangeValue | null,
];
export type FtmsCapabilityOperation = readonly [
  number,
  number,
  0 | 1,
  FtmsCapabilityDeclaration,
  FtmsCapabilityPrerequisite,
  number,
];
export type FtmsCapabilityObservation = readonly [
  number,
  string,
  number,
  FtmsCapabilityKnownKind,
  FtmsCapabilityReadState,
  FtmsCapabilityReadReason,
  number,
];
export type FtmsCapabilityDiagnostic = readonly [number, FtmsCapabilityKnownKind, number | null];
/** Normalized representation defined by shared/conformance/capabilities/v1. */
export interface FtmsCapabilityReport {
  readonly generation: number;
  readonly discovery: FtmsCapabilityDiscovery;
  readonly scope: FtmsCapabilityScope;
  readonly observationCount: number;
  readonly diagnosticCount: number;
  readonly presence: readonly FtmsCapabilityPresence[];
  readonly feature: FtmsCapabilityFeature;
  readonly ranges: readonly FtmsCapabilityRange[];
  readonly operations: readonly FtmsCapabilityOperation[];
  readonly observations: readonly FtmsCapabilityObservation[];
  readonly diagnostics: readonly FtmsCapabilityDiagnostic[];
}

/** Raw Control Point request operands, in their on-wire integer order. */
export interface FtmsControlRequestRaw {
  readonly opcode: number;
  readonly operands: readonly number[];
}

/** Raw Control Point response evidence; flags are integer 0/1 diagnostics. */
export interface FtmsControlResponseRaw {
  readonly requestOpcode: number;
  readonly resultCode: number;
  readonly parameter: number;
  readonly low: number;
  readonly high: number;
  readonly unknownRequest: number;
  readonly unknownResult: number;
  readonly unexpectedParameters: number;
}

export interface FTMSFeatures {
  averageSpeedSupported: boolean;
  cadenceSupported: boolean;
  totalDistanceSupported: boolean;
  inclinationSupported: boolean;
  elevationGainSupported: boolean;
  paceSupported: boolean;
  stepCountSupported: boolean;
  resistanceLevelSupported: boolean;
  strideCountSupported: boolean;
  expendedEnergySupported: boolean;
  heartRateMeasurementSupported: boolean;
  metabolicEquivalentSupported: boolean;
  elapsedTimeSupported: boolean;
  remainingTimeSupported: boolean;
  powerMeasurementSupported: boolean;
  forceOnBeltSupported: boolean;
  userDataRetentionSupported: boolean;
  speedTargetSettingSupported: boolean;
  inclinationTargetSettingSupported: boolean;
  resistanceTargetSettingSupported: boolean;
  powerTargetSettingSupported: boolean;
  heartRateTargetSettingSupported: boolean;
  targetedExpendedEnergySupported: boolean;
  targetedStepNumberSupported: boolean;
  targetedStrideNumberSupported: boolean;
  targetedDistanceSupported: boolean;
  targetedTrainingTimeSupported: boolean;
  targetedTimeTwoHRZonesSupported: boolean;
  targetedTimeThreeHRZonesSupported: boolean;
  targetedTimeFiveHRZonesSupported: boolean;
  indoorBikeSimulationSupported: boolean;
  wheelCircumferenceSupported: boolean;
  spinDownControlSupported: boolean;
  targetedCadenceSupported: boolean;
  /** @deprecated Use powerTargetSettingSupported. */
  supportsERG: boolean;
  /** @deprecated Use indoorBikeSimulationSupported. */
  supportsSIM: boolean;
  /** @deprecated Use resistanceTargetSettingSupported. */
  supportsResistance: boolean;
  speedRange?: FtmsSupportedRange;
  inclinationRange?: FtmsSupportedRange;
  resistanceRange?: FtmsSupportedRange;
  powerRange?: FtmsSupportedRange;
  heartRateRange?: FtmsSupportedRange;
}

export type FtmsControlResponseParameter =
  | { kind: "none" }
  | {
      kind: "spin_down_speeds";
      targetSpeedLowKph: number;
      targetSpeedHighKph: number;
    };

export interface FTMSResponse {
  requestOpCode: number;
  resultCode: number;
  resultCodeName: string;
  success: boolean;
  parameter: FtmsControlResponseParameter;
  issues: readonly FtmsDiagnostic[];
}

export interface FtmsRuntimeMetrics {
  hrBpm: number | null;
  powerWatts: number | null;
  averagePowerWatts: number | null;
  cadenceRpm: number | null;
  averageCadenceRpm: number | null;
  speedMps: number | null;
  averageSpeedMps: number | null;
  distanceMeters: number | null;
  elapsedTimeSeconds: number | null;
  remainingTimeSeconds: number | null;
  energyKcal: number | null;
  energyPerHourKcal: number | null;
  energyPerMinuteKcal: number | null;
  metabolicEquivalent: number | null;
  stepCount: number | null;
  stepRateSpm: number | null;
  averageStepRateSpm: number | null;
  strideCount: number | null;
  floorCount: number | null;
  positiveElevationGainMeters: number | null;
  negativeElevationGainMeters: number | null;
  inclinationPercent: number | null;
  rampAngleDegrees: number | null;
  resistanceLevel: number | null;
  instantaneousPaceSecondsPer500m: number | null;
  averagePaceSecondsPer500m: number | null;
  forceOnBeltNewtons: number | null;
  strokeRateSpm: number | null;
  averageStrokeRateSpm: number | null;
  strokeCount: number | null;
  movementDirection: "forward" | "backward" | null;
}

export type FtmsDiagnosticCode =
  | "truncated"
  | "unavailable"
  | "more_data"
  | "reserved_flags"
  | "invalid_flags"
  | "reserved_value"
  | "trailing_bytes"
  | "unknown_opcode";

export interface FtmsDiagnostic {
  code: FtmsDiagnosticCode;
  field?: string;
  offset?: number;
  expected?: number;
  actual?: number;
}

export interface FtmsParserDiagnostics {
  truncated: boolean;
  flags?: number;
  bytesRead: number;
  byteLength: number;
  moreData?: boolean;
  issues: readonly FtmsDiagnostic[];
}

export interface FtmsTrainingStatusDetails {
  kind: "training_status";
  flags: number;
  stringPresent: boolean;
  extendedStringPresent: boolean;
  trainingStatusString?: string;
}

export type FtmsMachineStatusParameter =
  | { kind: "none" }
  | { kind: "stop_pause"; action: "stop" | "pause" | "reserved" }
  | { kind: "speed"; speedKph: number }
  | { kind: "inclination"; inclinationPercent: number }
  | { kind: "resistance"; resistanceLevel: number }
  | { kind: "power"; powerWatts: number }
  | { kind: "heart_rate"; heartRateBpm: number }
  | { kind: "energy"; energyKcal: number }
  | { kind: "steps"; steps: number }
  | { kind: "strides"; strides: number }
  | { kind: "distance"; distanceMeters: number }
  | { kind: "training_time"; seconds: number }
  | { kind: "hr_zones"; seconds: readonly number[] }
  | {
      kind: "simulation";
      windSpeedMps: number;
      gradePercent: number;
      crr: number;
      cwKgPerM: number;
    }
  | { kind: "wheel_circumference"; circumferenceMm: number }
  | {
      kind: "spin_down";
      status: "requested" | "success" | "error" | "stop_pedaling" | "reserved";
    }
  | { kind: "cadence"; cadenceRpm: number };

export interface FtmsStatusPayload {
  code: number | null;
  label: string;
  /** Scalar compatibility projection for status values that contain one number. */
  parameter?: number;
  details: FtmsTrainingStatusDetails | FtmsMachineStatusParameter | null;
}

export type FtmsCharacteristicKind = "measurement" | "training_status" | "machine_status";

export interface ParsedFtmsPayload {
  kind: FtmsCharacteristicKind;
  characteristicUuid: string;
  machineType: FtmsMachineType;
  metrics: FtmsRuntimeMetrics;
  status: FtmsStatusPayload | null;
  diagnostics: FtmsParserDiagnostics;
}

export interface FtmsParserDefinition {
  uuid: string;
  name: string;
  kind: FtmsCharacteristicKind;
  machineType: FtmsMachineType;
  parse(data: ArrayBuffer | Uint8Array, options?: FtmsMeasurementFormatOptions): ParsedFtmsPayload;
}

export interface ParsedFtmsIndoorBikeData {
  hrBpm: number | null;
  powerWatts: number | null;
  cadenceRpm: number | null;
  speedMps: number | null;
  truncated: boolean;
}

/** Raw wire-unit measurement evidence. Values use the fixed 30-field corpus order. */
export interface FtmsMeasurementRaw {
  readonly kind: number;
  readonly flags: number;
  readonly present: number;
  readonly unavailable: number;
  readonly values: readonly number[];
  readonly moreData: number;
  readonly backward: number;
  readonly truncated: number;
  readonly trailingBytes: number;
  readonly reservedFlags: number;
  readonly bytesRead: number;
}

/** Raw machine-status evidence; parameter operands retain their on-wire units. */
export interface FtmsMachineStatusRaw {
  readonly opcode: number;
  readonly action: number;
  readonly parameter: FtmsControlRequestRaw | null;
  readonly unknownOpcode: number;
  readonly reservedValue: number;
  readonly truncated: number;
  readonly trailingBytes: number;
}

/** Raw training-status evidence. `text` is a view copied from the payload span. */
export interface FtmsTrainingStatusRaw {
  readonly flags: number;
  readonly code: number;
  readonly text: Uint8Array;
  readonly textOffset: number;
  readonly textSize: number;
  readonly textPresent: number;
  readonly extendedString: number;
  readonly reservedFlags: number;
  readonly reservedValue: number;
  readonly invalidFlags: number;
  readonly invalidUtf8: number;
  readonly truncated: number;
  readonly trailingBytes: number;
}
