# C protocol design

The released C99 library provides bidirectional Feature, range, measurement,
control and status codecs, plus static capability interpretation. It has no
BLE/OS API, allocator, I/O or global mutable state. CMake installation is provided
in the source archive. See [release status](../../../docs/released-packages.md),
[installation](../INSTALL.md), and the [public API index](../../../docs/api.md).
The design notes below focus on representation and ownership; each public header
is authoritative for its operation-specific argument and output contracts.

## API and representation

`include/ftms/ftms.h` is C99 and C++11-consumer compatible: it includes only
standard fixed-width/size headers, checks `CHAR_BIT == 8`, and uses an
`extern "C"` guard under `__cplusplus`. C source is compiled by a C compiler and
linked by C++ consumers; this demonstrates the tested compiler ABI combination,
not every vendor ABI. The header is self-contained and double-inclusion tested.

Feature output preserves both raw little-endian `uint32_t` words, including
unknown/reserved bits. The 17 defined machine and 17 defined target masks use
`uint32_t` shifts, not implementation-defined C bitfields. There are deliberately
no legacy ERG/SIM names; the host corpus adapter maps its three legacy aliases to
canonical bits only for v1 comparison.

Ranges use scaled integers (`int32_t minimum/maximum/increment`) plus a divisor
and unit: speed `u16 / 100`, inclination `s16 / 10`, power `s16`, resistance
`u8` by default (explicit signed16-tenths profile also available), and heart rate
`u8`. This preserves the wire meaning without an FPU. A
zero increment or reversed bounds is rejected. Range characteristic layouts are
not reused for control operands.

The Feature and supported-range decoders require non-null input/output and exact
lengths. Measurement/status diagnostics have different contracts. Invalid range kind
is reported before any input access. Outputs are assigned only after complete
validation and thus remain unchanged on failure. Byte reads are individually
assembled with explicitly widened operands, so unaligned input is safe; signed
16-bit values use `int32_t` subtraction rather than a potentially
implementation-defined unsigned-to-signed narrowing conversion. Input/output
may overlap for these Feature/range operations because bytes are read into locals
before the output write; do not generalize that permission to other APIs. No
pointer is retained.

## References and choices

* https://isocpp.org/wiki/faq/mixing-c-and-cpp — C linkage guard and C-object /
  C++-driver test.
* https://wiki.sei.cmu.edu/confluence/display/c/EXP36-C.+Do+not+cast+pointers+into+more+strictly+aligned+pointer+types — no typed casts of packet bytes.
* https://cmake.org/cmake/help/latest/guide/importing-exporting/index.html — the
  package-owned CMake project exports `ftms::ftms`; installed C/C++ consumers are
  tested independently of the source directory. Make tooling is checkout-only.
* FTMS 1.0 local project context and EC23224; canonical vectors are regression
  evidence, not the protocol oracle.

`tests/corpus_adapter.py` is host-only Python standard-library/jsonschema test
code. It reads canonical JSON directly and invokes a compiled C driver; JSON is
never embedded in or required by the target library.

## Capability evidence

`ftms_capability_requirements` preflights exact caller buffer counts and
`ftms_evaluate_capabilities` fills caller-owned observations, diagnostics and a
report without allocation or retained pointers. UUIDs are canonical Bluetooth
display/network-order 16-byte values; SIG UUID recognition requires the complete
Bluetooth base UUID, so arbitrary 128-bit UUIDs are copied rather than truncated.
The caller retains the snapshot/raw bytes and scopes it to one service instance and
generation. Discovery/read/malformed/property/duplicate evidence is distinct from
an API argument error. Reports never contain a `canExecute` claim.

For explicit C.7 evidence use the matching `_with_c7` requirements and evaluation
APIs with identical options. Omitted evidence remains unknown, not false; read
the [capability contract](../../../shared/protocol/capability-discovery.md).

Unlike the two byte decoders, snapshot inputs and output objects/buffers must not
overlap. Each call validates arguments before evaluating; a first evaluation
counts diagnostics without writes, and a second populates the caller buffers only
after capacity/null checks succeed. There is no allocation or arbitrary vendor
characteristic limit. Work is linear in observation count with fixed 16-kind,
5-range and 21-operation state. `size_t` count arithmetic is checked before walking
the input. Tests cover error atomicity for both buffers and the report.

The C source avoids hosted headers by using byte loops for UUID matching/copy and
report initialization. This does not promise absence of compiler-generated memory
helpers: the Cortex-M0 `-Oz -ffreestanding` compilation emits `__aeabi_memclr4` for
local aggregate initialization. An embedded SDK/runtime must supply it. Stack
and object-size evidence is compiler/flags-specific, not a bounded whole-firmware
resource claim. `make check-embedded` records compile-only evidence without a
sysroot download or substituting test headers for missing production headers.

The separate capability corpus uses exact output comparisons and literal template
edits; it never computes expected behavior with the C interpreter. The host driver
normalizes `SIZE_MAX` indices to null, serializes actual range kinds and every
operation/reason/diagnostic, and is not shipped in the library archive. Tests
deliberately mutate these fields to prove the comparator rejects incorrect output.
