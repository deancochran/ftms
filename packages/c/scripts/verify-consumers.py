#!/usr/bin/env python3
"""Verify real Make installation and C/C++ consumers from isolated prefixes."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
BUILD = PACKAGE / "build" / "consumers"
CFLAGS = ["-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Wconversion", "-Wsign-conversion", "-Werror"]
CXXFLAGS = ["-std=c++11", "-Wall", "-Wextra", "-Wpedantic", "-Wconversion", "-Wsign-conversion", "-Werror", "-fno-exceptions", "-fno-rtti"]


def run(command):
    print("+ " + " ".join(map(str, command)), flush=True)
    subprocess.run(command, check=True, cwd=PACKAGE)


def require(name):
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"required consumer verification tool is unavailable: {name}")
    return path


def main():
    try:
        c_compilers = [(name, require(name)) for name in ("gcc", "clang")]
        cpp_compilers = [(name, require(name)) for name in ("g++", "clang++")]
        make, ar = require("make"), require("ar")
    except RuntimeError as error:
        print("CONSUMER RUNNER ERROR: " + str(error), file=sys.stderr)
        return 2
    BUILD.mkdir(parents=True, exist_ok=True)
    # New paths make stale installed headers/objects unable to hide omissions.
    build = Path(tempfile.mkdtemp(prefix="install-", dir=BUILD))
    expected = {"include/ftms/" + path.name for path in (PACKAGE / "include/ftms").glob("*.h")}
    expected.add("lib/libftms.a")
    for c_name, compiler in c_compilers:
        stage = build / c_name / "stage"
        prefix = stage / "usr/local"
        objects = build / c_name / "objects"
        run([make, f"CC={compiler}", f"AR={ar}", f"BUILD={objects}",
             f"DESTDIR={stage}", "PREFIX=/usr/local", "install"])
        installed = {str(path.relative_to(prefix)) for path in prefix.rglob("*") if path.is_file()}
        if installed != expected:
            raise RuntimeError(f"installed file set differs: {installed ^ expected}")
        for header in (PACKAGE / "include/ftms").glob("*.h"):
            if header.read_bytes() != (prefix / "include/ftms" / header.name).read_bytes():
                raise RuntimeError(f"installed header bytes differ: {header.name}")
        archive = prefix / "lib/libftms.a"
        if archive.read_bytes() != (objects / "libftms.a").read_bytes():
            raise RuntimeError("installed archive bytes differ")
        for language, driver, flags, source in [
            ("c", compiler, CFLAGS, "consumer.c"),
            *[(name, driver, CXXFLAGS, "consumer.cpp") for name, driver in cpp_compilers],
        ]:
            executable = build / f"consumer-{c_name}-{language}"
            run([driver, *flags, "-I", str(prefix / "include"),
                 str(PACKAGE / "tests" / source), str(archive), "-o", str(executable)])
            run([str(executable)])
    print("installed consumer matrix passed: 2 C + 4 C++ consumers; GCC/Clang archives, real DESTDIR install")
    return 0


if __name__ == "__main__":
    sys.exit(main())
