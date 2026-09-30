#!/usr/bin/env python3
"""Exercise either an exact .crate archive or an exact public registry version.

Host verification tooling only, excluded from the published Rust library.
The temporary consumer has no access to canonical repository fixtures.
"""

import argparse
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import tomllib

import release


def verify(archive=None, registry_version=None, allow_dirty=False):
    with tempfile.TemporaryDirectory(prefix="ftms-rust-consumer-") as directory:
        root = Path(directory)
        env = release.public_env()
        env["CARGO_TARGET_DIR"] = str(root / "target")
        if registry_version is not None:
            release.require_version(registry_version)
            # Proves public installation, not reuse of a path dependency/cache.
            env["CARGO_HOME"] = str(root / "cargo-home")
            env.pop("CARGO_NET_OFFLINE", None)
            dependency = f'ftms = "={registry_version}"'
        else:
            if archive is None:
                archive = release.package(root / "package-target", allow_dirty)
            archive = Path(archive).resolve()
            identity = release.inspect_archive(archive)
            with tarfile.open(archive, "r:gz") as tar:
                # Inspection rejects traversal, links, duplicates and oversized
                # members. Use data filtering too on our Python >=3.12 CI.
                tar.extractall(root, filter="data")
            source = root / f'{identity["name"]}-{identity["version"]}'
            dependency = f'ftms = {{ path = {json.dumps(source.as_posix())} }}'
        consumer = root / "consumer"
        (consumer / "src").mkdir(parents=True)
        (consumer / "Cargo.toml").write_text(
            '[package]\nname = "ftms-consumer-check"\nversion = "0.0.0"\n'
            'edition = "2021"\n\n[dependencies]\n' + dependency + "\n",
            encoding="utf-8",
        )
        shutil.copyfile(release.PACKAGE / "tests/fixtures/consumer.rs", consumer / "src/main.rs")
        manifest = str(consumer / "Cargo.toml")
        release.run(["cargo", "generate-lockfile", "--manifest-path", manifest], env=env)
        release.run(["cargo", "run", "--locked", "--manifest-path", manifest], env=env)
        lock = tomllib.loads((consumer / "Cargo.lock").read_text(encoding="utf-8"))
        ftms = [p for p in lock["package"] if p["name"] == "ftms"]
        if len(ftms) != 1:
            raise release.ReleaseError("consumer did not install exactly one ftms crate")
        if registry_version is not None and (
            ftms[0]["version"] != registry_version
            or ftms[0].get("source") != "registry+https://github.com/rust-lang/crates.io-index"
        ):
            raise release.ReleaseError("consumer did not install the requested public registry version")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--archive", type=Path)
    mode.add_argument("--registry-version")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    verify(args.archive, args.registry_version, args.allow_dirty)
