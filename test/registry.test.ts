import { describe, expect, it } from "vitest";
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
    expect(Reflect.set(FTMS_OPCODES, "RESET", 0xff)).toBe(false);
  });
});
