#!/usr/bin/env python3
"""Build and prove a non-editable consumer from an extracted source distribution."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from pathlib import Path
from typing import Any

PACKAGE = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_archive_manifests(sdist: Path, wheel: Path) -> None:
    config = tomllib.loads((PACKAGE / "pyproject.toml").read_text())
    included = config["tool"]["hatch"]["build"]["targets"]["sdist"]["only-include"]
    identity = config["project"]["name"].replace("-", "_") + "-" + config["project"]["version"]
    expected_source = {f"{identity}/{name}" for name in included} | {f"{identity}/PKG-INFO"}
    with tarfile.open(sdist) as archive:
        members = archive.getmembers()
        if (
            {item.name for item in members} != expected_source
            or len(members) != len(expected_source)
            or any(not item.isfile() for item in members)
        ):
            raise ValueError("sdist does not match its explicit release manifest")
    expected_wheel = {name.removeprefix("src/") for name in included if name.startswith("src/")}
    expected_wheel.update(
        f"{identity}.dist-info/{name}"
        for name in ("METADATA", "WHEEL", "RECORD", "licenses/LICENSE")
    )
    with zipfile.ZipFile(wheel) as wheel_archive:
        names = wheel_archive.namelist()
        if set(names) != expected_wheel or len(names) != len(expected_wheel):
            raise ValueError("wheel does not match its explicit release manifest")


def _step(report: dict[str, Any], name: str, *args: str, cwd: Path | None = None) -> None:
    try:
        completed = subprocess.run(args, cwd=cwd, check=True, text=True, capture_output=True)
        report["steps"].append(
            {"name": name, "outcome": "passed", "returncode": completed.returncode}
        )
    except subprocess.CalledProcessError as error:
        report["steps"].append(
            {
                "name": name,
                "outcome": "failed",
                "returncode": error.returncode,
                "reason": error.stderr[-1000:],
            }
        )
        raise


def main() -> int:
    build = PACKAGE / "build" / "isolated"
    version = tomllib.loads((PACKAGE / "pyproject.toml").read_text())["project"]["version"]
    report: dict[str, Any] = {
        "package": "deancochran-ftms",
        "packageVersion": version,
        "steps": [],
        "artifacts": {},
        "errors": [],
    }
    try:
        shutil.rmtree(build, ignore_errors=True)
        build.mkdir(parents=True)
        _step(report, "build-source-artifacts", "uv", "build", "--out-dir", str(build), cwd=PACKAGE)
        sdist = next(build.glob("*.tar.gz"))
        wheel = next(build.glob("*.whl"))
        _check_archive_manifests(sdist, wheel)
        report["artifacts"]["sourceBuild"] = {
            sdist.name: _sha256(sdist),
            wheel.name: _sha256(wheel),
        }
        temporary_root: str | None = "/tmp/opencode"
        try:
            Path("/tmp/opencode").mkdir(parents=True, exist_ok=True)
            probe = Path(tempfile.mkdtemp(prefix="ftms-python-probe-", dir=temporary_root))
            probe.rmdir()
        except OSError:
            temporary_root = None
            report["temporaryRoot"] = "system default fallback; /tmp/opencode was not writable"
        else:
            report["temporaryRoot"] = "/tmp/opencode"
        with tempfile.TemporaryDirectory(
            prefix="ftms-python-sdist-", dir=temporary_root
        ) as temporary:
            temporary_path = Path(temporary)
            with tarfile.open(sdist) as archive:
                archive.extractall(temporary_path, filter="data")
            extracted = next(temporary_path.iterdir())
            rebuilt = temporary_path / "rebuilt"
            _step(
                report,
                "rebuild-extracted-sdist",
                "uv",
                "build",
                "--out-dir",
                str(rebuilt),
                cwd=extracted,
            )
            rebuilt_wheel = next(rebuilt.glob("*.whl"))
            rebuilt_sdist = next(rebuilt.glob("*.tar.gz"))
            _check_archive_manifests(rebuilt_sdist, rebuilt_wheel)
            report["archiveManifestsVerified"] = True
            report["artifacts"]["rebuiltFromSdist"] = {
                rebuilt_sdist.name: _sha256(rebuilt_sdist),
                rebuilt_wheel.name: _sha256(rebuilt_wheel),
            }
            report["wheelReproducibleFromSdist"] = _sha256(wheel) == _sha256(rebuilt_wheel)
            if not report["wheelReproducibleFromSdist"]:
                raise ValueError("wheel rebuilt from sdist differs from the source-built wheel")
            environment = temporary_path / "venv"
            _step(
                report,
                "create-fresh-python-3.11-environment",
                "uv",
                "venv",
                "--python",
                "3.11",
                str(environment),
            )
            python = environment / "bin" / "python"
            report["interpreter"] = subprocess.check_output(
                [str(python), "-c", "import sys; print(sys.version)"], text=True
            ).strip()
            _step(
                report,
                "install-rebuilt-wheel-noneditable",
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                "--no-deps",
                str(rebuilt_wheel),
            )
            check = """
