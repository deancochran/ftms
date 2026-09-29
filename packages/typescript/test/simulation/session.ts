import { decodeFtmsMeasurementRaw, encodeFtmsMeasurementRaw } from "../../src/parsers.js";
import type { FtmsMeasurementRaw } from "../../src/types.js";

export type SimulationStatus = "pending" | "complete" | "invalid" | "expired" | "generation";
export type SimulationProfile = {
  kind: number;
  maxAge: number;
  format: { resistance: 0 | 1; pace: 0 | 1 };
};
type Result = { status: SimulationStatus; raw?: FtmsMeasurementRaw };

/** Test-only conceptual model: accepted decoded fragments are reduced only at finalization. */
export class SimulationSession {
  readonly #profile: SimulationProfile;
  #generation: number;
  #startedAt: number | undefined;
  #fragments: FtmsMeasurementRaw[] = [];
  constructor(profile: SimulationProfile, generation: number) {
    this.#profile = { kind: profile.kind, maxAge: profile.maxAge, format: { ...profile.format } };
    this.#generation = generation >>> 0;
  }
  reset(): SimulationStatus {
    this.#startedAt = undefined;
    this.#fragments = [];
    return "pending";
  }
  reconnect(generation: number): SimulationStatus {
    this.reset();
    this.#generation = generation >>> 0;
    return "pending";
  }
  feed(bytes: readonly number[], generation: number, at: number): Result {
    if (generation >>> 0 !== this.#generation) {
      this.reset();
      return { status: "generation" };
    }
    const now = at >>> 0;
    if (this.#startedAt !== undefined && (now - this.#startedAt) >>> 0 >= this.#profile.maxAge) {
      this.reset();
      return { status: "expired" };
    }
    let fragment: FtmsMeasurementRaw;
    try {
      const options = {
        resistanceFormat: this.#profile.format.resistance ? "signed16Tenths" : "uint8Whole",
        treadmillPaceFormat: this.#profile.format.pace ? "uint8Legacy" : "uint16",
      } as const;
      fragment = decodeFtmsMeasurementRaw(this.#profile.kind, Uint8Array.from(bytes), options);
      const canonical = encodeFtmsMeasurementRaw(fragment, options);
      if (
        canonical.length !== bytes.length ||
        canonical.some((value, index) => value !== bytes[index])
      ) {
        this.reset();
        return { status: "invalid" };
      }
    } catch {
      this.reset();
      return { status: "invalid" };
    }
    if (fragment.truncated || fragment.trailingBytes || fragment.reservedFlags) {
      this.reset();
      return { status: "invalid" };
    }
    const prior = this.#fragments;
    if (
      prior.some((p) => p.backward !== fragment.backward || (p.present & fragment.present) !== 0)
    ) {
      this.reset();
      return { status: "invalid" };
    }
    if (fragment.moreData) {
      if (!prior.length) this.#startedAt = now;
      prior.push(fragment);
      return { status: "pending" };
    }
    // A final fragment need only contain that measurement family's mandatory fields.
    // The decoder's present bitmap is authoritative; mandatory bit zero is treadmill/bike only.
    const mandatory: readonly number[] = [1, 1, 0x1800000, 0x800000, 0x6000000, 1];
    const mandatoryFields = mandatory[this.#profile.kind] ?? 0;
    if (prior.length && (fragment.present & mandatoryFields) !== mandatoryFields) {
      this.reset();
      return { status: "invalid" };
    }
    if (!prior.length) return { status: "complete", raw: fragment };
    const all = [...prior, fragment];
    const values = Array(30).fill(0);
    let present = 0,
      unavailable = 0,
      flags = 0;
    for (const part of all) {
      flags |= part.flags;
      present |= part.present;
      unavailable |= part.unavailable;
      for (let field = 0; field < 30; field++)
        if (part.present & (1 << field)) values[field] = part.values[field] ?? 0;
    }
    this.reset();
    return {
      status: "complete",
      raw: {
        ...fragment,
        flags: flags & ~1,
        present,
        unavailable,
        values,
        moreData: 0,
        bytesRead: 0,
      },
    };
  }
}
