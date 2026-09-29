"""Generate deterministic independent expectations; no production table imports."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
contract = json.loads((ROOT / "shared/conformance/measurement-matrix/v1/layouts.json").read_text())
assert contract["contract"] == "ftms-measurement-matrix-v1"
counts = {"subsets": 0, "sentinels": 0, "reserved": 0, "full": 0}
with tempfile.TemporaryFile(mode="w+") as inputs:
    for layout in contract["layouts"]:
        kind = layout["kind"]
        for variant in range(2 if kind in (0, 1, 4, 5) else 1):
            fields = []
            for bit, width, field, signed, sentinel in layout["fields"]:
                if variant and field == 21:
                    width, signed = 2, 1
                if variant and kind == 0 and field in (7, 8):
                    width = 1
                fields.append((bit, width, field, signed, sentinel))

            def emit(flags, category, sentinel_field=-1, minimum_budget=0):
                values = [0] * 30
                present = unavailable = 0
                payload = bytearray(flags.to_bytes(layout["flagBytes"], "little"))
                for bit, width, field, signed, _ in fields:
                    if (flags & 1) if bit == 0 else not (flags & (1 << bit)):
                        continue
                    is_sentinel = field == sentinel_field
                    value = ((32767 if signed else (1 << (width * 8)) - 1)
                             if is_sentinel else (field + 1) * (-1 if signed else 1))
                    values[field] = 0 if is_sentinel else value
                    present |= 1 << field
                    if is_sentinel:
                        unavailable |= 1 << field
                    payload.extend(value.to_bytes(width, "little", signed=bool(signed)))
                header = [kind, int(bool(variant and kind != 0)), int(bool(variant and kind == 0)),
                          int(category == "reserved"), minimum_budget, len(payload), flags, present, unavailable]
                inputs.write(" ".join(map(str, header + values)) + " " + payload.hex() + "\n")
                counts[category] += 1

            for subset in range(1 << layout["optionalGroups"]):
                for more in range(2):
                    for backward in range(2 if kind == 1 else 1):
                        emit((subset << 1) | more | (backward << 15), "subsets")
            full_flags = ((1 << layout["optionalGroups"]) - 1) << 1
            for _, _, field, _, sentinel in fields:
                if sentinel:
                    emit(full_flags, "sentinels", field)
            for bit in range(16 if kind == 1 else layout["optionalGroups"] + 1, layout["flagBytes"] * 8):
                emit(full_flags | (1 << bit), "reserved")
            groups = {}
            for bit, width, *_ in fields:
                groups[bit] = groups.get(bit, 0) + width
            emit(full_flags, "full", minimum_budget=layout["flagBytes"] + max(groups.values()))
    assert counts == {"subsets": 181760, "sentinels": 46, "reserved": 47, "full": 10}, counts
    inputs.seek(0)
    subprocess.run([sys.argv[1]], stdin=inputs, check=True)
print("Independent generated input accounting:", counts)
