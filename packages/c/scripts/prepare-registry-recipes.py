#!/usr/bin/env python3
"""Generate (never submit) a vcpkg port for a verified clean tagged release artifact."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile

PACKAGE = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", type=Path, required=True, help="new output directory, normally under build/")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("source_bundle", PACKAGE / "scripts/source-bundle.py")
    source = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    source.verify(args.archive)
    version = source.version_value()
    with tarfile.open(args.archive) as archive:
        identity = json.load(archive.extractfile(f"ftms-c-{version}/SOURCE.json"))
    if (args.tag != f"c-v{version}" or identity["releaseTag"] != args.tag
            or not identity["releaseArtifact"] or identity["dirty"]):
        raise ValueError("registry recipes require the clean, tagged release artifact, not a local candidate")
    args.output.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha512(args.archive.read_bytes()).hexdigest()
    url = f"https://github.com/deancochran/ftms/releases/download/{args.tag}/{args.archive.name}"
    manifest = json.loads((PACKAGE / "packaging/vcpkg/ftms/vcpkg.json").read_text())
    manifest["version-semver"] = version
    (args.output / "vcpkg.json").write_text(json.dumps(manifest, indent=2) + "\n")
    local = (PACKAGE / "packaging/vcpkg/ftms/portfile.cmake").read_text()
    suffix = local[local.index("vcpkg_extract_source_archive_ex("):]
    (args.output / "portfile.cmake").write_text(
        "# Generated from verified release bytes; review before registry submission.\n"
        "vcpkg_check_linkage(ONLY_STATIC_LIBRARY)\n"
        f'vcpkg_download_distfile(ARCHIVE\n  URLS "{url}"\n'
        f'  FILENAME "{args.archive.name}"\n  SHA512 {digest})\n' + suffix)
    print(f"Prepared {args.output}; URL availability and registry acceptance have NOT been verified.")


if __name__ == "__main__":
    main()
