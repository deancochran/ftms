"""Synthetic host tests, not captures or evidence for any trainer."""
import json
import subprocess
import sys

program = sys.argv[1]


def run(*args):
    return subprocess.run([program, *args], capture_output=True, text=True, check=False)


packet = run("4400d204b400fa00")
assert packet.returncode == 0, packet.stderr
result = json.loads(packet.stdout)
values = [0] * 30
values[0], values[28], values[17] = 1234, 180, 250
assert result == {
    "flags": 68, "present": (1 << 0) | (1 << 28) | (1 << 17),
    "unavailable": 0, "moreData": 0, "truncated": 0,
    "trailingBytes": 0, "reservedFlags": 0, "bytesRead": 8, "values": values,
}
assert run("").returncode == 2
assert run("0").returncode == 64
assert run("zz").returncode == 64
assert run("00" * 513).returncode == 64
assert run("0100", "auto").returncode == 64
assert run("4400d204b400").returncode == 2
assert run("0100").returncode == 0  # More Data is not itself malformed.
assert run("2100f4ff", "signed16Tenths").returncode == 0
assert run("2100f4ff", "uint8Whole").returncode == 2  # Trailing bytes, no guessing.
print("offline replay synthetic boundaries passed (no hardware)")
