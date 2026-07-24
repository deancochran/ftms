/** @deprecated Compatibility enum; prefer protocol request unions in new code. */
export enum ControlMode {
  ERG = "erg",
  SIM = "sim",
  RESISTANCE = "resistance",
  SPEED = "speed",
  INCLINATION = "inclination",
  HEART_RATE = "heart_rate",
  CADENCE = "cadence",
}

/** @deprecated Compatibility type; prefer FtmsMachineType. */
export type FTMSDeviceType = "bike" | "rower" | "elliptical" | "treadmill";

export type FtmsMachineType =
  | "bike"
  | "treadmill"
  | "rower"
  | "cross_trainer"
  | "step_climber"
  | "stair_climber"
  | "unknown";

export type FtmsMachineTypeSource =
  | "data_characteristic"
  | "user_confirmed"
  | "feature_heuristic"
  | "unknown";

export type FtmsControlSupportLevel =
  | "metrics_only"
  | "control_capable"
  | "control_requesting"
  | "control_granted"
  | "control_rejected"
  | "control_lost";

export type FtmsControlState = Exclude<FtmsControlSupportLevel, "metrics_only">;

/** @experimental Application-facing control-mode presentation contract. */
export type FtmsControlMode =
  | "status"
  | "erg"
  | "free_ride"
  | "grade"
  | "inclination"
  | "resistance"
  | "speed"
  | "target_heart_rate"
  | "target_cadence"
  | "workout_goal"
  | "calibration"
  | "machine_state";

export const ftmsControlModes = Object.freeze([
  "status",
  "erg",
  "free_ride",
  "grade",
  "inclination",
  "resistance",
  "speed",
  "target_heart_rate",
  "target_cadence",
  "workout_goal",
  "calibration",
  "machine_state",
] as const satisfies readonly FtmsControlMode[]);

/** @experimental Application-facing safety policy, not an FTMS wire value. */
export type FtmsSafetyLevel = "none" | "confirm" | "strong_confirm" | "blocked";

export interface FtmsCharacteristicProperties {
  readable?: boolean;
  notifiable?: boolean;
  indicatable?: boolean;
  writableWithResponse?: boolean;
  writableWithoutResponse?: boolean;
}

/** @experimental Application-facing mode presentation contract. */
export interface FtmsAvailableModeRange {
  min: number;
  max: number;
  increment: number;
  unit: string;
}

/** @experimental Application-facing mode presentation contract. */
export interface FtmsAvailableMode {
  id: FtmsControlMode;
  label: string;
  enabled: boolean;
  disabledReason?: string;
  range?: FtmsAvailableModeRange;
  safetyLevel: FtmsSafetyLevel;
}

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

export interface FTMSResponse {
  requestOpCode: number;
  resultCode: number;
  resultCodeName: string;
  success: boolean;
  parameters?: Uint8Array;
}

export interface FTMSControlEvent {
  timestamp: number;
  controlType:
    | "power_target"
    | "simulation"
    | "resistance"
    | "speed"
    | "inclination"
    | "heart_rate"
    | "cadence";
  targetValue: number;
  actualValue?: number;
  success: boolean;
  errorMessage?: string;
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
