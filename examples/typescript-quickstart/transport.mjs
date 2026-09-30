import { parseFtmsIndoorBikeMeasurement } from "@deancochran/ftms";
import base64 from "base64-js";

/** Web Bluetooth characteristic.value is a DataView, not a whole backing buffer. */
export function parseBikeDataView(value) {
  if (!(value instanceof DataView)) throw new TypeError("Expected a DataView");
  return parseFtmsIndoorBikeMeasurement(
    new Uint8Array(value.buffer, value.byteOffset, value.byteLength),
  );
}

/** react-native-ble-plx Characteristic.value is nullable base64, not UTF-8 text. */
export function parseBlePlxBike(value) {
  if (value === null || value === undefined) return null;
  if (typeof value !== "string") throw new TypeError("Expected base64 or null");
  return parseFtmsIndoorBikeMeasurement(base64.toByteArray(value));
}
