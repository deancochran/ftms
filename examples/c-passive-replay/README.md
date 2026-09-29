# Passive KICKR CORE pilot: offline C replay

User-selected target: **Wahoo KICKR CORE with Zwift Cog**, computer first.
Firmware **2.5.37** is confirmed by the user's Wahoo device-information screenshot.
The inspected development computer runs **EndeavourOS**, Linux
`7.2.2-arch1-1` on x86_64. BlueZ `bluetoothctl` and `btmon` **5.87** are installed;
the Bluetooth service is active and `hci0` is present, using `btusb`, with no
reported software/hardware radio block. These are local readiness observations,
not a connection or interoperability result. Device serial, advertising suffix
and ANT+ ID are deliberately omitted. The screenshot is not stored in the repo.

**Hardware capture status: one passive session completed; limited evidence only.**
See `docs/equipment-results/2026-09-29-kickr-core-linux.md` in the source checkout.
The C replay executable contains no BLE transport,
connection code, subscriptions or control writes. Its test bytes are synthetic,
not captured from a KICKR. Zwift-specific shifting is outside this FTMS pilot.

## Build against an installed C artifact

Install the reviewed C 0.1.0 source artifact using `packages/c/INSTALL.md`, then:

```sh
cmake -S examples/c-passive-replay -B build/passive-replay \
  -DCMAKE_PREFIX_PATH=/absolute/path/to/installed/ftms
cmake --build build/passive-replay
ctest --test-dir build/passive-replay --output-on-failure
build/passive-replay/ftms_passive_replay 4400d204b400fa00
```

That synthetic packet contains speed 1234 hundredths km/h, cadence 180 half-rpm,
and power 250 W. Output is complete raw JSON, not rounded display values. `values`
is indexed by `FTMS_M_*` in `measurement.h`; interpret `present` and `unavailable`
before using a value. More Data packets are not individually complete records;
this small replay tool does **not** assemble them or make compatibility decisions.

Exit 0 means the decoder returned without truncation/RFU/trailing diagnostics,
not that the trainer or its readings are certified. Exit 2 means a native decode
error or those diagnostics (JSON still records evidence); 64 means invalid CLI
input. Only hexadecimal bytes of **Indoor Bike Data, UUID 0x2AD2**, belong here.
Do not feed Cycling Power, CSC or vendor-specific notifications to this decoder.

The optional second argument explicitly selects `uint8Whole` (default) or
`signed16Tenths` measurement resistance format. Do not select it from the brand,
Zwift Cog, packet length or a successful parse alone. Preserve the originally
observed bytes and document any independently justified compatibility selection.

## Passive capture procedure (operator-run; not performed by this example)

The optional Linux-only `capture_bluez.py` performs an explicitly authorized
capture using system python-dbus/PyGObject. It selects one exact advertised name,
reads only Feature and Supported Range values, and subscribes only to Indoor Bike
Data. It never calls Control Point WriteValue, pairs, registers an agent or changes
radio settings. Name equality is a selection filter, not cryptographic identity;
the operator must confirm the intended nearby equipment. It stops discovery and
disconnects only when this process started them, and releases its notification
session in cleanup. Other applications should not share the test connection.

```sh
python3 examples/c-passive-replay/capture_bluez.py \
  --name 'EXACT NAME CONFIRMED BY OPERATOR' --seconds 45 \
  --output packages/c/build/equipment-private/session.json
```

Output files are reserved mode 0600, refuse overwrites and omit addresses/name/
serial identifiers. Limits are 120 seconds and 4096 packets of at most 512 bytes.
Data can still contain personal workout measurements: retain it privately, not
as an automatic shared fixture. Only run after explicit operator permission.

1. Identify exact trainer model and firmware using the vendor's ordinary device
   information screen. Do not update firmware or perform calibration merely to
   run this pilot. Record computer OS, Bluetooth adapter and chosen capture client.
2. Arrange operator consent and close other apps that own the trainer connection.
   Select a BLE inspection client appropriate to that OS. Pair/security changes,
   connections and subscriptions require operator approval; none are automated.
3. Confirm the FTMS service 0x1826 and record full characteristic UUIDs/properties.
   Record Feature/range read outcomes, not invented zero values. Keep addresses,
   serial numbers and other personal identifiers out of shared reports.
4. Subscribe only to observed Indoor Bike Data notifications (subscription may
   write a CCCD). Do not write Control Point, request control, start/resume, set
   resistance/power, calibrate or invoke virtual shifting. If telemetry requires
   such actions, stop and record that limitation rather than silently escalating.
5. Preserve each complete notification's hex, relative timestamp and source UUID
   through a short idle interval and a safely operator-driven pedaling interval.
   Keep boundaries and More Data flags intact; never join notifications by hand.
6. Replay the captured 0x2AD2 values offline through this installed C consumer.
   Record diagnostics and compare selected speed/cadence/power readings with an
   independent display/reference, noting time and unit differences. A replay
   failure is evidence to investigate, not a reason to silently change profiles.
7. Follow `docs/equipment-testing.md` for a reviewed model/firmware/platform report.
   Reconnect and any live control validation are separately approved steps.

BlueZ was used for the authorized capture without installing Bleak. The first
capture and both-port replay results are recorded separately, including the
six-byte Resistance Range compatibility limitation. The initial readiness check
did not scan/connect; the subsequent authorized test did. This is limited host/device evidence,
not MCU execution; a board/toolchain must be chosen separately for the latter.
