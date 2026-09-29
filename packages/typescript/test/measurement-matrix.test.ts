import { deepStrictEqual, equal, throws } from "node:assert/strict";
import { it } from "vitest";
import matrix from "../../../shared/conformance/measurement-matrix/v1/layouts.json" with {
  type: "json",
};
import { decodeFtmsMeasurementRaw, encodeFtmsMeasurementRaw } from "../src/parsers.js";
import type { FtmsMeasurementFormatOptions } from "../src/types.js";

it("enumerates every optional-group subset, More Data state, direction and supported layout", () => {
  let count = 0;
  let sentinels = 0;
  let reserved = 0;
  for (const layout of matrix.layouts) {
    for (let variant = 0; variant < ([0, 1, 4, 5].includes(layout.kind) ? 2 : 1); variant++) {
      const options: FtmsMeasurementFormatOptions = {
        resistanceFormat: variant && layout.kind !== 0 ? "signed16Tenths" : "uint8Whole",
        treadmillPaceFormat: variant && layout.kind === 0 ? "uint8Legacy" : "uint16",
      };
      const fields = layout.fields.map(
        ([bit = 0, width = 0, field = 0, signed = 0, sentinel = 0]) => ({
          bit,
          field,
          sentinel,
          width:
            variant && field === 21
              ? 2
              : variant && layout.kind === 0 && [7, 8].includes(field)
                ? 1
                : width,
          signed: variant && field === 21 ? 1 : signed,
        }),
      );
      const build = (flags: number, sentinelField = -1) => {
        const bytes: number[] = Array.from(
          { length: layout.flagBytes },
          (_, i) => (flags >>> (i * 8)) & 255,
        );
        const values = Array<number>(30).fill(0);
        let present = 0;
        let unavailable = 0;
        for (const f of fields) {
          if (f.bit === 0 ? flags & 1 : !(flags & (1 << f.bit))) continue;
          const value =
            f.field === sentinelField
              ? f.signed
                ? 32767
                : 2 ** (8 * f.width) - 1
              : (f.field + 1) * (f.signed ? -1 : 1);
          // Comparison contract canonicalizes unavailable values to zero;
          // their sentinel bytes are represented by the unavailable mask.
          values[f.field] = f.field === sentinelField ? 0 : value;
          present += 2 ** f.field;
          if (f.field === sentinelField) unavailable += 2 ** f.field;
          for (let i = 0; i < f.width; i++) bytes.push((value >>> (i * 8)) & 255);
        }
        return {
          bytes: Uint8Array.from(bytes),
          expected: {
            kind: layout.kind,
            flags,
            present,
            unavailable,
            values,
            moreData: flags & 1,
            backward: layout.kind === 1 ? (flags >>> 15) & 1 : 0,
            truncated: 0,
            trailingBytes: 0,
            reservedFlags: 0,
            bytesRead: bytes.length,
          },
        };
      };
      const check = (flags: number, sentinelField = -1) => {
        const { bytes, expected } = build(flags, sentinelField);
        deepStrictEqual(decodeFtmsMeasurementRaw(layout.kind, bytes, options), expected);
        deepStrictEqual(encodeFtmsMeasurementRaw(expected, options), bytes);
      };
      for (let subset = 0; subset < 2 ** layout.optionalGroups; subset++) {
        for (let more = 0; more < 2; more++) {
          for (let backward = 0; backward < (layout.kind === 1 ? 2 : 1); backward++) {
            check((subset << 1) | more | (backward << 15));
            count++;
          }
        }
      }
      const all = (2 ** layout.optionalGroups - 1) << 1;
      for (const f of fields.filter((f) => f.sentinel)) {
        check(all, f.field);
        sentinels++;
      }
      const full = build(all);
      equal(full.bytes.length, layout.fullLength + (variant ? (layout.kind === 0 ? -2 : 1) : 0));
      for (let length = 0; length < full.bytes.length; length++) {
        const bytes = full.bytes.slice(0, length);
        if (length < layout.flagBytes)
          throws(() => decodeFtmsMeasurementRaw(layout.kind, bytes, options));
        else equal(decodeFtmsMeasurementRaw(layout.kind, bytes, options).truncated, 1);
      }
      for (
        let bit = layout.kind === 1 ? 16 : layout.optionalGroups + 1;
        bit < layout.flagBytes * 8;
        bit++
      ) {
        const test = build(all | (1 << bit));
        deepStrictEqual(decodeFtmsMeasurementRaw(layout.kind, test.bytes, options), {
          ...test.expected,
          reservedFlags: 1,
        });
        throws(() => encodeFtmsMeasurementRaw(test.expected, options));
        reserved++;
      }
    }
  }
  equal(count, 181760);
  equal(sentinels, 46);
  equal(reserved, 47);
}, 30000);
