import { describe, expect, it } from "vitest";
import {
  ControlMode,
  createInitialFtmsControlState,
  FTMS_OPCODES,
  FTMS_RESULT_CODES,
  type FTMSResponse,
  type FtmsControlReducerState,
  initialFtmsControlState,
  reduceFtmsControl,
} from "../src/index.js";

function response(opcode: number, resultCode: number = FTMS_RESULT_CODES.SUCCESS): FTMSResponse {
  return {
    requestOpCode: opcode,
    resultCode,
    resultCodeName: resultCode === FTMS_RESULT_CODES.SUCCESS ? "success" : "failure",
    success: resultCode === FTMS_RESULT_CODES.SUCCESS,
  };
}

function grantedState(mode: ControlMode | null = null): FtmsControlReducerState {
  return {
    support: "control_granted",
    pending: null,
    currentMode: mode,
    disposed: false,
  };
}

function capableState(): FtmsControlReducerState {
  return reduceFtmsControl(createInitialFtmsControlState(), {
    type: "capabilityDiscovered",
  });
}

describe("FTMS control reducer", () => {
  it("starts metrics-only with no pending operation", () => {
    expect(createInitialFtmsControlState()).toEqual({
      support: "metrics_only",
      pending: null,
      currentMode: null,
      disposed: false,
    });
  });

  it("does not expose a mutable shared initial state", () => {
    expect(Object.isFrozen(initialFtmsControlState)).toBe(true);
    expect(Reflect.set(initialFtmsControlState, "support", "control_granted")).toBe(false);
  });

  it("moves to control-capable after discovery", () => {
    const state = reduceFtmsControl(createInitialFtmsControlState(), {
      type: "capabilityDiscovered",
    });
    expect(state.support).toBe("control_capable");
  });

  it("ignores control requests before capability discovery", () => {
    const initial = createInitialFtmsControlState();
    expect(
      reduceFtmsControl(initial, {
        type: "requestControlSent",
        generation: 1,
      }),
    ).toBe(initial);
  });

  it("ignores commands until control is granted", () => {
    const capable = capableState();
    expect(
      reduceFtmsControl(capable, {
        type: "commandSent",
        opcode: FTMS_OPCODES.SET_TARGET_POWER,
        generation: 1,
        requestedMode: ControlMode.ERG,
      }),
    ).toBe(capable);
  });

  it("records the generation when requesting control", () => {
    const state = reduceFtmsControl(capableState(), {
      type: "requestControlSent",
      generation: 7,
    });
    expect(state).toMatchObject({
      support: "control_requesting",
      pending: { opcode: FTMS_OPCODES.REQUEST_CONTROL, generation: 7 },
    });
  });

  it("does not overwrite an operation that is already pending", () => {
    const requesting = reduceFtmsControl(capableState(), {
      type: "requestControlSent",
      generation: 1,
    });
    expect(
      reduceFtmsControl(requesting, {
        type: "commandSent",
        opcode: FTMS_OPCODES.SET_TARGET_POWER,
        generation: 2,
        requestedMode: ControlMode.ERG,
      }),
    ).toBe(requesting);
  });

  it("grants control only for a matching successful response", () => {
    const requesting = reduceFtmsControl(capableState(), {
      type: "requestControlSent",
      generation: 7,
    });
    const granted = reduceFtmsControl(requesting, {
      type: "responseReceived",
      generation: 7,
      response: response(FTMS_OPCODES.REQUEST_CONTROL),
    });
    expect(granted).toMatchObject({ support: "control_granted", pending: null });
  });

  it("derives response success from the result code instead of a caller flag", () => {
    const requesting = reduceFtmsControl(capableState(), {
      type: "requestControlSent",
      generation: 7,
    });
    const rejected = reduceFtmsControl(requesting, {
      type: "responseReceived",
      generation: 7,
      response: {
        ...response(FTMS_OPCODES.REQUEST_CONTROL, FTMS_RESULT_CODES.CONTROL_NOT_PERMITTED),
        success: true,
      },
    });

    expect(rejected.support).toBe("control_lost");
  });

  it("marks a rejected request without granting control", () => {
    const requesting = reduceFtmsControl(capableState(), {
      type: "requestControlSent",
      generation: 1,
    });
    const rejected = reduceFtmsControl(requesting, {
      type: "responseReceived",
      generation: 1,
      response: response(FTMS_OPCODES.REQUEST_CONTROL, FTMS_RESULT_CODES.OPERATION_FAILED),
    });
    expect(rejected.support).toBe("control_rejected");
  });

  it("maps control-not-permitted request responses to control-lost", () => {
    const requesting = reduceFtmsControl(capableState(), {
      type: "requestControlSent",
      generation: 1,
    });
    const lost = reduceFtmsControl(requesting, {
      type: "responseReceived",
      generation: 1,
      response: response(FTMS_OPCODES.REQUEST_CONTROL, FTMS_RESULT_CODES.CONTROL_NOT_PERMITTED),
    });
    expect(lost.support).toBe("control_lost");
  });

  it("ignores a response from a stale generation", () => {
    const requesting = reduceFtmsControl(capableState(), {
      type: "requestControlSent",
      generation: 2,
    });
    const next = reduceFtmsControl(requesting, {
      type: "responseReceived",
      generation: 1,
      response: response(FTMS_OPCODES.REQUEST_CONTROL),
    });
    expect(next).toBe(requesting);
  });

  it("ignores a response for a mismatched opcode", () => {
    const pending = reduceFtmsControl(grantedState(), {
      type: "commandSent",
      opcode: FTMS_OPCODES.SET_TARGET_POWER,
      generation: 3,
      requestedMode: ControlMode.ERG,
    });
    const next = reduceFtmsControl(pending, {
      type: "responseReceived",
      generation: 3,
      response: response(FTMS_OPCODES.SET_TARGET_SPEED),
    });
    expect(next).toBe(pending);
  });

  it("ignores duplicate responses after an operation resolves", () => {
    const pending = reduceFtmsControl(grantedState(), {
      type: "commandSent",
      opcode: FTMS_OPCODES.SET_TARGET_POWER,
      generation: 3,
      requestedMode: ControlMode.ERG,
    });
    const completed = reduceFtmsControl(pending, {
      type: "responseReceived",
      generation: 3,
      response: response(FTMS_OPCODES.SET_TARGET_POWER),
    });
    const duplicate = reduceFtmsControl(completed, {
      type: "responseReceived",
      generation: 3,
      response: response(FTMS_OPCODES.SET_TARGET_POWER),
    });
    expect(duplicate).toBe(completed);
  });

  it("records an ordinary pending command without changing the active mode", () => {
    const state = reduceFtmsControl(grantedState(ControlMode.RESISTANCE), {
      type: "commandSent",
      opcode: FTMS_OPCODES.SET_TARGET_POWER,
      generation: 4,
      requestedMode: ControlMode.ERG,
    });
    expect(state).toMatchObject({
      support: "control_granted",
      currentMode: ControlMode.RESISTANCE,
      pending: { requestedMode: ControlMode.ERG },
    });
  });

  it("commits the requested mode only after command success", () => {
    const pending = reduceFtmsControl(grantedState(ControlMode.RESISTANCE), {
      type: "commandSent",
      opcode: FTMS_OPCODES.SET_TARGET_POWER,
      generation: 4,
      requestedMode: ControlMode.ERG,
    });
    const completed = reduceFtmsControl(pending, {
      type: "responseReceived",
      generation: 4,
      response: response(FTMS_OPCODES.SET_TARGET_POWER),
    });
    expect(completed.currentMode).toBe(ControlMode.ERG);
  });

  it("preserves the active mode after an ordinary command failure", () => {
    const pending = reduceFtmsControl(grantedState(ControlMode.RESISTANCE), {
      type: "commandSent",
      opcode: FTMS_OPCODES.SET_TARGET_POWER,
      generation: 4,
      requestedMode: ControlMode.ERG,
    });
    const failed = reduceFtmsControl(pending, {
      type: "responseReceived",
      generation: 4,
      response: response(FTMS_OPCODES.SET_TARGET_POWER, FTMS_RESULT_CODES.INVALID_PARAMETER),
    });
    expect(failed).toMatchObject({
      support: "control_granted",
      currentMode: ControlMode.RESISTANCE,
      pending: null,
    });
  });

  it("loses permission and mode after control-not-permitted on a command", () => {
    const pending = reduceFtmsControl(grantedState(ControlMode.ERG), {
      type: "commandSent",
      opcode: FTMS_OPCODES.SET_TARGET_POWER,
      generation: 5,
    });
    const lost = reduceFtmsControl(pending, {
      type: "responseReceived",
      generation: 5,
      response: response(FTMS_OPCODES.SET_TARGET_POWER, FTMS_RESULT_CODES.CONTROL_NOT_PERMITTED),
    });
    expect(lost).toMatchObject({ support: "control_lost", currentMode: null, pending: null });
  });

  it("invalidates permission and mode as soon as reset is sent", () => {
    const state = reduceFtmsControl(grantedState(ControlMode.ERG), {
      type: "commandSent",
      opcode: FTMS_OPCODES.RESET,
      generation: 6,
    });
    expect(state).toMatchObject({
      support: "control_lost",
      currentMode: null,
      pending: { reset: true },
    });
  });

  it("ends control-capable rather than granted after reset success", () => {
    const pending = reduceFtmsControl(grantedState(ControlMode.ERG), {
      type: "commandSent",
      opcode: FTMS_OPCODES.RESET,
      generation: 6,
    });
    const reset = reduceFtmsControl(pending, {
      type: "responseReceived",
      generation: 6,
      response: response(FTMS_OPCODES.RESET),
    });
    expect(reset).toMatchObject({
      support: "control_capable",
      currentMode: null,
      pending: null,
    });
  });

  it("does not reclaim permission after reset failure", () => {
    const pending = reduceFtmsControl(grantedState(ControlMode.ERG), {
      type: "commandSent",
      opcode: FTMS_OPCODES.RESET,
      generation: 6,
    });
    const failed = reduceFtmsControl(pending, {
      type: "responseReceived",
      generation: 6,
      response: response(FTMS_OPCODES.RESET, FTMS_RESULT_CODES.OPERATION_FAILED),
    });
    expect(failed).toMatchObject({ support: "control_lost", currentMode: null, pending: null });
  });

  it("marks a request timeout as rejected", () => {
    const requesting = reduceFtmsControl(capableState(), {
      type: "requestControlSent",
      generation: 8,
    });
    const timedOut = reduceFtmsControl(requesting, { type: "timeout", generation: 8 });
    expect(timedOut).toMatchObject({ support: "control_rejected", pending: null });
  });

  it("preserves granted state and mode after an ordinary command timeout", () => {
    const pending = reduceFtmsControl(grantedState(ControlMode.ERG), {
      type: "commandSent",
      opcode: FTMS_OPCODES.SET_TARGET_POWER,
      generation: 9,
    });
    const timedOut = reduceFtmsControl(pending, { type: "timeout", generation: 9 });
    expect(timedOut).toMatchObject({
      support: "control_granted",
      currentMode: ControlMode.ERG,
      pending: null,
    });
  });

  it("ignores a timeout from a stale generation", () => {
    const pending = reduceFtmsControl(grantedState(), {
      type: "commandSent",
      opcode: FTMS_OPCODES.SET_TARGET_POWER,
      generation: 10,
    });
    expect(reduceFtmsControl(pending, { type: "timeout", generation: 9 })).toBe(pending);
  });

  it("clears pending work and mode on permission-loss status", () => {
    const pending = reduceFtmsControl(grantedState(ControlMode.ERG), {
      type: "commandSent",
      opcode: FTMS_OPCODES.SET_TARGET_POWER,
      generation: 10,
    });
    const lost = reduceFtmsControl(pending, { type: "permissionLost" });
    expect(lost).toMatchObject({ support: "control_lost", pending: null, currentMode: null });
  });

  it("clears pending work and mode on disconnect", () => {
    const pending = reduceFtmsControl(grantedState(ControlMode.ERG), {
      type: "commandSent",
      opcode: FTMS_OPCODES.SET_TARGET_POWER,
      generation: 10,
    });
    const lost = reduceFtmsControl(pending, { type: "disconnected" });
    expect(lost).toMatchObject({ support: "control_lost", pending: null, currentMode: null });
  });

  it("moves to a terminal disposed state", () => {
    const disposed = reduceFtmsControl(grantedState(ControlMode.ERG), { type: "disposed" });
    expect(disposed).toEqual({
      support: "metrics_only",
      pending: null,
      currentMode: null,
      disposed: true,
    });
  });

  it("ignores all later events after disposal", () => {
    const disposed = reduceFtmsControl(grantedState(), { type: "disposed" });
    expect(reduceFtmsControl(disposed, { type: "capabilityDiscovered" })).toBe(disposed);
  });

  it("preserves the mode after successful commands that do not request a mode", () => {
    const pending = reduceFtmsControl(grantedState(ControlMode.ERG), {
      type: "commandSent",
      opcode: FTMS_OPCODES.START_RESUME,
      generation: 11,
    });
    const completed = reduceFtmsControl(pending, {
      type: "responseReceived",
      generation: 11,
      response: response(FTMS_OPCODES.START_RESUME),
    });
    expect(completed.currentMode).toBe(ControlMode.ERG);
  });
});
