export * from "./constants.js";
export * from "./control.js";
export * from "./features.js";
export * from "./parsers.js";
export * from "./types.js";

import { FTMS_CHARACTERISTICS, FTMS_DATA_CHARACTERISTICS } from "./constants.js";
import type { FTMSFeatures, FtmsMachineType, FtmsMachineTypeSource } from "./types.js";

export const FTMS_MACHINE_DATA_CHARACTERISTIC_UUIDS = Object.freeze(
  Object.values(FTMS_DATA_CHARACTERISTICS),
);

export const FTMS_MEASUREMENT_AND_STATUS_CHARACTERISTIC_UUIDS = Object.freeze([
  ...FTMS_MACHINE_DATA_CHARACTERISTIC_UUIDS,
  FTMS_CHARACTERISTICS.TRAINING_STATUS,
  FTMS_CHARACTERISTICS.STATUS,
] as const);

export const FTMS_MACHINE_TYPE_BY_DATA_CHARACTERISTIC_UUID: Readonly<
  Record<string, FtmsMachineType>
> = Object.freeze({
  [FTMS_CHARACTERISTICS.TREADMILL_DATA]: "treadmill",
  [FTMS_CHARACTERISTICS.CROSS_TRAINER_DATA]: "cross_trainer",
  [FTMS_CHARACTERISTICS.STEP_CLIMBER_DATA]: "step_climber",
  [FTMS_CHARACTERISTICS.STAIR_CLIMBER_DATA]: "stair_climber",
  [FTMS_CHARACTERISTICS.ROWER_DATA]: "rower",
  [FTMS_CHARACTERISTICS.INDOOR_BIKE_DATA]: "bike",
});

export interface FtmsMachineTypeDetectionInput {
  characteristicUuids?: readonly string[];
  features?: Partial<FTMSFeatures> | null;
  userConfirmedMachineType?: FtmsMachineType | null;
}

export interface FtmsMachineTypeDetectionResult {
  machineType: FtmsMachineType;
  source: FtmsMachineTypeSource;
  matchedCharacteristicUuid?: string;
}

function inferFtmsMachineTypeFromFeatures(
  features?: Partial<FTMSFeatures> | null,
): FtmsMachineType {
  if (!features) {
    return "unknown";
  }
  if (features.forceOnBeltSupported || (features.inclinationSupported && features.paceSupported)) {
    return "treadmill";
  }
  if (features.powerMeasurementSupported && features.indoorBikeSimulationSupported) {
    return "bike";
  }
  if (features.strideCountSupported && features.resistanceLevelSupported) {
    return "cross_trainer";
  }
  if (features.stepCountSupported) {
    return "step_climber";
  }
  return "unknown";
}

/**
 * Detects a machine type from characteristic evidence, user confirmation, or a
 * best-effort feature heuristic, in that order. Feature heuristics are not
 * authoritative and may return unknown.
 */
export function detectFtmsMachineType(
  input: FtmsMachineTypeDetectionInput,
): FtmsMachineTypeDetectionResult {
  for (const uuid of input.characteristicUuids ?? []) {
    const normalizedUuid = uuid.toLowerCase();
    const machineType = FTMS_MACHINE_TYPE_BY_DATA_CHARACTERISTIC_UUID[normalizedUuid];
    if (machineType) {
      return {
        machineType,
        source: "data_characteristic",
        matchedCharacteristicUuid: normalizedUuid,
      };
    }
  }

  if (input.userConfirmedMachineType && input.userConfirmedMachineType !== "unknown") {
    return {
      machineType: input.userConfirmedMachineType,
      source: "user_confirmed",
    };
  }

  const inferred = inferFtmsMachineTypeFromFeatures(input.features);
  return {
    machineType: inferred,
    source: inferred === "unknown" ? "unknown" : "feature_heuristic",
  };
}
