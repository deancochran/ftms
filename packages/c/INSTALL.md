# Install FTMS for C

This source package builds a portable C99 static library. C++ consumers use the
same library through its C-linkage headers; no wrapper library is required.
Read `VERSION` for the package version and `SOURCE.json` for exact source identity.
An artifact's existence is not evidence that it is registered in vcpkg or ConanCenter.

## Download, verify, extract, install

Obtain the source archive and SHA-256 sidecar from the chosen immutable `c-vVERSION`
GitHub release. Verify the sidecar in the archive's directory before extracting:

```sh
sha256sum -c ftms-c-VERSION.tar.gz.sha256
tar -xzf ftms-c-VERSION.tar.gz
cd ftms-c-VERSION
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/your/local/prefix
cmake --build build --config Release
cmake --install build --config Release
```

Replace `VERSION` with the actual version. Windows users can verify SHA-256 with
PowerShell `Get-FileHash` and use their standard archive extractor; CMake supports
Visual Studio's multi-configuration build. Building requires CMake 3.16+ and a C99
compiler. Consuming the C++ API requires a compatible C/C++ ABI. Ordinary builds
need neither Node nor Python. Tests and package-manager tools have separate host
dependencies. Do not use a privileged system install unless explicitly intended.

## Installed CMake dependency

```cmake
find_package(ftms CONFIG REQUIRED)
target_link_libraries(your_application PRIVATE ftms::ftms)
```

Configure your application with `-DCMAKE_PREFIX_PATH=/your/local/prefix`.
`find_package` finds an installed dependency; it does not download it. The
`ftms.pc` file also supports pkg-config consumers. Pre-1.0 package-config version
compatibility requires the same major/minor; use an exact version when required.

## Vendored or downloaded source

For a checked-in/extracted source dependency:

```cmake
add_subdirectory(third_party/ftms-c)
target_link_libraries(your_application PRIVATE ftms::ftms)
```

For CMake FetchContent, use a real release URL and its reviewed SHA-256:

```cmake
include(FetchContent)
FetchContent_Declare(ftms
  URL "${FTMS_SOURCE_URL}"
  URL_HASH "SHA256=${FTMS_SOURCE_SHA256}")
FetchContent_MakeAvailable(ftms)
target_link_libraries(your_application PRIVATE ftms::ftms)
```

Set those variables to the chosen artifact, not a moving main-branch archive.
For a vendor IDE, compile `src/*.c` as C99, add `include/` to the header search
path and link the objects. There is no universal precompiled archive for all
embedded CPUs/ABIs. Supply any compiler-generated runtime helpers as required by
your toolchain. Select a CMake toolchain file for cross compilation as normal.

## Conan

The included Conan 2 recipe can be created in a configured local Conan environment:

```sh
conan create . --no-remote
```

This creates a local `ftms/VERSION` package; it does not upload it or establish
ConanCenter availability. A consumer then declares that version in its Conan
requirements and uses CMakeDeps/CMakeToolchain with the same `ftms::ftms` target.
The repository's release checks independently test C and C++ consumers against
the extracted archive recipe.

## Minimal C or C++ use

```c
#include <ftms/ftms.h>

int main(void) {
  const uint8_t bytes[8] = {1, 0, 0, 0, 2, 0, 0, 0};
  ftms_features features;
  return ftms_decode_features(bytes, sizeof bytes, &features) != FTMS_OK;
}
```

See the public headers for measurement, control, status, packet-planning and
capability APIs. No BLE transport, connection lifecycle, permission handling or
actuator safety is supplied. Host/package tests are not board interoperability
or Bluetooth qualification. The minimal archive omits repository conformance
tooling; check out the source revision identified in `SOURCE.json` to run it.
