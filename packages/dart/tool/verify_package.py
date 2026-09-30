"""Verify source distribution contents and a consumer isolated from this checkout."""
from __future__ import annotations

import gzip
import io
import json
import os
import re
import shutil
import tarfile
import tempfile
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

from corpus import PACKAGE, ROOT, provenance, sha256
from verify import dart, run

NAME = "deancochran_ftms"
ROOT_FILES = {"pubspec.yaml", "LICENSE", "README.md", "CHANGELOG.md", "RELEASING.md"}
DIRECTORIES = {"lib", "example", "doc"}


def registry_environment(cache: Path) -> dict[str, str]:
    return {**os.environ, "PUB_CACHE": str(cache), "PUB_HOSTED_URL": "https://pub.dev"}


def require_current_package(evidence: dict) -> None:
    identity = provenance()
    if (not evidence.get("complete") or evidence.get("name") != NAME
            or evidence.get("version") != version()
            or any(evidence.get(k) != identity[k] for k in ("sourceCommit", "dirty"))):
        raise ValueError("Package evidence does not identify current source")
    manifest = {name: sha256(path) for name, path in distribution_files().items()}
    if manifest != evidence.get("files"):
        raise ValueError("Current publication files differ from verified package evidence")


def version() -> str:
    text = (PACKAGE / "pubspec.yaml").read_text()
    if not re.search(rf"^name: {NAME}$", text, re.M):
        raise ValueError("Unexpected publication identity")
    match = re.search(r"^version: (\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)$", text, re.M)
    if not match:
        raise ValueError("Invalid package version")
    return match[1]


def distribution_files() -> dict[str, Path]:
    files = {name: PACKAGE / name for name in sorted(ROOT_FILES)}
    for directory in sorted(DIRECTORIES):
        for path in sorted((PACKAGE / directory).rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Symlink not allowed: {path}")
            if path.is_file() and not path.is_relative_to(PACKAGE / "doc/api"):
                if path.suffix not in (".dart", ".md"):
                    raise ValueError(f"Unexpected distribution file: {path}")
                files[str(path.relative_to(PACKAGE)).replace(os.sep, "/")] = path
    if any(not p.is_file() or p.is_symlink() for p in files.values()):
        raise ValueError("Missing required publication file")
    if files["LICENSE"].read_bytes() != (ROOT / "LICENSE").read_bytes():
        raise ValueError("Package LICENSE differs from canonical repository policy")
    if "lib/deancochran_ftms.dart" not in files or "example/main.dart" not in files:
        raise ValueError("Missing public entry point or runnable example")
    return files


def archive_bytes(files: dict[str, Path]) -> bytes:
    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=0, filename="") as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as archive:
            for name, path in sorted(files.items()):
                data = path.read_bytes()
                info = tarfile.TarInfo(name)
                info.size, info.mode, info.mtime = len(data), 0o644, 0
                archive.addfile(info, io.BytesIO(data))
    return output.getvalue()


def extract_checked(archive: Path, destination: Path, expected: dict[str, str]) -> None:
    observed = {}
    extracted_size = 0
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            if member.isdir():
                target = destination / member.name
                if not target.resolve().is_relative_to(destination.resolve()):
                    raise ValueError("Archive directory escapes extraction directory")
                continue
            if not member.isfile() or member.name not in expected or member.name in observed:
                raise ValueError(f"Unexpected/duplicate/non-file archive member: {member.name}")
            extracted_size += member.size
            if member.size > 8_000_000 or extracted_size > 32_000_000:
                raise ValueError("Archive exceeds bounded extraction size")
            target = destination / member.name
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError("Archive path escapes extraction directory")
            data = tar.extractfile(member).read()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            observed[member.name] = sha256(target)
    if observed != expected:
        raise ValueError("Extracted archive manifest mismatch")


