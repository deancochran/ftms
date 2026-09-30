#!/usr/bin/env python3
"""Package-local aggregate verification; never invokes repository-root tooling."""

from __future__ import annotations

import subprocess
from pathlib import Path

P = Path(__file__).resolve().parents[1]
COMMANDS = (
    ["uv", "run", "--locked", "--group", "dev", "ruff", "format", "--check", "."],
    ["uv", "run", "--locked", "--group", "dev", "ruff", "check", "."],
    ["uv", "run", "--locked", "--group", "dev", "mypy", "src", "tests", "scripts"],
    ["uv", "run", "--locked", "--group", "dev", "--python", "3.11", "pytest"],
    ["uv", "run", "--locked", "--group", "dev", "--python", "3.14", "pytest"],
    ["uv", "run", "--locked", "--group", "dev", "python", "scripts/run_features_conformance.py"],
    [
        "uv",
        "run",
        "--locked",
        "--group",
        "dev",
        "python",
        "scripts/run_measurement_status_conformance.py",
    ],
    ["uv", "run", "--locked", "--group", "dev", "python", "scripts/run_measurement_matrix.py"],
    ["uv", "run", "--locked", "--group", "dev", "python", "scripts/run_capability_conformance.py"],
    ["uv", "run", "--locked", "--group", "dev", "python", "scripts/verify_package.py"],
)


def main() -> int:
    for c in COMMANDS:
        subprocess.run(c, cwd=P, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
