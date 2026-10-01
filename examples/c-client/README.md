# C installed-library quickstart

Decode Indoor Bike and Treadmill data, detect truncation, and encode—but never
send—Request Control bytes. [main.c](main.c) checks expected values and exits
nonzero on failure. The same example also compiles as C++11 against the C library.

Prerequisites: CMake 3.16+, compatible C99/C++11 compilers, and a build tool.
The commands below use a POSIX shell, curl, tar and sha256sum. Windows users can
download the same assets and verify the hash with PowerShell `Get-FileHash`.
Node and Python are not required for ordinary consumption.

## Download and install the released library

Run in a new directory, not a system prefix:

```sh
curl -fLO https://github.com/deancochran/ftms/releases/download/c-v0.2.0/ftms-c-0.2.0.tar.gz
curl -fLO https://github.com/deancochran/ftms/releases/download/c-v0.2.0/ftms-c-0.2.0.tar.gz.sha256
sha256sum -c ftms-c-0.2.0.tar.gz.sha256
tar -xzf ftms-c-0.2.0.tar.gz
cmake -S ftms-c-0.2.0 -B ftms-build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PWD/ftms-prefix"
cmake --build ftms-build --config Release
cmake --install ftms-build --config Release
```

Expected archive SHA-256 (also recorded in the [release matrix](../../docs/released-packages.md)):
`3aa60d809f3dcd02634417018d39f325c46a552734f0fe311ba748261914e61f`.
Compare the sidecar to this reviewed value; a matching checksum is integrity
evidence, not device or protocol qualification.

Copy this example's `main.c` and `CMakeLists.txt` into a directory named `client`
alongside `ftms-prefix`, then run:

```sh
cmake -S client -B example-build -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$PWD/ftms-prefix"
cmake --build example-build --config Release
ctest --test-dir example-build -C Release --output-on-failure
ctest --test-dir example-build -C Release -V
```

Both tests must pass. Verbose output includes raw bike power `250 W`, raw cadence
`180 0.5 rpm` (90 rpm), treadmill inclination `-15 0.1 percent` (-1.5%), and
`Request Control bytes: 0x00 (encoded only; not sent)`. The example asserts these
key values and a deliberately truncated packet. Other printed fields remain
raw integers; [measurement.h](../../packages/c/include/ftms/measurement.h) defines scales.

Keep `CMAKE_BUILD_TYPE=Release` for single-configuration generators such as Unix
Makefiles or Ninja; `--config Release` alone does not select their build type.
Multi-configuration generators use `--config Release` at build/install time.

`find_package(ftms CONFIG REQUIRED)` discovers the installed library; it does
not download it. For other acquisition methods see [C installation](../../packages/c/INSTALL.md).
The example itself is repository-owned and is not shipped inside the C archive.

## Contributor-only candidate verification

From a repository checkout, `python3 packages/c/scripts/source-bundle.py` creates
a local candidate. Substitute that archive in the same flow to test a candidate,
but do not describe it as the released artifact. The native test suite checks
the example against an isolated installation of its source candidate.

## Boundaries

The example contains no BLE transport. Applications own discovery, properties,
security, control ownership, supported-range validation, serialized procedures,
matching indications, timeouts, disconnection and user authorization. Host codec
success is not physical equipment compatibility, PTS or Bluetooth qualification.
