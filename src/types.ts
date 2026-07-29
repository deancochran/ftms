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
  parse(data: ArrayBuffer | Uint8Array): ParsedFtmsPayload;
}

export interface ParsedFtmsIndoorBikeData {
  hrBpm: number | null;
  powerWatts: number | null;
  cadenceRpm: number | null;
  speedMps: number | null;
  truncated: boolean;
}
