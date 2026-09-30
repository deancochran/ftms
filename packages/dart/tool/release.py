"""Release gates. Only the explicit publish --execute command uploads anything."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
from pathlib import Path

from corpus import PACKAGE, ROOT, git, provenance, sha256
from verify import dart, run
from verify_package import NAME, distribution_files, extract_checked, version
from verify_public import fetch


def public_version_exists(release_version: str, fetch_metadata=fetch) -> bool:
    """Only a definitive 404 permits upload; all other failures block it."""
    try:
        metadata = json.loads(fetch_metadata(
            f"https://pub.dev/api/packages/{NAME}/versions/{release_version}", 1_000_000))
    except urllib.error.HTTPError as error:
        error.close()
        if error.code == 404:
            return False
        raise
    if metadata.get("version") != release_version:
        raise ValueError("Registry version mismatch")
    return True


def validate_tag(tag: str) -> None:
    expected = f"dart-v{version()}"
    if tag != expected:
        raise ValueError(f"Expected exact tag {expected}")
    if provenance()["dirty"]:
        raise ValueError("Release checkout must be clean, including untracked files")
    if git("rev-parse", f"refs/tags/{tag}^{{commit}}") != git("rev-parse", "HEAD"):
        raise ValueError("Release tag does not identify HEAD")
    subprocess.run(["git", "merge-base", "--is-ancestor", "HEAD", "refs/remotes/origin/main"],
                   cwd=ROOT, check=True)
    if f"## {version()}" not in (PACKAGE / "CHANGELOG.md").read_text().splitlines():
        raise ValueError("Missing versioned changelog heading")


def validated_evidence() -> dict:
    evidence = json.loads((PACKAGE / "build/distribution/package-verification.json").read_text())
    identity = provenance()
    if (not evidence.get("complete") or evidence.get("dirty") is not False
            or evidence.get("sourceCommit") != identity["sourceCommit"]
            or identity["dirty"] or evidence.get("version") != version()):
        raise ValueError("Clean matching package verification is required")
    actual = {name: sha256(path) for name, path in distribution_files().items()}
    if actual != evidence["files"]:
        raise ValueError("Publication files differ from verified manifest")
    conformance = json.loads((PACKAGE / "build/vm/verification.json").read_text())
    if (not conformance.get("complete") or conformance.get("dirty") is not False
            or conformance.get("sourceCommit") != identity["sourceCommit"]):
        raise ValueError("Clean matching full-conformance evidence is required")
    for relative, digest in conformance["runnerHashes"].items():
        if sha256(PACKAGE / relative) != digest:
            raise ValueError("Runner/runtime source changed since verification")
    for corpus in conformance["corpora"].values():
        if not corpus["complete"]:
            raise ValueError("Incomplete corpus evidence")
        for relative, digest in corpus["hashes"].items():
            if sha256(ROOT / relative) != digest:
                raise ValueError("Corpus identity changed since verification")
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate-tag", "prepare", "publish"))
    parser.add_argument("--tag", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    validate_tag(args.tag)
    if args.action == "validate-tag":
        return
    if args.action == "prepare":
        run(sys.executable, "tool/verify.py", "--package")
        validated_evidence()
        return
    if not args.execute:
        raise ValueError("Publishing requires --execute and release approval")
    if (os.environ.get("GITHUB_EVENT_NAME") != "push"
            or os.environ.get("GITHUB_REF") != f"refs/tags/{args.tag}"
            or os.environ.get("GITHUB_REPOSITORY") != "deancochran/ftms"):
        raise ValueError("Automated publishing requires the authorized repository tag-push workflow")
    evidence = validated_evidence()
    archive = PACKAGE / f"build/distribution/deancochran_ftms-{version()}.tar.gz"
    if sha256(archive) != evidence["archiveSha256"]:
        raise ValueError("Verified archive changed")
    if public_version_exists(version()):
        # An existing version is acceptable only after exact-file and hosted
        # consumer verification, including retries after an ambiguous upload.
        run(sys.executable, "tool/verify_public.py")
        return
    with tempfile.TemporaryDirectory(prefix="ftms-dart-publish-", dir=Path.home() / ".cache") as temporary:
        stage = Path(temporary)
        extract_checked(archive, stage, evidence["files"])
        run(dart(), "pub", "get", cwd=stage)
        run(dart(), "pub", "publish", "--dry-run", cwd=stage)
        # OIDC is provisioned by setup-dart in the protected workflow environment.
        run(dart(), "pub", "publish", "--force", cwd=stage)
    run(sys.executable, "tool/verify_public.py")


if __name__ == "__main__":
    main()
