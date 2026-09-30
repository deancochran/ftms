import assert from "node:assert/strict";
import {
  decodeFtmsControlResponse,
  decodeFtmsFeatures,
  decodeSupportedPowerRange,
  parseRegisteredFtmsPayload,
  tryEncodeFtmsControlRequest,
} from "@deancochran/ftms";
import { parseBikeDataView, parseBlePlxBike } from "./transport.mjs";

const bytes = Uint8Array.of(0x44, 0x00, 0x10, 0x0e, 0xb4, 0x00, 0xfa, 0x00);
const reading = parseRegisteredFtmsPayload("00002ad2-0000-1000-8000-00805f9b34fb", bytes);
assert.equal(reading?.kind, "measurement");
assert.equal(reading.metrics.powerWatts, 250);

const features = decodeFtmsFeatures(Uint8Array.of(0x03, 0, 0, 0, 0x08, 0, 0, 0));
assert.equal(features.ok, true);
assert.equal(features.value.cadenceSupported, true);
assert.equal(features.value.powerTargetSettingSupported, true);
assert.equal(decodeFtmsFeatures(Uint8Array.of(0)).ok, false);

const range = decodeSupportedPowerRange(Uint8Array.of(0, 0, 0xf4, 1, 0x0a, 0));
assert.equal(range.ok, true);
assert.deepEqual(range.value, { kind: "power", min: 0, max: 500, increment: 10, unit: "watts" });

// Constructs bytes only. Neither a range nor successful encoding grants permission.
const encoded = tryEncodeFtmsControlRequest({ op: "setTargetPower", powerWatts: 250 });
assert.equal(encoded.ok, true);
assert.deepEqual([...encoded.value], [0x05, 0xfa, 0x00]);
assert.equal(tryEncodeFtmsControlRequest({ op: "setTargetPower", powerWatts: 250.5 }).ok, false);
const response = decodeFtmsControlResponse(Uint8Array.of(0x80, 0x05, 0x01));
assert.equal(response.ok, true);
assert.equal(response.value.success, true);

const resistance = tryEncodeFtmsControlRequest(
  { op: "setTargetResistance", resistanceLevel: 12.3 },
  { resistanceFormat: "uint8Tenths" },
);
assert.equal(resistance.ok, true);
assert.deepEqual([...resistance.value], [0x04, 0x7b]);

// Test a nonzero offset AND an oversized backing buffer; neither prefix nor tail
// belongs to the characteristic value.
const padded = Uint8Array.of(0xff, 0xff, ...bytes, 0xee);
const view = new DataView(padded.buffer, 2, bytes.length);
assert.deepEqual(parseBikeDataView(view), reading);
assert.equal(parseBikeDataView(new DataView(padded.buffer, 2, 7)).diagnostics.truncated, true);
assert.deepEqual(parseBlePlxBike("RAAQDrQA+gA="), reading);
assert.equal(parseBlePlxBike(null), null);
assert.equal(parseBlePlxBike(undefined), null);
assert.throws(() => parseBlePlxBike(42), TypeError);
assert.throws(() => parseBlePlxBike("x"));
console.log("Recipes passed: dispatch, features, range, controls, DataView and base64 boundaries.");
