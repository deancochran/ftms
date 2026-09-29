#!/usr/bin/env python3
"""Operator-authorized Linux passive capture; never writes Control Point.

Requires distro python-dbus and PyGObject. Captures are private local evidence,
not automatic additions to the canonical corpus. No pairing or agent changes.
"""
import argparse
import json
import os
import time
from pathlib import Path

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

BASE = "-0000-1000-8000-00805f9b34fb"
SERVICE = "00001826" + BASE
BIKE = "00002ad2" + BASE
READS = {"00002acc" + BASE, *("0000" + x + BASE for x in ["2ad4", "2ad5", "2ad6", "2ad7", "2ad8"])}


class CleanupFailed(RuntimeError):
    """Evidence was saved, but the radio session could not be fully released."""


def wait_until(predicate, seconds):
    end = time.monotonic() + seconds
    context = GLib.MainContext.default()
    while time.monotonic() < end:
        while context.pending():
            context.iteration(False)
        if predicate():
            return True
        time.sleep(0.05)
    return predicate()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--name", required=True, help="Exact advertised name confirmed by the operator; not recorded")
    parser.add_argument("--seconds", type=int, default=45)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 120:
        parser.error("seconds must be between 1 and 120")
    if args.output.exists():
        parser.error("output already exists; select a new private capture path")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Reserve a private file before interacting with equipment.
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    record = {"schema": "ftms-local-passive-capture-1", "model": "Wahoo KICKR CORE",
              "firmwareUserReported": "2.5.37", "mode": "passive-no-control",
              "result": "not_run", "characteristics": [], "packets": [], "errors": []}
    bus = adapter = device = subscription = receiver = None
    discovery_owned = connected_owned = False
    start = time.monotonic()
    try:
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")

        def objects():
            return manager.GetManagedObjects()

        def properties(path, interface):
            return dbus.Interface(bus.get_object("org.bluez", path), "org.freedesktop.DBus.Properties").GetAll(interface)

        adapters = [p for p, interfaces in objects().items() if "org.bluez.Adapter1" in interfaces]
        if len(adapters) != 1:
            record["result"] = "adapter_selection_required"
            return 2
        adapter_path = adapters[0]
        adapter = dbus.Interface(bus.get_object("org.bluez", adapter_path), "org.bluez.Adapter1")
        state = properties(adapter_path, "org.bluez.Adapter1")
        if not state.get("Powered", False):
            record["result"] = "adapter_not_powered"
            return 2
        if not state.get("Discovering", False):
            adapter.StartDiscovery()
            discovery_owned = True
        print("Scanning for KICKR CORE (20 seconds; nearby identifiers are not logged)", flush=True)
        wait_until(lambda: False, 20)
        candidates = []
        for path, interfaces in objects().items():
            props = interfaces.get("org.bluez.Device1", {})
            if props.get("Adapter") == adapter_path and str(props.get("Name", "")) == args.name:
                candidates.append(path)
        if discovery_owned:
            adapter.StopDiscovery()
            discovery_owned = False
        record["matchingDevices"] = len(candidates)
        if len(candidates) != 1:
            record["result"] = "device_not_found" if not candidates else "ambiguous_device"
            return 2
        device_path = candidates[0]
        device = dbus.Interface(bus.get_object("org.bluez", device_path), "org.bluez.Device1")
        state = properties(device_path, "org.bluez.Device1")
        if not state.get("Connected", False):
            connected_owned = True
            device.Connect(timeout=30)
        if not wait_until(lambda: bool(properties(device_path, "org.bluez.Device1").get("ServicesResolved", False)), 20):
            record["result"] = "services_unresolved"
            return 2
        all_objects = objects()
        services = [p for p, i in all_objects.items() if
                    str(i.get("org.bluez.GattService1", {}).get("UUID", "")) == SERVICE and
                    i["org.bluez.GattService1"].get("Device") == device_path]
        record["ftmsServiceInstances"] = len(services)
        if len(services) != 1:
            record["result"] = "ftms_absent_or_ambiguous"
            return 2
        bikes = []
        for path, interfaces in all_objects.items():
            props = interfaces.get("org.bluez.GattCharacteristic1", {})
            if props.get("Service") != services[0]:
                continue
            uuid = str(props["UUID"])
            flags = [str(flag) for flag in props.get("Flags", [])]
            entry = {"uuid": uuid, "flags": flags, "readState": "not_attempted"}
            record["characteristics"].append(entry)
            if uuid in READS and "read" in flags:
                try:
                    value = dbus.Interface(bus.get_object("org.bluez", path), "org.bluez.GattCharacteristic1").ReadValue(dbus.Dictionary({}, signature="sv"))
                    entry.update(readState="success", hex=bytes(value).hex())
                except dbus.DBusException as error:
                    entry.update(readState="failed", error=error.get_dbus_name())
            if uuid == BIKE:
                bikes.append((path, flags))
        if len(bikes) != 1 or "notify" not in bikes[0][1]:
            record["result"] = "bike_notification_unavailable_or_ambiguous"
            return 2
        bike_path = bikes[0][0]

        def changed(interface, changed_properties, invalidated):
            if interface == "org.bluez.GattCharacteristic1" and "Value" in changed_properties:
                value = bytes(changed_properties["Value"])
                if len(record["packets"]) >= 4096 or len(value) > 512:
                    record["errors"].append("capture_limit")
                    return
                record["packets"].append({"elapsedMs": round((time.monotonic() - start) * 1000),
                                          "uuid": BIKE, "hex": value.hex()})

        receiver = bus.add_signal_receiver(changed, signal_name="PropertiesChanged",
            dbus_interface="org.freedesktop.DBus.Properties", path=bike_path, bus_name="org.bluez")
        characteristic = dbus.Interface(bus.get_object("org.bluez", bike_path), "org.bluez.GattCharacteristic1")
        characteristic.StartNotify(timeout=15)
        subscription = characteristic
        print(f"Receiving Indoor Bike Data for {args.seconds} seconds; no Control Point writes", flush=True)
        wait_until(lambda: bool(record["errors"]), args.seconds)
        record["result"] = "captured" if record["packets"] and not record["errors"] else "no_telemetry_or_capture_error"
        return 0 if record["result"] == "captured" else 2
    except dbus.DBusException as error:
        record["result"] = "bluetooth_error"
        record["errors"].append(error.get_dbus_name())
        return 2
    finally:
        for action in [subscription.StopNotify if subscription else None,
                       device.Disconnect if connected_owned and device else None,
                       adapter.StopDiscovery if discovery_owned and adapter else None]:
            if action:
                try:
                    action(timeout=10)
                except dbus.DBusException as error:
                    record["errors"].append("cleanup:" + error.get_dbus_name())
        if receiver:
            receiver.remove()
        cleanup_failed = any(error.startswith("cleanup:") for error in record["errors"])
        if cleanup_failed and record["result"] == "captured":
            record["result"] = "captured_with_cleanup_error"
        record["elapsedSeconds"] = round(time.monotonic() - start, 3)
        with os.fdopen(descriptor, "w") as output:
            json.dump(record, output, indent=2)
            output.write("\n")
        print(json.dumps({"result": record["result"], "packets": len(record["packets"]), "errors": record["errors"]}), flush=True)
        if cleanup_failed:
            raise CleanupFailed("Bluetooth cleanup failed; see the private capture record")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CleanupFailed:
        raise SystemExit(2) from None
