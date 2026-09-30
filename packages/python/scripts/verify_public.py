#!/usr/bin/env python3
"""Verify exact public PyPI artifacts and execute an isolated installed consumer."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PACKAGE_NAME = "deancochran-ftms"
PYPI_JSON = f"https://pypi.org/pypi/{PACKAGE_NAME}/{{version}}/json"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fetch(url: str, attempts: int = 8, delay_seconds: int = 10) -> bytes:
    error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "ftms-release-verifier"})
            with urllib.request.urlopen(request, timeout=30) as response:
                return bytes(response.read())
        except (TimeoutError, urllib.error.HTTPError, urllib.error.URLError) as caught:
            error = caught
            if attempt + 1 < attempts:
                time.sleep(delay_seconds)
    raise RuntimeError(f"failed to fetch {url}: {error}")


def _select_artifacts(metadata: dict[str, Any], version: str) -> dict[str, dict[str, Any]]:
    info = metadata.get("info")
    if not isinstance(info, dict):
        raise ValueError("PyPI response has no info object")
    if info.get("name") != PACKAGE_NAME or info.get("version") != version:
        raise ValueError("PyPI project/version identity does not match")

    expected = {
        "wheel": f"deancochran_ftms-{version}-py3-none-any.whl",
        "sdist": f"deancochran_ftms-{version}.tar.gz",
    }
    urls = metadata.get("urls")
    if not isinstance(urls, list) or len(urls) != len(expected):
        raise ValueError("PyPI release must contain exactly one wheel and one source distribution")

    selected: dict[str, dict[str, Any]] = {}
    for raw in urls:
        if not isinstance(raw, dict):
            raise ValueError("PyPI artifact entry is not an object")
        filename = raw.get("filename")
        kind = next((name for name, wanted in expected.items() if filename == wanted), None)
        if kind is None or kind in selected:
            raise ValueError(f"unexpected or duplicate PyPI artifact: {filename}")
        if raw.get("yanked") is not False:
            raise ValueError(f"PyPI artifact is yanked: {filename}")
        url = raw.get("url")
        if not isinstance(url, str):
            raise ValueError(f"PyPI artifact has no URL: {filename}")
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "files.pythonhosted.org":
            raise ValueError(f"PyPI artifact URL is not an expected pythonhosted URL: {filename}")
        digest = raw.get("digests")
        if not isinstance(digest, dict) or not isinstance(digest.get("sha256"), str):
            raise ValueError(f"PyPI artifact has no SHA-256: {filename}")
        selected[kind] = raw

    if set(selected) != set(expected):
        raise ValueError("PyPI release artifact set is incomplete")
    return selected


def _run_consumer(artifact: Path, root: Path, report: dict[str, Any], artifact_kind: str) -> None:
    environment = root / f"venv-{artifact_kind}"
    subprocess.run([sys.executable, "-m", "venv", str(environment)], check=True)
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-cache-dir",
            "--no-deps",
            str(artifact),
        ],
        check=True,
    )
    consumer = """
import importlib.metadata as m
import deancochran_ftms as f
assert m.version('deancochran-ftms') == VERSION
feature = f.FeaturesRaw(0x80000000, 1 << 13)
wire = f.encode_features_raw(feature)
assert wire == bytes([0, 0, 0, 128, 0, 32, 0, 0])
assert f.decode_features_raw(wire) == feature
request = f.ControlRequestRaw(5, (75,))
assert f.encode_control_request_raw(request) == bytes([5, 75, 0])
assert f.decode_control_response_raw(bytes([128, 5, 1])).result_code == 1
measurement = f.MeasurementRaw(5, 0, 1, 0, (1234,) + (0,) * 29)
assert f.decode_measurement_raw(f.encode_measurement_raw(measurement), 5).values[0] == 1234
""".replace("VERSION", repr(report["packageVersion"]))
    subprocess.run([str(python), "-I", "-c", consumer], check=True)
    report.setdefault("consumers", {})[artifact_kind] = {
        "outcome": "passed",
        "interpreter": subprocess.check_output(
            [str(python), "-c", "import sys; print(sys.version)"], text=True
        ).strip(),
    }


def verify_public_release(
    version: str,
    expected_wheel_sha256: str,
    expected_sdist_sha256: str,
    output: Path,
    metadata_url: str | None = None,
) -> bool:
    report: dict[str, Any] = {
        "package": PACKAGE_NAME,
        "packageVersion": version,
        "registry": "https://pypi.org/",
        "artifacts": {},
        "errors": [],
    }
    try:
        raw_metadata = _fetch(metadata_url or PYPI_JSON.format(version=version))
        metadata = json.loads(raw_metadata)
        if not isinstance(metadata, dict):
            raise ValueError("PyPI response is not an object")
        selected = _select_artifacts(metadata, version)
        expected_digests = {
            "wheel": expected_wheel_sha256,
            "sdist": expected_sdist_sha256,
        }
        temporary_root = Path("/tmp/opencode")
        try:
            temporary_root.mkdir(parents=True, exist_ok=True)
            temporary = tempfile.TemporaryDirectory(
                prefix="ftms-python-public-", dir=temporary_root
            )
        except OSError:
            temporary = tempfile.TemporaryDirectory(prefix="ftms-python-public-")
        with temporary as directory:
            root = Path(directory)
            downloaded: dict[str, Path] = {}
            for kind in ("wheel", "sdist"):
                artifact = selected[kind]
                registry_digest = artifact["digests"]["sha256"]
                expected_digest = expected_digests[kind]
                if registry_digest != expected_digest:
                    raise ValueError(f"{kind} registry SHA-256 differs from verified build output")
                # Metadata propagation can legitimately lag after upload. Once
                # PyPI has advertised an exact file, use a smaller independent
                # retry budget so the whole job remains inside its timeout.
                data = _fetch(artifact["url"], attempts=3)
                actual_digest = _sha256(data)
                if actual_digest != expected_digest:
                    raise ValueError(
                        f"downloaded {kind} SHA-256 differs from verified build output"
                    )
                path = root / artifact["filename"]
                path.write_bytes(data)
                downloaded[kind] = path
                report["artifacts"][kind] = {
                    "filename": artifact["filename"],
                    "sha256": actual_digest,
                    "uploadTime": artifact.get("upload_time_iso_8601"),
                }
            for kind in ("wheel", "sdist"):
                _run_consumer(downloaded[kind], root, report, kind)
    except Exception as error:
        report["errors"].append({"reason": f"{type(error).__name__}: {error}"})
    consumers = report.get("consumers", {})
    report["complete"] = not report["errors"] and all(
        consumers.get(kind, {}).get("outcome") == "passed" for kind in ("wheel", "sdist")
    )
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    except OSError as error:
        print(
            json.dumps(
                {
                    "publicPackageVerification": False,
                    "report": str(output),
                    "reportWriteError": f"{type(error).__name__}: {error}",
                }
            ),
            file=sys.stderr,
        )
        return False
    print(json.dumps({"publicPackageVerification": report["complete"], "report": str(output)}))
    return bool(report["complete"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--wheel-sha256", required=True)
    parser.add_argument("--sdist-sha256", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "build/public-package-verification-report.json",
    )
    args = parser.parse_args()
    complete = verify_public_release(
        args.version, args.wheel_sha256, args.sdist_sha256, args.output
    )
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
