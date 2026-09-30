import assert from "node:assert/strict";
import { parseFtmsIndoorBikeMeasurement } from "@deancochran/ftms";

// Illustrative bytes: flags, speed (0.01 km/h), cadence (0.5 rpm), power (W).
const bytes = Uint8Array.of(0x44, 0x00, 0x10, 0x0e, 0xb4, 0x00, 0xfa, 0x00);
const reading = parseFtmsIndoorBikeMeasurement(bytes);
assert.equal(reading.metrics.speedMps, 10);
assert.equal(reading.metrics.cadenceRpm, 90);
assert.equal(reading.metrics.powerWatts, 250);
assert.equal(reading.metrics.hrBpm, null);
assert.equal(reading.diagnostics.truncated, false);

const short = parseFtmsIndoorBikeMeasurement(bytes.subarray(0, 7));
assert.equal(short.diagnostics.truncated, true);
assert.equal(short.metrics.powerWatts, null);

console.log("speedMps=10 cadenceRpm=90 powerWatts=250 hrBpm=null");
console.log("complete.truncated=false short.truncated=true");
