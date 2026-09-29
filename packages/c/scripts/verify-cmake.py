#!/usr/bin/env python3
"""Build, install, relocate, and consume the CMake package without SDKs."""

from __future__ import annotations

import os
import pathlib
import shutil
import shlex
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT


def run(args: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", shlex.join(args))
    subprocess.run(args, check=True, env=env)


def cmake() -> str:
    configured = os.environ.get("CMAKE")
    if configured:
        return configured
    found = shutil.which("cmake")
    if not found:
        raise RuntimeError("set CMAKE to a CMake executable or add cmake to PATH")
    return found


def write_installed_consumer(directory: pathlib.Path) -> None:
    directory.mkdir()
    (directory / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.16)\n"
        "project(ftms_installed_consumer LANGUAGES C CXX)\n"
        f"find_package(ftms {(ROOT / 'VERSION').read_text().strip()} CONFIG REQUIRED)\n"
        "add_executable(c_consumer c_consumer.c)\n"
        "target_link_libraries(c_consumer PRIVATE ftms::ftms)\n"
        "add_executable(cxx_consumer cxx_consumer.cpp)\n"
        "target_link_libraries(cxx_consumer PRIVATE ftms::ftms)\n")
    shutil.copy2(ROOT / "tests" / "consumer.c", directory / "c_consumer.c")
    shutil.copy2(ROOT / "tests" / "consumer.cpp", directory / "cxx_consumer.cpp")


def verify_compiler(cmake_exe: str, cc: str, cxx: str, temporary: pathlib.Path) -> None:
    build = temporary / f"build-{cc}"
    install = temporary / f"prefix {cc}"
    relocated = temporary / f"relocated prefix {cc}"
    run([cmake_exe, "-S", str(SOURCE), "-B", str(build), "-G", "Ninja",
         f"-DCMAKE_C_COMPILER={cc}",
         f"-DCMAKE_INSTALL_PREFIX={install}", "-DCMAKE_INSTALL_LIBDIR=lib"])
    run([cmake_exe, "--build", str(build), "--parallel"])
    run([cmake_exe, "--install", str(build)])
    shutil.move(str(install), str(relocated))

    consumer = temporary / f"consumer {cc}"
    write_installed_consumer(consumer)
    consumer_build = temporary / f"consumer build {cc}"
    run([cmake_exe, "-S", str(consumer), "-B", str(consumer_build), "-G", "Ninja",
         f"-DCMAKE_PREFIX_PATH={relocated}", f"-DCMAKE_C_COMPILER={cc}",
         f"-DCMAKE_CXX_COMPILER={cxx}"])
    run([cmake_exe, "--build", str(consumer_build), "--parallel"])
    run([str(consumer_build / "c_consumer")])
    run([str(consumer_build / "cxx_consumer")])

    pkg_config = shutil.which("pkg-config")
    if not pkg_config:
        raise RuntimeError("pkg-config is required for this package verification")
    environment = os.environ.copy()
    environment["PKG_CONFIG_PATH"] = str(relocated / "lib" / "pkgconfig")
    flags = subprocess.check_output(
        [pkg_config, "--static", "--cflags", "--libs", "ftms"], text=True,
        env=environment).strip()
    command = [cc, str(ROOT / "tests" / "consumer.c"), *shlex.split(flags),
               "-o", str(temporary / f"pkg-config-consumer-{cc}")]
    run(command, env=environment)
    run([command[-1]], env=environment)


def main() -> int:
    cmake_exe = cmake()
    missing = [tool for tool in ("gcc", "g++", "clang", "clang++", "ninja", "pkg-config")
               if not shutil.which(tool)]
    if missing:
        print("missing required verification tools: " + ", ".join(missing), file=sys.stderr)
        return 2
    local_build = ROOT / "build" / "cmake-consumers"
    local_build.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ftms cmake-", dir=local_build) as work:
        temporary = pathlib.Path(work)
        # This builds the package as an add_subdirectory dependency without an install.
        run([cmake_exe, "-S", str(ROOT / "cmake" / "consumer"),
             "-B", str(temporary / "add-subdirectory"), "-G", "Ninja"])
        run([cmake_exe, "--build", str(temporary / "add-subdirectory"), "--parallel"])
        run([str(temporary / "add-subdirectory" / "ftms_add_subdirectory_consumer")])
        verify_compiler(cmake_exe, "gcc", "g++", temporary)
        verify_compiler(cmake_exe, "clang", "clang++", temporary)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print(f"verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