def run_consumer(package: Path, consumer: Path, cache: Path, *, hosted_version: str | None = None) -> None:
    consumer.mkdir(parents=True, exist_ok=True)
    dependency = f"'{hosted_version}'" if hosted_version else f"\n    path: '{package.as_posix()}'"
    (consumer / "pubspec.yaml").write_text(
        f"name: ftms_install_check\npublish_to: none\nenvironment:\n  sdk: '>=3.11.0 <4.0.0'\n"
        f"dependencies:\n  {NAME}: {dependency}\n")
    # Consumer code comes from distribution files and uses only the public import.
    shutil.copyfile(package / "example/main.dart", consumer / "main.dart")
    shutil.copyfile(package / "example/capability_evidence.dart", consumer / "capabilities.dart")
    env = registry_environment(cache)
    run(dart(), "pub", "get", cwd=consumer, env=env)
    configuration = json.loads((consumer / ".dart_tool/package_config.json").read_text())
    selected = [p for p in configuration["packages"] if p["name"] == NAME]
    if len(selected) != 1:
        raise ValueError("Consumer did not resolve exactly one FTMS package")
    config_uri = (consumer / ".dart_tool/package_config.json").as_uri()
    resolved_uri = urlparse(urljoin(config_uri, selected[0]["rootUri"]))
    if resolved_uri.scheme != "file":
        raise ValueError("Unexpected installed-package URI")
    installed_path = unquote(resolved_uri.path)
    if os.name == "nt" and re.match(r"^/[A-Za-z]:/", installed_path):
        installed_path = installed_path[1:]
    installed = Path(installed_path).resolve()
    if hosted_version:
        if not installed.is_relative_to(cache.resolve()):
            raise ValueError("Hosted package resolved outside the fresh registry cache")
        # Ensure the registry-resolved code, not just a separately fetched archive,
        # matches the isolated candidate that the examples are testing.
        for source in package.rglob("*"):
            if source.is_file() and not source.name.startswith('.'):
                target = installed / source.relative_to(package)
                if not target.is_file() or sha256(target) != sha256(source):
                    raise ValueError("Registry consumer bytes differ from verified public archive")
    elif installed != package.resolve():
        raise ValueError("Local consumer did not resolve the extracted package")
    run(dart(), "analyze", "--fatal-infos", cwd=consumer, env=env)
    run(dart(), "run", "main.dart", cwd=consumer, env=env)
    run(dart(), "run", "capabilities.dart", cwd=consumer, env=env)
    executable = consumer / ("consumer.exe" if os.name == "nt" else "consumer")
    run(dart(), "compile", "exe", "main.dart", "-o", str(executable), cwd=consumer, env=env)
    run(str(executable), cwd=consumer, env=env)


def main() -> None:
    output = PACKAGE / "build/distribution"
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "package-verification.json"
    report_path.write_text('{"complete":false}\n')
    files = distribution_files()
    manifest = {name: sha256(path) for name, path in sorted(files.items())}
    archive = output / f"{NAME}-{version()}.tar.gz"
    archive.write_bytes(archive_bytes(files))
    if archive.read_bytes() != archive_bytes(files):
        raise ValueError("Local distribution is not reproducible")
    cache_parent = Path.home() / ".cache"
    cache_parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ftms-dart-consumer-", dir=cache_parent) as temporary:
        root = Path(temporary)
        package = root / "package"
        extract_checked(archive, package, manifest)
        run(dart(), "pub", "get", cwd=package)
        run(dart(), "pub", "publish", "--dry-run", cwd=package, output=output / "pub-dry-run.log")
        run_consumer(package, root / "consumer", root / "cache")
    # Source content must not change while the isolated checks run.
    if manifest != {name: sha256(path) for name, path in distribution_files().items()}:
        raise ValueError("Source publication files changed during verification")
    report = {**provenance(), "name": NAME, "version": version(), "complete": True,
              "archiveSha256": sha256(archive), "files": manifest,
              "consumer": "isolated extracted source archive, path dependency; VM and native executable",
              "publicationVerified": False}
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Verified isolated package: {archive}")


if __name__ == "__main__":
    main()
