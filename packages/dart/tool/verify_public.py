"""Read-only registry verification after an explicitly authorized publication."""
from __future__ import annotations

import json
import re
import tempfile
import urllib.request
from pathlib import Path

from corpus import PACKAGE, sha256
from verify_package import NAME, extract_checked, require_current_package, run_consumer, version


def fetch(url: str, limit: int) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Registry response exceeds bounded verification size")
        return data


def main() -> None:
    report_path = PACKAGE / "build/distribution/package-verification.json"
    expected = json.loads(report_path.read_text())
    require_current_package(expected)
    if (not expected.get("complete") or expected["name"] != NAME
            or expected["version"] != version() or expected.get("dirty") is not False):
        raise ValueError("Clean, complete release package evidence required")
    result_path = PACKAGE / "build/distribution/public-verification.json"
    result_path.write_text('{"complete":false}\n')
    release_version = expected["version"]
    metadata = json.loads(fetch(f"https://pub.dev/api/packages/{NAME}/versions/{release_version}", 1_000_000))
    if metadata["version"] != release_version:
        raise ValueError("Registry version mismatch")
    digest = metadata["archive_sha256"]
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Invalid registry archive digest")
    # Use a fixed public endpoint, not a server-supplied arbitrary archive URL.
    archive_url = f"https://pub.dev/api/archives/{NAME}-{release_version}.tar.gz"
    archive = PACKAGE / "build/distribution/public.tar.gz"
    archive.write_bytes(fetch(archive_url, 16_000_000))
    if sha256(archive) != digest:
        raise ValueError("Registry archive checksum mismatch")
    with tempfile.TemporaryDirectory(prefix="ftms-dart-public-", dir=Path.home() / ".cache") as temporary:
        root = Path(temporary)
        package = root / "package"
        extract_checked(archive, package, expected["files"])
        run_consumer(package, root / "consumer", root / "cache", hosted_version=release_version)
    result_path.write_text(json.dumps({"complete": True, "name": NAME,
        "version": release_version, "registryArchiveSha256": digest,
        "fileManifestMatched": True, "hostedConsumerExecuted": True,
        "sourceCommit": expected["sourceCommit"]}, indent=2) + "\n")


if __name__ == "__main__":
    main()
