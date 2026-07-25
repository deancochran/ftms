import { describe, expect, it } from "vitest";
import { detectFtmsMachineType, ftmsControlModes } from "../src/application.js";
import {
  FTMS_CHARACTERISTICS,
  FTMS_MEASUREMENT_AND_STATUS_CHARACTERISTIC_UUIDS,
  FTMS_OPCODES,
  FTMS_PARSER_DEFINITIONS_BY_UUID,
  getFtmsParserDefinition,
  listFtmsParserDefinitions,
} from "../src/index.js";

describe("FTMS parser registry", () => {
  it("lists all six measurements and both status characteristics", () => {
    expect(FTMS_MEASUREMENT_AND_STATUS_CHARACTERISTIC_UUIDS).toHaveLength(8);
    expect(listFtmsParserDefinitions()).toHaveLength(8);
  });

  it("normalizes characteristic UUID casing", () => {
    expect(getFtmsParserDefinition(FTMS_CHARACTERISTICS.ROWER_DATA.toUpperCase())).toMatchObject({
      machineType: "rower",
      kind: "measurement",
    });
  });

  it("protects exported registries and protocol constants from runtime mutation", () => {
    const definition = getFtmsParserDefinition(FTMS_CHARACTERISTICS.ROWER_DATA);

    expect(Object.isFrozen(FTMS_OPCODES)).toBe(true);
    expect(Object.isFrozen(FTMS_MEASUREMENT_AND_STATUS_CHARACTERISTIC_UUIDS)).toBe(true);
    expect(Object.isFrozen(FTMS_PARSER_DEFINITIONS_BY_UUID)).toBe(true);
    expect(Object.isFrozen(definition)).toBe(true);
    expect(Object.isFrozen(ftmsControlModes)).toBe(true);
    expect(Reflect.set(FTMS_OPCODES, "RESET", 0xff)).toBe(false);
  });
});

describe("FTMS machine-type detection", () => {
  it("prefers an observed data characteristic", () => {
    expect(
      detectFtmsMachineType({
        characteristicUuids: [FTMS_CHARACTERISTICS.ROWER_DATA.toUpperCase()],
        userConfirmedMachineType: "bike",
      }),
    ).toEqual({
      machineType: "rower",
      source: "data_characteristic",
      matchedCharacteristicUuid: FTMS_CHARACTERISTICS.ROWER_DATA,
    });
  });

  it("uses a confirmed machine type when no data characteristic is observed", () => {
    expect(detectFtmsMachineType({ userConfirmedMachineType: "stair_climber" })).toMatchObject({
      machineType: "stair_climber",
      source: "user_confirmed",
    });
  });

  it.each([
    {
      name: "treadmill",
      features: { forceOnBeltSupported: true },
      expected: "treadmill",
    },
    {
      name: "bike",
      features: { powerMeasurementSupported: true, indoorBikeSimulationSupported: true },
      expected: "bike",
    },
    {
      name: "cross trainer",
      features: { strideCountSupported: true, resistanceLevelSupported: true },
      expected: "cross_trainer",
    },
    {
      name: "step climber",
      features: { stepCountSupported: true },
      expected: "step_climber",
    },
  ])("uses the $name feature heuristic", ({ features, expected }) => {
    expect(detectFtmsMachineType({ features })).toMatchObject({
      machineType: expected,
      source: "feature_heuristic",
    });
  });

  it("returns unknown when no evidence is available", () => {
    expect(detectFtmsMachineType({})).toEqual({
      machineType: "unknown",
      source: "unknown",
    });
  });
});
