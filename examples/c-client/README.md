# C FTMS client example

This is a C99 consumer of the installed `ftms::ftms` CMake target. It decodes
literal Indoor Bike and Treadmill characteristic values, checks a deliberately
truncated value, and encodes—but never sends—a Request Control operation. Its
output preserves the library's raw integer units; `measurement.h` defines each
field's scale and unavailable sentinel.

## Build from the local source candidate

The C `0.1.0` candidate is not published. First obtain an archive supplied by
your maintainer (or build the local candidate), verify its SHA-256 sidecar, then
install it to an isolated prefix:

```sh
python3 packages/c/scripts/source-bundle.py
tar -xzf packages/c/build/source-candidate/ftms-c-0.1.0.tar.gz
cmake -S ftms-c-0.1.0 -B ftms-build -DCMAKE_INSTALL_PREFIX="$PWD/ftms-prefix"
cmake --build ftms-build
cmake --install ftms-build
cmake -S examples/c-client -B example-build -DCMAKE_PREFIX_PATH="$PWD/ftms-prefix"
cmake --build example-build
ctest --test-dir example-build --output-on-failure
```

The library target is implemented as C99. A C++ consumer can link the same
`ftms::ftms` target; set that consumer's own C++ language level (the package
verification consumers use `cxx_std_11`) and compile its C++ sources normally.

Once a C release archive exists, obtain that archive and its published SHA-256
from its release record before following the same install-and-consume flow. Do
not substitute an unverified URL or treat this candidate as a publication.

The example has no BLE transport and does not write a Control Point. A caller
must separately establish discovery state, characteristic properties, security,
control ownership, range validation, procedure serialization, responses, and
user authorization. It is a host codec example, not real-hardware, PTS, or
Bluetooth qualification evidence.
