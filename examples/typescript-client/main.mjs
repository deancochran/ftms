import {
  decodeFtmsFeatures,
  decodeFtmsRange,
  encodeFtmsControlRequest,
  parseRegisteredFtmsPayload,
} from "@deancochran/ftms";

function requireValue(condition, message) {
  if (!condition) throw new Error(message);
}

// These are illustrative characteristic values, not a device capture or fixture loader.
const features = decodeFtmsFeatures(Uint8Array.of(0x03, 0, 0, 0, 0x08, 0, 0, 0));
requireValue(features.ok, "Feature characteristic did not decode");
requireValue(features.value.cadenceSupported, "Expected cadence declaration");
requireValue(features.value.powerTargetSettingSupported, "Expected power target declaration");

const powerRange = decodeFtmsRange("power", Uint8Array.of(0x00, 0x00, 0xf4, 0x01, 0x0a, 0x00));
requireValue(powerRange.ok, "Power range did not decode");
requireValue(powerRange.value.min === 0 && powerRange.value.max === 500, "Unexpected power range");

const bike = parseRegisteredFtmsPayload(
  "00002ad2-0000-1000-8000-00805f9b34fb",
  Uint8Array.of(
    0xfe,
    0x1f,
    0xe8,
    0x03,
    0x84,
    0x03,
    0xb4,
    0x00,
    0xaa,
    0x00,
    0xe8,
    0x03,
    0x00,
    0x08,
    0xfa,
    0x00,
    0xf0,
    0x00,
    0x2c,
    0x01,
    0x90,
    0x01,
    0x05,
    0x91,
    0x50,
    0x58,
    0x02,
    0x64,
    0x00,
  ),
);
const treadmill = parseRegisteredFtmsPayload(
  "00002acd-0000-1000-8000-00805f9b34fb",
  Uint8Array.of(
    0xfe,
    0x1f,
    0xe8,
    0x03,
    0x84,
    0x03,
    0x03,
    0x02,
    0x01,
    0xf1,
    0xff,
    0x19,
    0x00,
    0x7b,
    0x00,
    0x2d,
    0x00,
    0x2c,
    0x01,
    0x40,
    0x01,
    0xf4,
    0x01,
    0x58,
    0x02,
    0x0a,
    0x96,
    0x55,
    0x10,
    0x0e,
    0x58,
    0x02,
    0xec,
    0xff,
    0xfa,
    0x00,
  ),
);
requireValue(
  bike?.kind === "measurement" && bike.metrics.powerWatts === 250,
  "Bike payload mismatch",
);
requireValue(
  treadmill?.kind === "measurement" && treadmill.metrics.inclinationPercent === -1.5,
  "Treadmill payload mismatch",
);

// This only constructs bytes. A successful encoder call never authorizes a BLE write.
const requestControl = encodeFtmsControlRequest({ op: "requestControl" });
requireValue(
  requestControl.length === 1 && requestControl[0] === 0x00,
  "Request Control encoding mismatch",
);

console.log("Feature declarations:", {
  cadence: features.value.cadenceSupported,
  powerTarget: features.value.powerTargetSettingSupported,
});
console.log("Declared power range:", powerRange.value);
console.log("Indoor Bike sample:", bike.metrics);
console.log("Treadmill sample:", treadmill.metrics);
console.log(
  "Request Control bytes:",
  [...requestControl].map((byte) => `0x${byte.toString(16).padStart(2, "0")}`).join(" "),
);
console.log(
  "Declarations and ranges are not execution permission; discover the correct service state, properties, security, ownership, and ranges before any control procedure.",
);
