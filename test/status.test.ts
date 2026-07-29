import { describe, expect, it } from "vitest";
import {
  type FtmsMachineStatusParameter,
  parseFtmsMachineStatus,
  parseFtmsTrainingStatus,
} from "../src/index.js";

describe("Training Status", () => {
  it("requires the flags and status-code bytes", () => {
    const result = parseFtmsTrainingStatus(Uint8Array.of(0));
    expect(result.diagnostics.truncated).toBe(true);
    expect(result.status?.code).toBeNull();
  });

  it("decodes a status without a string", () => {
    const result = parseFtmsTrainingStatus(Uint8Array.of(0, 0x0d));
    expect(result.status).toMatchObject({
      code: 0x0d,
      label: "manual_mode",
      details: {
        kind: "training_status",
        stringPresent: false,
        extendedStringPresent: false,
      },
    });
    expect(result.diagnostics.truncated).toBe(false);
  });

  it("decodes a UTF-8 status string and extended-string indicator", () => {
    const text = Uint8Array.of(0x57, 0x61, 0x72, 0x6d, 0x2d, 0x75, 0x70, 0x20, 0xe2, 0x9c, 0x93);
    const result = parseFtmsTrainingStatus(Uint8Array.of(0x03, 0x02, ...text));
    expect(result.status?.details).toMatchObject({
      kind: "training_status",
      stringPresent: true,
      extendedStringPresent: true,
      trainingStatusString: "Warm-up ✓",
    });
    expect(result.diagnostics.bytesRead).toBe(2 + text.byteLength);
  });

  it.each([
    ["invalid four-byte leader", [0xf5, 0x80, 0x80, 0x80]],
    ["overlong two-byte sequence", [0xc0, 0xaf]],
    ["overlong three-byte sequence", [0xe0, 0x80, 0x80]],
    ["surrogate sequence", [0xed, 0xa0, 0x80]],
    ["code point above Unicode range", [0xf4, 0x90, 0x80, 0x80]],
  ])("replaces a malformed UTF-8 %s without throwing", (_name, malformed) => {
    const result = parseFtmsTrainingStatus(Uint8Array.of(0x01, 0x01, ...malformed));
    expect(result.status?.details).toMatchObject({
      kind: "training_status",
      trainingStatusString: expect.stringContaining("\uFFFD"),
    });
  });

  it("diagnoses reserved and inconsistent flags", () => {
    const result = parseFtmsTrainingStatus(Uint8Array.of(0x86, 0x01));
    expect(result.diagnostics.issues).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ code: "reserved_flags" }),
        expect.objectContaining({ code: "invalid_flags" }),
      ]),
    );
  });

  it("diagnoses trailing bytes when no string is advertised", () => {
    const result = parseFtmsTrainingStatus(Uint8Array.of(0, 1, 0x41));
    expect(result.diagnostics.issues).toContainEqual(
      expect.objectContaining({ code: "trailing_bytes", offset: 2 }),
    );
  });

  it("diagnoses every reserved training state without treating it as truncation", () => {
    for (let code = 0x10; code <= 0xff; code += 1) {
      const result = parseFtmsTrainingStatus(Uint8Array.of(0, code));
      expect(result.status?.label).toBe("reserved");
      expect(result.diagnostics.truncated).toBe(false);
      expect(result.diagnostics.issues).toContainEqual({
        code: "reserved_value",
        field: "trainingStatus",
        offset: 1,
        actual: code,
      });
    }
  });
});

interface MachineStatusCase {
  name: string;
  bytes: number[];
  expected: Partial<FtmsMachineStatusParameter>;
}

