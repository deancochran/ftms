import { FTMS_CHARACTERISTICS, FTMS_OPCODES, FTMS_RESULT_CODES } from "./constants.js";
import type { FTMSFeatures, FTMSResponse, FtmsMachineType } from "./types.js";

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
  | "control_lost"
  | "control_uncertain";

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

export interface FtmsPendingOperation {
  opcode: number;
  generation: number;
  requestedMode: ControlMode | null;
  reset: boolean;
}

export interface FtmsControlReducerState {
  support: FtmsControlSupportLevel;
  pending: FtmsPendingOperation | null;
  currentMode: ControlMode | null;
  disposed: boolean;
}

export type FtmsControlReducerEvent =
  | { type: "capabilityDiscovered" }
  | { type: "requestControlSent"; generation: number }
  | {
      type: "commandSent";
      opcode: number;
      generation: number;
      requestedMode?: ControlMode;
    }
  | { type: "responseReceived"; response: FTMSResponse; generation: number }
  | { type: "timeout"; generation: number }
  | { type: "recoveryCompleted" }
  | { type: "permissionLost" }
  | { type: "disconnected" }
  | { type: "disposed" };

const ftmsCommandOpcodes = new Set<number>(
  Object.values(FTMS_OPCODES).filter(
    (opcode) => opcode !== FTMS_OPCODES.REQUEST_CONTROL && opcode !== FTMS_OPCODES.RESPONSE_CODE,
  ),
);

export function createInitialFtmsControlState(): FtmsControlReducerState {
  return {
    support: "metrics_only",
    pending: null,
    currentMode: null,
    disposed: false,
  };
}

/** @experimental Transport-agnostic state helper; the caller still owns GATT serialization. */
export const initialFtmsControlState: Readonly<FtmsControlReducerState> = Object.freeze(
  createInitialFtmsControlState(),
);

/**
 * @experimental Reduces legal single-flight control transitions. After a timeout,
 * recoveryCompleted must only be emitted once stale responses can no longer arrive.
 */
export function reduceFtmsControl(
  state: FtmsControlReducerState,
  event: FtmsControlReducerEvent,
): FtmsControlReducerState {
  if (state.disposed) {
    return state;
  }

  switch (event.type) {
    case "capabilityDiscovered":
      return state.support === "metrics_only" ||
        state.support === "control_rejected" ||
        state.support === "control_lost"
        ? { ...state, support: "control_capable" }
        : state;
    case "requestControlSent": {
      const canRequestControl =
        state.support === "control_capable" ||
        state.support === "control_rejected" ||
        state.support === "control_lost";
      if (!canRequestControl || state.pending !== null) {
        return state;
      }
      return {
        ...state,
        support: "control_requesting",
        pending: {
          opcode: FTMS_OPCODES.REQUEST_CONTROL,
          generation: event.generation,
          requestedMode: null,
          reset: false,
        },
      };
    }
    case "commandSent": {
      if (
        state.support !== "control_granted" ||
        state.pending !== null ||
        !ftmsCommandOpcodes.has(event.opcode)
      ) {
        return state;
      }
      const reset = event.opcode === FTMS_OPCODES.RESET;
      return {
        ...state,
        support: reset ? "control_lost" : state.support,
        currentMode: reset ? null : state.currentMode,
        pending: {
          opcode: event.opcode,
          generation: event.generation,
          requestedMode: event.requestedMode ?? null,
          reset,
        },
      };
    }
    case "responseReceived": {
      const pending = state.pending;
      if (
        pending === null ||
        pending.generation !== event.generation ||
        pending.opcode !== event.response.requestOpCode
      ) {
        return state;
      }

      const responseSucceeded = event.response.resultCode === FTMS_RESULT_CODES.SUCCESS;
      if (!responseSucceeded) {
        const controlLost = event.response.resultCode === FTMS_RESULT_CODES.CONTROL_NOT_PERMITTED;
        const requestRejected = pending.opcode === FTMS_OPCODES.REQUEST_CONTROL;
        return {
          ...state,
          support: controlLost
            ? "control_lost"
            : requestRejected
              ? "control_rejected"
              : state.support,
          currentMode: controlLost ? null : state.currentMode,
          pending: null,
        };
      }

      if (pending.opcode === FTMS_OPCODES.REQUEST_CONTROL) {
        return { ...state, support: "control_granted", pending: null };
      }
      if (pending.reset) {
        return {
          ...state,
          support: "control_capable",
          pending: null,
          currentMode: null,
        };
      }
      return {
        ...state,
        pending: null,
        currentMode: pending.requestedMode ?? state.currentMode,
      };
    }
    case "timeout":
      if (state.pending?.generation !== event.generation) {
        return state;
      }
      return {
        ...state,
        support: "control_uncertain",
        pending: null,
        currentMode: null,
      };
    case "recoveryCompleted":
      return state.support === "control_uncertain"
        ? { ...state, support: "control_capable" }
        : state;
    case "permissionLost":
    case "disconnected":
      return {
        ...state,
        support: "control_lost",
        pending: null,
        currentMode: null,
      };
    case "disposed":
      return {
        support: "metrics_only",
        pending: null,
        currentMode: null,
        disposed: true,
      };
  }
}

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
  if (!features) return "unknown";
  if (features.forceOnBeltSupported || (features.inclinationSupported && features.paceSupported)) {
    return "treadmill";
  }
  if (features.powerMeasurementSupported && features.indoorBikeSimulationSupported) return "bike";
  if (features.strideCountSupported && features.resistanceLevelSupported) return "cross_trainer";
  if (features.stepCountSupported) return "step_climber";
  return "unknown";
}

/** Detects a machine type from observed, confirmed, then heuristic evidence. */
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
    return { machineType: input.userConfirmedMachineType, source: "user_confirmed" };
  }

  const machineType = inferFtmsMachineTypeFromFeatures(input.features);
  return {
    machineType,
    source: machineType === "unknown" ? "unknown" : "feature_heuristic",
  };
}
