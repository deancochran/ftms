#!/usr/bin/env python3
"""Execute the shared measurement-matrix structural contract without copied layouts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from deancochran_ftms import (
    MeasurementFormatOptions,
    MeasurementRaw,
    RawCodecError,
    decode_measurement_raw,
    encode_measurement_raw,
)

P = Path(__file__).resolve().parents[1]
R = P.parents[1]
M = R / "shared/conformance/measurement-matrix/v1"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    x = json.loads((M / "layouts.json").read_text())
    counts = {
        "structural": 0,
        "sentinel": 0,
        "rfu": 0,
        "prefix": 0,
        "decodeAssertions": 0,
        "encodeAssertions": 0,
    }
    errors: list[str] = []
    try:
        for layout in x["layouts"]:
            for variant in range(2 if layout["kind"] in (0, 1, 4, 5) else 1):
                o = MeasurementFormatOptions(
                    "signed16Tenths" if variant and layout["kind"] else "uint8Whole",
                    "uint8Legacy" if variant and layout["kind"] == 0 else "uint16",
                )
                fs = [(a, b, c, d, e) for a, b, c, d, e in layout["fields"]]

                def build(flags: int, sentinel: int = -1) -> tuple[bytes, MeasurementRaw]:
                    out = bytearray(flags.to_bytes(layout["flagBytes"], "little"))
                    values = [0] * 30
                    present = unavailable = 0
                    for bit, w, f, s, u in fs:
                        if bit == 0 and flags & 1 or bit and not flags & (1 << bit):
                            continue
                        if variant and f == 21:
                            w, s = 2, 1
                        if variant and layout["kind"] == 0 and f in (7, 8):
                            w = 1
                        v = (
                            (0x7FFF if s else (1 << (8 * w)) - 1)
                            if f == sentinel
                            else (f + 1) * (-1 if s else 1)
                        )
                        values[f] = 0 if f == sentinel else v
                        present |= 1 << f
                        unavailable |= (1 << f) if f == sentinel else 0
                        out.extend(v.to_bytes(w, "little", signed=bool(s)))
                    return bytes(out), MeasurementRaw(
                        layout["kind"],
                        flags,
                        present,
                        unavailable,
                        tuple(values),
                        flags & 1,
                        int(layout["kind"] == 1 and bool(flags & 0x8000)),
                        0,
                        0,
                        0,
                        len(out),
                    )

                def check(flags: int, sentinel: int = -1) -> None:
                    b, e = build(flags, sentinel)
                    d = decode_measurement_raw(b, layout["kind"], o)
                    if d != e:
                        raise AssertionError(f"decode {layout['kind']} {flags}")
                    if encode_measurement_raw(e, o) != b:
                        raise AssertionError(f"encode {layout['kind']} {flags}")
                    counts["decodeAssertions"] += 1
                    counts["encodeAssertions"] += 1

                for subset in range(1 << layout["optionalGroups"]):
                    for more in range(2):
                        for backward in range(2 if layout["kind"] == 1 else 1):
                            check((subset << 1) | more | (backward << 15))
                            counts["structural"] += 1
                all_flags = ((1 << layout["optionalGroups"]) - 1) << 1
                for _, _, f, _, u in fs:
                    if u:
                        check(all_flags, f)
                        counts["sentinel"] += 1
                full, _ = build(all_flags)
                for n in range(len(full)):
                    if n < layout["flagBytes"]:
                        try:
                            decode_measurement_raw(full[:n], layout["kind"], o)
                            raise AssertionError("short flags accepted")
                        except RawCodecError:
                            pass
                    elif not decode_measurement_raw(full[:n], layout["kind"], o).truncated:
                        raise AssertionError("prefix not truncated")
                    counts["prefix"] += 1
                for bit in range(
                    16 if layout["kind"] == 1 else layout["optionalGroups"] + 1,
                    layout["flagBytes"] * 8,
                ):
                    b, e = build(all_flags | (1 << bit))
                    d = decode_measurement_raw(b, layout["kind"], o)
                    if not d.reserved_flags:
                        raise AssertionError("rfu unmarked")
                    try:
                        encode_measurement_raw(e, o)
                        raise AssertionError("rfu encoded")
                    except RawCodecError:
                        pass
                    counts["rfu"] += 1
        if counts["structural"] != 181760 or counts["sentinel"] != 46 or counts["rfu"] != 47:
            raise AssertionError(str(counts))
    except Exception as e:
        errors.append(f"{type(e).__name__}: {e}")
    report = {
        "contract": x["contract"],
        "sourceCommit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=R, text=True
        ).strip(),
        "dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=R, text=True).strip()
        ),
        "counts": counts,
        "sha256": {str(q.relative_to(R)): sha(q) for q in (M / "layouts.json", M / "README.md")},
        "errors": errors,
        "complete": not errors,
    }
    (P / "build").mkdir(exist_ok=True)
    out = P / "build/measurement-matrix-verification-report.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"complete": report["complete"], "counts": counts, "report": str(out)}))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