const machineStatusCases: readonly MachineStatusCase[] = [
  { name: "reset", bytes: [0x01], expected: { kind: "none" } },
  {
    name: "stopped by user",
    bytes: [0x02, 0x01],
    expected: { kind: "stop_pause", action: "stop" },
  },
  { name: "safety key", bytes: [0x03], expected: { kind: "none" } },
  { name: "started by user", bytes: [0x04], expected: { kind: "none" } },
  {
    name: "target speed",
    bytes: [0x05, 0xd2, 0x04],
    expected: { kind: "speed", speedKph: 12.34 },
  },
  {
    name: "target inclination",
    bytes: [0x06, 0xf4, 0xff],
    expected: { kind: "inclination", inclinationPercent: -1.2 },
  },
  {
    name: "target resistance",
    bytes: [0x07, 0xf4, 0xff],
    expected: { kind: "resistance", resistanceLevel: -1.2 },
  },
  {
    name: "target power",
    bytes: [0x08, 0x9c, 0xff],
    expected: { kind: "power", powerWatts: -100 },
  },
  {
    name: "target heart rate",
    bytes: [0x09, 150],
    expected: { kind: "heart_rate", heartRateBpm: 150 },
  },
  {
    name: "target energy",
    bytes: [0x0a, 0xf4, 0x01],
    expected: { kind: "energy", energyKcal: 500 },
  },
  {
    name: "target steps",
    bytes: [0x0b, 0x58, 0x02],
    expected: { kind: "steps", steps: 600 },
  },
  {
    name: "target strides",
    bytes: [0x0c, 0xbc, 0x02],
    expected: { kind: "strides", strides: 700 },
  },
  {
    name: "target distance",
    bytes: [0x0d, 0x03, 0x02, 0x01],
    expected: { kind: "distance", distanceMeters: 0x010203 },
  },
  {
    name: "target training time",
    bytes: [0x0e, 0x10, 0x0e],
    expected: { kind: "training_time", seconds: 3600 },
  },
  {
    name: "two heart-rate zones",
    bytes: [0x0f, 10, 0, 20, 0],
    expected: { kind: "hr_zones", seconds: [10, 20] },
  },
  {
    name: "three heart-rate zones",
    bytes: [0x10, 10, 0, 20, 0, 30, 0],
    expected: { kind: "hr_zones", seconds: [10, 20, 30] },
  },
  {
    name: "five heart-rate zones",
    bytes: [0x11, 10, 0, 20, 0, 30, 0, 40, 0, 50, 0],
    expected: { kind: "hr_zones", seconds: [10, 20, 30, 40, 50] },
  },
  {
    name: "simulation parameters",
    bytes: [0x12, 0xe8, 0x03, 0xfa, 0x00, 10, 20],
    expected: {
      kind: "simulation",
      windSpeedMps: 1,
      gradePercent: 2.5,
      crr: 0.001,
      cwKgPerM: 0.2,
    },
  },
  {
    name: "wheel circumference",
    bytes: [0x13, 0x08, 0x52],
    expected: { kind: "wheel_circumference", circumferenceMm: 2100 },
  },
  {
    name: "spin-down success",
    bytes: [0x14, 0x02],
    expected: { kind: "spin_down", status: "success" },
  },
  {
    name: "target cadence",
    bytes: [0x15, 180, 0],
    expected: { kind: "cadence", cadenceRpm: 90 },
  },
  { name: "control permission lost", bytes: [0xff], expected: { kind: "none" } },
];

describe("Fitness Machine Status", () => {
  it.each(machineStatusCases)("decodes $name", ({ bytes, expected }) => {
    const result = parseFtmsMachineStatus(Uint8Array.from(bytes));
    expect(result.status?.details).toMatchObject(expected);
    expect(result.status?.label).not.toBe("reserved");
    expect(result.diagnostics.truncated).toBe(false);
  });

  it.each([
    { name: "one-byte parameter", bytes: [0x02] },
    { name: "two-byte parameter", bytes: [0x05, 1] },
    { name: "three-byte parameter", bytes: [0x0d, 1, 2] },
    { name: "two-zone array", bytes: [0x0f, 1, 0, 2] },
    { name: "simulation", bytes: [0x12, 1, 0, 2, 0, 3] },
    { name: "five-zone array", bytes: [0x11, 1, 0, 2, 0, 3, 0, 4, 0, 5] },
  ])("marks a truncated $name status", ({ bytes }) => {
    const result = parseFtmsMachineStatus(Uint8Array.from(bytes));
    expect(result.diagnostics.truncated).toBe(true);
    expect(result.status?.details).toBeNull();
  });

  it("diagnoses an unknown opcode without guessing its parameters", () => {
    const result = parseFtmsMachineStatus(Uint8Array.of(0x22, 1, 2));
    expect(result.status).toMatchObject({ code: 0x22, label: "reserved", details: null });
    expect(result.diagnostics.issues).toContainEqual(
      expect.objectContaining({ code: "unknown_opcode", actual: 0x22 }),
    );
  });

  it("diagnoses trailing bytes for a known opcode", () => {
    const result = parseFtmsMachineStatus(Uint8Array.of(0x01, 0xaa));
    expect(result.diagnostics.issues).toContainEqual(
      expect.objectContaining({ code: "trailing_bytes", offset: 1 }),
    );
  });

  it("diagnoses a reserved stop/pause value", () => {
    const result = parseFtmsMachineStatus(Uint8Array.of(0x02, 0x03));
    expect(result.status?.details).toMatchObject({ kind: "stop_pause", action: "reserved" });
    expect(result.diagnostics.issues).toContainEqual(
      expect.objectContaining({ code: "reserved_value", field: "stopPause" }),
    );
  });

  it("diagnoses a reserved spin-down value", () => {
    const result = parseFtmsMachineStatus(Uint8Array.of(0x14, 0x05));
    expect(result.status?.details).toMatchObject({ kind: "spin_down", status: "reserved" });
    expect(result.diagnostics.issues).toContainEqual(
      expect.objectContaining({ code: "reserved_value", field: "spinDownStatus" }),
    );
  });
});
