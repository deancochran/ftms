#!/usr/bin/env python3
"""Verify locally installed recipes. No publishing or registry submission."""
import argparse
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]


def run(*args, env):
    print("+", *map(str, args), flush=True)
    subprocess.run(list(map(str, args)), check=True, env=env)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--conan", help="Conan 2 executable")
    parser.add_argument("--vcpkg", help="bootstrapped vcpkg executable")
    args = parser.parse_args()
    if not args.conan and not args.vcpkg:
        parser.error("select --conan and/or --vcpkg; missing tools are not passing tests")
    spec = importlib.util.spec_from_file_location("bundle", PACKAGE / "scripts/source-bundle.py")
    bundle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bundle)
    identity = bundle.verify(args.archive)
    archive = args.archive.resolve()
    cmake = os.environ.get("CMAKE") or shutil.which("cmake")
    if not cmake:
        raise RuntimeError("CMake must be on PATH or in CMAKE")
    ctest = str(Path(shutil.which(cmake) or cmake).with_name("ctest.exe" if os.name == "nt" else "ctest"))
    root = PACKAGE / "build"
    root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="package-managers-", dir=root) as directory:
        work = Path(directory)
        env = dict(os.environ)
        env["PATH"] = str(Path(shutil.which(cmake) or cmake).parent) + os.pathsep + env["PATH"]
        if args.conan:
            env["CONAN_HOME"] = str(work / "conan-home")
            run(args.conan, "profile", "detect", env=env)
            with tarfile.open(archive) as tar:
                for member in tar.getmembers():
                    dest = work / member.name
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(tar.extractfile(member).read())
            source = work / f"ftms-c-{identity['packageVersion']}"
            run(args.conan, "create", source, "--no-remote", "--test-folder", PACKAGE / "test_package", env=env)
        if args.vcpkg:
            manifest = PACKAGE / "packaging/vcpkg/ftms/vcpkg.json"
            import json
            if json.loads(manifest.read_text())["version-semver"] != identity["packageVersion"]:
                raise ValueError("overlay manifest version must match archive")
            env.update(FTMS_SOURCE_ARCHIVE=str(archive),
                       FTMS_SOURCE_ARCHIVE_SHA512=hashlib.sha512(archive.read_bytes()).hexdigest(),
                       VCPKG_DISABLE_METRICS="1", VCPKG_BINARY_SOURCES="clear")
            installed = work / "installed"
            # This verification intentionally targets the host Linux compiler;
            # other triplets are covered by standalone platform consumers first.
            run(args.vcpkg, "install", "ftms:x64-linux", "--classic",
                f"--overlay-ports={PACKAGE / 'packaging/vcpkg'}", f"--x-install-root={installed}", env=env)
            build = work / "vcpkg-consumer"
            run(cmake, "-S", PACKAGE / "test_package", "-B", build, "-DCMAKE_BUILD_TYPE=Release",
                f"-DCMAKE_PREFIX_PATH={installed / 'x64-linux'}", env=env)
            run(cmake, "--build", build, "--config", "Release", env=env)
            run(ctest, "--test-dir", build, "--build-config", "Release", "--output-on-failure", "--no-tests=error", env=env)
    print("Selected package managers passed with actual installed C and C++ consumers")


if __name__ == "__main__":
    main()
