#!/usr/bin/env python3
"""Require positive success for selected jobs, including runner-abandonment cases."""
import json
import os

JOBS = {
    "typescript": "verify", "c": "c", "kotlin": "kotlin", "rust": "rust",
    "swift": "swift", "python": "python", "csharp": "csharp", "dart": "dart",
    "go": "go", "docs": "docs",
}


def validate(needs):
    expected = {"changes", "workflow-lint", *JOBS.values()}
    if not isinstance(needs, dict) or set(needs) != expected:
        raise ValueError("Missing or unexpected CI dependencies")
    for name, job in needs.items():
        if not isinstance(job, dict) or job.get("result") not in {"success", "skipped"}:
            raise ValueError(f"CI job did not succeed: {name}")
    for name in ("changes", "workflow-lint"):
        if needs[name]["result"] != "success":
            raise ValueError(f"Required CI job was skipped: {name}")
    outputs = needs["changes"].get("outputs", {})
    for port, job in JOBS.items():
        selected = outputs.get(port)
        if selected not in {"true", "false"}:
            raise ValueError(f"Missing or invalid selection for {port}")
        if selected == "true" and needs[job]["result"] != "success":
            raise ValueError(f"Selected CI job was skipped: {job}")


if __name__ == "__main__":
    try:
        validate(json.loads(os.environ["CI_NEEDS"]))
    except (KeyError, ValueError, TypeError) as error:
        raise SystemExit(str(error)) from error
    print("All selected CI jobs explicitly succeeded.")
