export * from "./constants.js";
export * from "./control.js";
export * from "./features.js";
export * from "./parsers.js";
export * from "./types.js";

import { FTMS_CHARACTERISTICS, FTMS_DATA_CHARACTERISTICS } from "./constants.js";

export const FTMS_MACHINE_DATA_CHARACTERISTIC_UUIDS = Object.freeze(
  Object.values(FTMS_DATA_CHARACTERISTICS),
);

export const FTMS_MEASUREMENT_AND_STATUS_CHARACTERISTIC_UUIDS = Object.freeze([
  ...FTMS_MACHINE_DATA_CHARACTERISTIC_UUIDS,
  FTMS_CHARACTERISTICS.TRAINING_STATUS,
  FTMS_CHARACTERISTICS.STATUS,
] as const);
