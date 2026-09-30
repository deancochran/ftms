"""Plan a PyPI retry without accepting different immutable files."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

PACKAGE = "deancochran-ftms"


def plan(version: str, expected: dict[str, str], fetch: Callable[[str], bytes]) -> list[str]:
    try:
        data = json.loads(fetch(f"https://pypi.org/pypi/{PACKAGE}/{version}/json"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            error.close()
            return list(expected)
        raise
    remote = {x.get("filename"): x.get("digests", {}).get("sha256") for x in data.get("urls", [])}
    missing = []
    for name, digest in expected.items():
        if name not in remote:
            missing.append(name)
        elif remote[name] != digest:
            raise ValueError(f"existing PyPI artifact differs or lacks digest: {name}")
    return missing


def fetch_metadata(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return bytes(response.read())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--wheel-sha256", required=True)
    parser.add_argument("--sdist-sha256", required=True)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    expected = {
        f"deancochran_ftms-{args.version}-py3-none-any.whl": args.wheel_sha256,
        f"deancochran_ftms-{args.version}.tar.gz": args.sdist_sha256,
    }
    missing = plan(args.version, expected, fetch_metadata)
    for name, digest in expected.items():
        if hashlib.sha256((args.dist / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"local artifact differs: {name}")
    # Never let leftovers from a previous invocation expand the upload set.
    args.output.mkdir(parents=True, exist_ok=False)
    for name in missing:
        shutil.copyfile(args.dist / name, args.output / name)
    print(f"publish={'true' if missing else 'false'}")


if __name__ == "__main__":
    main()