import importlib.metadata as m
import deancochran_ftms as f
assert f.__file__ and '/src/' not in f.__file__
assert m.metadata('deancochran-ftms')['Version'] == EXPECTED_VERSION
b = f.encode_features_raw(f.FeaturesRaw(0x80000000, 1 << 13))
assert b == bytes([0, 0, 0, 128, 0, 32, 0, 0])
assert f.decode_features_raw(b).machine == 0x80000000
assert f.encode_supported_range_raw(f.SupportedRangeRaw('speed', 500, 3000, 50, 100, 'km/h')) == bytes([244, 1, 184, 11, 50, 0])
r = f.decode_supported_range_raw(bytes([1, 100, 1]), 'resistance')
assert (r.minimum, r.maximum, r.increment) == (1, 100, 1)
c = f.encode_control_request_raw(f.ControlRequestRaw(2, (1234,)))
assert c == bytes([2, 210, 4]) and f.decode_control_request_raw(c).operands == (1234,)
assert f.decode_control_response_raw(bytes([128, 19, 1, 100, 0, 200, 0])).low == 100
assert f.encode_measurement_raw(f.MeasurementRaw(5, 0, 1, 0, (1234,) + (0,) * 29)) == bytes([0, 0, 210, 4])
assert f.decode_machine_status_raw(bytes([7, 249, 255])).parameter == (4, (-7,))
assert f.decode_training_status_raw(bytes([1, 13]) + b'manual').text == b'manual'
e = f.CharacteristicEvidence('00002acc00001000800000805f9b34fb', 2, f.ReadState.SUCCESS, read_bytes=bytes(8))
report = f.evaluate_capabilities(f.CapabilitySnapshot(f.DiscoveryState.COMPLETE, f.ServiceScope.PRESENT, 3, (e,)))
assert report.to_wire()['feature'][1] == 1 and 'canExecute' not in report.to_wire()
assert report.presence[1] is f.Presence.UNIQUE
assert report.feature[1] == f.DecodeState.VALID
r = f.CharacteristicEvidence('00002ad600001000800000805f9b34fb', 2, f.ReadState.SUCCESS, read_bytes=bytes.fromhex('f6ff64000a00'))
selected = f.evaluate_capabilities(f.CapabilitySnapshot(f.DiscoveryState.COMPLETE, f.ServiceScope.PRESENT, 4, (r,)), f.RangeFormatOptions('signed16Tenths'))
assert selected.ranges[2][3] == (2, -10, 100, 10, 10, 2)
assert (m.distribution('deancochran-ftms').locate_file('deancochran_ftms/py.typed')).is_file()
""".replace("EXPECTED_VERSION", repr(version))
            _step(
                report,
                "isolated-consumer-import-metadata-and-bytes",
                str(python),
                "-I",
                "-c",
                check,
            )
            typed_consumer = temporary_path / "consumer.py"
            typed_consumer.write_text(
                "from typing import assert_type\n"
                "from deancochran_ftms import (CapabilitySnapshot, CharacteristicEvidence, DiscoveryState,\n"
                "    FeaturesRaw, MeasurementRaw, ReadState, ServiceScope, TrainingStatusRaw,\n"
                "    decode_features_raw, decode_measurement_raw, encode_training_status_raw, evaluate_capabilities)\n"
                "assert_type(decode_features_raw(bytes(8)), FeaturesRaw)\n"
                "assert_type(decode_measurement_raw(bytes(4), 5), MeasurementRaw)\n"
                "assert_type(encode_training_status_raw(TrainingStatusRaw(0, 1)), bytes)\n"
                "snapshot = CapabilitySnapshot(DiscoveryState.COMPLETE, ServiceScope.PRESENT, 0,\n"
                "    (CharacteristicEvidence('00002acc00001000800000805f9b34fb', 2, ReadState.SUCCESS, read_bytes=bytes(8)),))\n"
                "assert_type(evaluate_capabilities(snapshot).to_wire(), dict[str, object])\n"
            )
            _step(
                report,
                "isolated-installed-typed-consumer",
                sys.executable,
                "-m",
                "mypy",
                "--strict",
                "--no-incremental",
                "--python-executable",
                str(python),
                str(typed_consumer),
                cwd=temporary_path,
            )
    except Exception as error:
        report["errors"].append({"reason": f"{type(error).__name__}: {error}"})
    report["complete"] = not report["errors"] and all(
        step["outcome"] == "passed" for step in report["steps"]
    )
    output = PACKAGE / "build" / "package-verification-report.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "isolatedConsumer": "passed" if report["complete"] else "failed",
                "report": str(output),
            },
            sort_keys=True,
        )
    )
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
