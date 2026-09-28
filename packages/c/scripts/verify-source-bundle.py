#!/usr/bin/env python3
"""Build real consumers of an exact extracted artifact, including multi-config generators."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[1]
SOURCE = PACKAGE / "scripts/source-bundle.py"
BODY = """#include <ftms/ftms.h>
int main(void) {
  const unsigned char bytes[8] = {1, 0, 0, 0, 2, 0, 0, 0};
  ftms_features value;
  return ftms_decode_features(bytes, sizeof bytes, &value) != FTMS_OK ||
         value.machine != 1 || value.target != 2;
}
"""


def run(*args):
    print("+", *map(str, args), flush=True)
    subprocess.run(list(map(str, args)), check=True)


def tools():
    cmake = os.environ.get("CMAKE") or shutil.which("cmake")
    if not cmake:
        candidate = Path("/opt/android-sdk/cmake/3.22.1/bin/cmake")
        if candidate.is_file():
            cmake = str(candidate)
    if not cmake:
        raise RuntimeError("CMake is required; set CMAKE or add it to PATH")
    resolved = Path(shutil.which(cmake) or cmake)
    suffix = ".exe" if os.name == "nt" else ""
    ctest = resolved.with_name("ctest" + suffix)
    if not ctest.is_file():
        raise RuntimeError("CTest is required beside CMake")
    return str(resolved), str(ctest)


def consume(directory, prelude, cmake, ctest, *options):
    directory.mkdir()
    (directory / "main.c").write_text(BODY)
    (directory / "main.cpp").write_text(BODY)
    (directory / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.16)\nproject(consumer LANGUAGES C CXX)\n"
        + prelude + "\nenable_testing()\n"
        "add_executable(consumer_c main.c)\n"
        "target_link_libraries(consumer_c PRIVATE ftms::ftms)\n"
        "add_executable(consumer_cpp main.cpp)\n"
        "target_compile_features(consumer_cpp PRIVATE cxx_std_11)\n"
        "target_link_libraries(consumer_cpp PRIVATE ftms::ftms)\n"
        "add_test(NAME c_consumer COMMAND consumer_c)\n"
        "add_test(NAME cpp_consumer COMMAND consumer_cpp)\n"
    )
    build = directory / "build"
    run(cmake, "-S", directory, "-B", build, "-DCMAKE_BUILD_TYPE=Release", *options)
    run(cmake, "--build", build, "--config", "Release")
    run(ctest, "--test-dir", build, "--build-config", "Release", "--output-on-failure", "--no-tests=error")


def consume_example(directory, prefix, cmake, ctest):
    shutil.copytree(ROOT / "examples" / "c-client", directory)
    build = directory / "build"
    run(cmake, "-S", directory, "-B", build, "-DCMAKE_BUILD_TYPE=Release",
        f"-DCMAKE_PREFIX_PATH={prefix}")
    run(cmake, "--build", build, "--config", "Release")
    run(ctest, "--test-dir", build, "--build-config", "Release", "--output-on-failure", "--no-tests=error")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, help="consume this exact archive without rebuilding it")
    args = parser.parse_args()
    cmake, ctest = tools()
    build_root = PACKAGE / "build"
    build_root.mkdir(exist_ok=True)
    if args.archive:
        archive = args.archive.resolve()
    else:
        run(sys.executable, SOURCE)
        version = (PACKAGE / "VERSION").read_text().strip()
        archive = build_root / "source-candidate" / f"ftms-c-{version}.tar.gz"
        first = archive.read_bytes()
        run(sys.executable, SOURCE)
        if first != archive.read_bytes():
            raise RuntimeError("source archive is not deterministic")
    run(sys.executable, SOURCE, "--verify", archive)
    before = hashlib.sha256(archive.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="artifact consumers ", dir=build_root) as temporary:
        temp = Path(temporary)
        with tarfile.open(archive) as bundle:
            # Source verification has already rejected non-files and unsafe paths.
            for member in bundle.getmembers():
                destination = temp / member.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(bundle.extractfile(member).read())
        source = temp / archive.name.removesuffix(".tar.gz")
        prefix = temp / "installed prefix"
        build = temp / "library build"
        run(cmake, "-S", source, "-B", build, f"-DCMAKE_INSTALL_PREFIX={prefix}",
            "-DCMAKE_BUILD_TYPE=Release", "-DFTMS_WARNINGS_AS_ERRORS=ON")
        run(cmake, "--build", build, "--config", "Release")
        run(cmake, "--install", build, "--config", "Release")
        relocated = temp / "relocated prefix"
        shutil.move(prefix, relocated)
        version = (source / "VERSION").read_text().strip()
        consume(temp / "installed consumer", f"find_package(ftms {version} EXACT CONFIG REQUIRED)",
                cmake, ctest, f"-DCMAKE_PREFIX_PATH={relocated}")
        consume_example(temp / "installed example", relocated, cmake, ctest)
        consume(temp / "vendored consumer", f'add_subdirectory("{source.as_posix()}" ftms-build)', cmake, ctest)
        consume(temp / "fetched consumer",
                'include(FetchContent)\nFetchContent_Declare(ftms\n'
                f'  URL "{archive.resolve().as_uri()}"\n  URL_HASH SHA256={before})\n'
                'FetchContent_MakeAvailable(ftms)', cmake, ctest)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != before:
        raise RuntimeError("verification changed the release artifact")
    print("Exact source artifact: 6 C/C++ consumers plus the installed C example passed across install, vendoring and FetchContent")


if __name__ == "__main__":
    main()
