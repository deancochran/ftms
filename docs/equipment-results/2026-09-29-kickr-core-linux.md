# KICKR CORE / Linux passive pilot — 2026-09-29

**Disposition: partial interoperability evidence, not qualification.**
The operator authorized testing after selecting an embedded-C pilot, computer
first. Only scanning, connection, discovery, characteristic reads and Indoor Bike
Data notification subscription were performed. No Control Point write, control
acquisition, workout start/stop, resistance/power target, calibration, firmware
update or virtual-shifting command was issued. Subscription is a GATT/CCCD
operation, not a claim of absolutely no Bluetooth writes.

## Identity and scope

- Equipment: Wahoo KICKR CORE with Zwift Cog, firmware **2.5.37** as shown by
  the user's device-information screenshot. Firmware was not independently read
  in this session. Serial, ANT+ ID, BLE address and advertising suffix omitted.
- Host: EndeavourOS, Linux `7.2.2-arch1-1`, x86_64; BlueZ **5.87**, `btusb`.
- Capture: `examples/c-passive-replay/capture_bluez.py`, system python-dbus and
  PyGObject, 20-second discovery followed by 45-second and 10-second notification
  windows in two independently connected sessions. Exact
  operator-confirmed device name selected in memory; not retained in the record.
- Source: branch `fix/protocol-boundary-hardening`, dirty local changes on
  `74f1552959d96755f38eac42f6999a5b04088b2f`. C production sources are unchanged
  from released 0.1.0. C replay used an actual CMake-installed library; TypeScript
  used the locally built 0.3.0-based hardening candidate, not a fresh npm install.
- Capture and replay files are private ignored artifacts under
  `packages/c/build/equipment-private/`, mode 0600, not canonical fixtures.
  Capture `kickr-passive-01.json` SHA-256:
  `3f8cb0fd7f769edb51e814f499e4c52241ae6b7b00e2f24538c1f10067d4abff`.
  Second capture `kickr-passive-02.json` SHA-256:
  `f8198bbd29418bd73d5acde09b342030fd1c5b9436e82f888b1e5698c4e78053`.
  Back up privately if retaining evidence; ignored build files are not archival.

## Observed discovery and reads

One FTMS service instance was found. Its observed characteristics were:

| UUID | Observed properties | Read result |
| --- | --- | --- |
| 2ACC Feature | Read | Success, 8 bytes; raw machine=16387, target=24588 |
| 2AD8 Power Range | Read | Success, 6 bytes; 0–2000 W, increment 1 W |
| 2AD6 Resistance Range | Read | Success, 6 bytes; see profile limitation below |
| 2AD2 Indoor Bike Data | Notify | Subscribed; 45 received notifications |
| 2ADA Machine Status | Notify | Not subscribed |
| 2AD9 Control Point | Write, Indicate | **Not written or subscribed** |
| 2AD3 Training Status | Read, Notify | Not read/subscribed in this pilot |

Short UUIDs above expand using the Bluetooth base UUID. Feature declarations do
not establish authorization, supported execution or C.7 lifetime/bonding facts.

## Telemetry replay results

- **45/45** observed 8-byte Indoor Bike Data values decoded through the installed
  C replay executable with exit 0.
- **45/45** complete raw reports from the C measurement driver exactly matched
  TypeScript for the same bytes: masks, all 30 raw values and all diagnostics.
- No More Data, truncation, trailing-byte or reserved-flag indicator appeared in
  these packets. This does not test fragmented records or every optional field.
- Speed, cadence and power varied and included nonzero readings. Physical values
  were not independently checked against a display or reference. The observation
  supports non-idle telemetry decoding, not measurement accuracy or calibration.
- Capture reported no errors. Cleanup StopNotify/Disconnect/StopDiscovery calls
  reported no errors; a subsequent local check showed discovery inactive and no
  matching cached target object. No pairing/agent settings were changed.

## Resistance Range compatibility observation

Both default range decoders rejected the actual **six-byte** 2AD6 value with a
length error, because their default resistance range layout is three UINT8
whole-level fields. This is not a failed Bluetooth read.

Explicitly choosing the already-supported `signed16Tenths` range format **offline**
produced the same result in both ports: minimum numerator 0, maximum 100,
increment 1, divisor 10 (interpreted as 0–10 levels, increment 0.1 under that
profile). This demonstrates structural compatibility with that profile, not
independent proof of physical resistance units. No Control Point command format
or measurement resistance layout was inferred from this range or the device name.
No defaults were modified. Profile choice must remain explicit and documented.

## Remaining gates

A subsequent disconnect/reconnect/discovery/subscription session captured another
10 packets, all decoded by the installed C replay and exactly matching the
TypeScript/C raw reports, with no capture/cleanup errors. Total: **55 packets**.
This demonstrates one successful reconnect path, not exhaustive lifecycle or
generation-state verification. The C replay is stateless; assembler generation
handling was not exercised by these unfragmented packets.

- Independent physical/reference comparison: **not run**.
- Controlled idle versus active intervals: **not run**. One reconnect and
  resubscription succeeded, as noted above.
- Fragmented records, drop/reordering, optional resistance telemetry: **not observed**.
- Live controls, virtual shifting, security/bonding behavior: **not tested**.
- MCU link/runtime and Bluetooth PTS/qualification: **not tested**.

Do not generalize these observations beyond this model/firmware/session. Before
turning private captures into shared fixtures, review and sanitize them, establish
independent expectations and obtain approval to retain/distribute the data.
