#!/usr/bin/env python3
"""Conservative, credential-free CI selection from a NUL-delimited git diff."""
import argparse
import json
import subprocess

PORTS = ("typescript", "c", "kotlin", "rust", "swift", "python")


def select(paths, force=False):
    selected = dict.fromkeys((*PORTS, "docs"), force)
    for path in paths:
        if path.startswith(("shared/", ".github/", "tools/")):
            return dict.fromkeys(selected, True)
        if path.startswith("packages/"):
            port = path.split("/")[1]
            if port not in PORTS:
                return dict.fromkeys(selected, True)
            selected[port] = True
            # Site content/link checks consume package docs and TypeDoc source.
            selected["docs"] = True
        elif path.startswith(("docs/", "site/")) or path.endswith(".md"):
            selected["docs"] = True
        elif path == "Package.swift":
            selected["swift"] = True
            selected["docs"] = True
        else:
            # Shared contracts, workflows, tools, lockfiles, root configuration,
            # examples and unknown paths conservatively invalidate every lane.
            return dict.fromkeys(selected, True)
    return selected


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    force = args.all or not args.base or set(args.base) == {"0"}
    paths = []
    if not force:
        # Missing history must not cause verification to be skipped.
        diff = subprocess.run(
            ["git", "diff", "--name-only", "--no-renames", "-z", args.base, args.head],
            capture_output=True, check=False,
        )
        force = diff.returncode != 0
        paths = diff.stdout.decode("utf-8", errors="replace").strip("\0").split("\0") if diff.stdout else []
    for key, value in select(paths, force).items():
        print(f"{key}={json.dumps(value)}")
