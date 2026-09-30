#!/usr/bin/env python3
"""GitHub Actions adapter: verify without secrets, then sign/publish exact gate bytes."""

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

import publish as release

REPOSITORY = "deancochran/ftms"
VERIFIED = release.PACKAGE / ".releases/verified"
CORE_ASSETS = ("central-bundle.zip", "manifest.json", "manifest.json.asc", "signing-public.asc")
EVIDENCE_ASSETS = ("conformance-evidence.zip", "conformance-evidence.zip.asc")
RECEIPTS = ("deployment.json", "central-status.json", "staged-verification.json", "public-verification.json")


def version():
    value = (release.PACKAGE / "VERSION").read_text().strip()
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", value):
        raise release.ReleaseError("VERSION must contain one stable semantic version")
    if "## " + value not in (release.PACKAGE / "CHANGELOG.md").read_text().splitlines():
        raise release.ReleaseError("Missing exact version heading in the Kotlin changelog")
    return value


def source_identity():
    commit = release.clean_commit()
    value = version()
    event = os.environ.get("GITHUB_EVENT_NAME")
    if event != "pull_request":
        if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
            raise release.ReleaseError("Publishing is restricted to the canonical repository")
        ref_type, ref_name = os.environ.get("GITHUB_REF_TYPE"), os.environ.get("GITHUB_REF_NAME")
        if (ref_type, ref_name) not in (("branch", "main"), ("tag", "kotlin-v" + value)):
            raise release.ReleaseError("Release requires main or a version-matched Kotlin tag")
        release.run(["git", "merge-base", "--is-ancestor", commit, "origin/main"])
    return commit, value


def gate():
    commit, value = source_identity()
    if VERIFIED.exists():
        raise release.ReleaseError("Refusing to replace existing CI gate evidence")
    log = release.PACKAGE / ".gradle/ci-verification.log"
    log.parent.mkdir(exist_ok=True)
    release.logged(["bash", str(release.PACKAGE / "verification/verify.sh")], log)
    if release.clean_commit() != commit:
        raise release.ReleaseError("Source changed during CI verification")
    built_version, repo, files = release.publication()
    if value != built_version:
        raise release.ReleaseError("Gradle publication version differs from VERSION")
    VERIFIED.mkdir(parents=True)
    for path in files:
        target = VERIFIED / "repository" / path.relative_to(repo)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    shutil.copyfile(log, VERIFIED / "verification.log")
    for relative in ("conformance", "reports/conformance", "test-results/test"):
        shutil.copytree(release.PACKAGE / "build" / relative, VERIFIED / "evidence" / relative)
    suites = [ET.parse(p).getroot() for p in (VERIFIED / "evidence/test-results/test").glob("TEST-*.xml")]
    counts = {key: sum(int(s.get(key, 0)) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    if counts["tests"] == 0 or any(counts[k] for k in ("failures", "errors", "skipped")):
        raise release.ReleaseError("JUnit accounting is incomplete or contains failures/skips")
    metadata = {"sourceCommit": commit, "version": value, "junit": counts,
                "files": {p.relative_to(VERIFIED).as_posix(): release.sha256(p.read_bytes())
                          for p in sorted(VERIFIED.rglob("*")) if p.is_file()}}
    release.write_json(VERIFIED / "gate.json", metadata)
    with Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"commit={commit}\nversion={value}\n")
        output.write("gate_sha256=" + release.sha256((VERIFIED / "gate.json").read_bytes()) + "\n")
    print(f"Verified Kotlin {value} at {commit}; no publishing secrets used.")


def load_gate(expected_sha256):
    data = (VERIFIED / "gate.json").read_bytes()
    if release.sha256(data) != expected_sha256:
        raise release.ReleaseError("Downloaded gate metadata differs from the verification job output")
    metadata = json.loads(data)
    commit, value = source_identity()
    if metadata["sourceCommit"] != commit or metadata["version"] != value:
        raise release.ReleaseError("Gate artifact identifies a different source/version")
    actual = {p.relative_to(VERIFIED).as_posix() for p in VERIFIED.rglob("*") if p.is_file()}
    if actual != set(metadata["files"]) | {"gate.json"}:
        raise release.ReleaseError("Downloaded gate contains unexpected or missing files")
    for name, expected in metadata["files"].items():
        path = VERIFIED / name
        if path.is_symlink() or not path.resolve().is_relative_to(VERIFIED.resolve()):
            raise release.ReleaseError("Invalid gate artifact path")
        if release.sha256(path.read_bytes()) != expected:
            raise release.ReleaseError("Downloaded artifact differs from the bytes tested in the gate job")
    return metadata


def config_path():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise release.ReleaseError("CI credential setup/cleanup requires a GitHub Actions runner")
    path = Path(os.environ["RUNNER_TEMP"]).resolve() / "ftms-kotlin-publishing"
    if path.is_relative_to(release.ROOT):
        raise release.ReleaseError("Runner credential directory must be outside the checkout")
    return path


def bootstrap():
    config = config_path()
    config.mkdir(mode=0o700)
    for filename, variable in (("central-token", "MAVEN_CENTRAL_TOKEN"),
                               ("signing-passphrase", "MAVEN_SIGNING_PASSPHRASE"),
                               ("signing-fingerprint", "MAVEN_SIGNING_FINGERPRINT")):
        value = os.environ.get(variable, "").strip()
        if not value:
            raise release.ReleaseError("A required Maven Central environment secret/variable is missing")
        (config / filename).write_text(value + "\n")
        (config / filename).chmod(0o600)
    (config / "gnupg").mkdir(mode=0o700)
    private_key = os.environ.get("MAVEN_SIGNING_PRIVATE_KEY", "")
    if "BEGIN PGP PRIVATE KEY BLOCK" not in private_key:
        raise release.ReleaseError("Missing armored Maven signing key")
    release.run(release.signing_command(config) + ["--import"], input=private_key.encode(),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # GPG is invoked by Git without putting the passphrase in argv or the repo.
    wrapper = config / "git-gpg"
    command = release.signing_command(config) + ["--pinentry-mode", "loopback", "--passphrase-file",
                                                 str(config / "signing-passphrase")]
    wrapper.write_text("#!/bin/sh\nexec " + shlex.join(command) + ' "$@"\n')
    wrapper.chmod(0o700)
    probe = config / "signing-check"
    probe.write_text("FTMS CI signing-key verification\n")
    release.sign(config, probe)
    release.verify_signature(config, probe)
    release.central(config, "/deployments?namespace=" + release.NAMESPACE + "&size=1", method="GET")
    print("Environment credentials, namespace authority and signing-key possession verified.")


def cleanup():
    config = config_path()
    if config.exists():
        if config.is_symlink():
            raise release.ReleaseError("Refusing to clean a symlinked credential directory")
        subprocess.run(["gpgconf", "--homedir", str(config / "gnupg"), "--kill", "all"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        shutil.rmtree(config)


def gh(*args, check=True):
    result = release.run(["gh", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE) if check else subprocess.run(
        ["gh", *args], cwd=release.ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result


def github_release(tag):
    result = gh("api", f"repos/{REPOSITORY}/releases/tags/{tag}", check=False)
    try:
        data = json.loads(result.stdout)
    except ValueError:
        raise release.ReleaseError("GitHub release lookup failed; no upload attempted") from None
    if result.returncode:
        if str(data.get("status")) == "404":
            return None
        raise release.ReleaseError("GitHub release lookup failed; no upload attempted")
    return data


def restore(existing):
    names = {item["name"] for item in existing["assets"]}
    if not set(CORE_ASSETS).issubset(names):
        raise release.ReleaseError("Existing release has incomplete bundle/manifest evidence; refusing to replace it")
    if release.RELEASE.exists():
        raise release.ReleaseError("Refusing to overwrite local release evidence")
    release.RELEASE.mkdir(parents=True)
    for name in (*CORE_ASSETS, *EVIDENCE_ASSETS, *RECEIPTS):
        if name in names:
            gh("release", "download", existing["tag_name"], "--repo", REPOSITORY,
               "--pattern", name, "--dir", str(release.RELEASE))


def ensure_tag(config, tag, commit):
    ref = "refs/tags/" + tag
    remote = release.git("ls-remote", "origin", ref)
    if not remote:
        # Do not create a tag using an unverified caller-selected source ref.
        if release.clean_commit() != commit:
            raise release.ReleaseError("Tag source differs from the verified commit")
        release.run(["git", "-c", "user.name=github-actions[bot]", "-c",
                     "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                     "-c", "gpg.format=openpgp", "-c", "gpg.program=" + str(config / "git-gpg"),
                     "-c", "user.signingkey=" + release.fingerprint(config), "tag", "-s", tag,
                     "-m", "FTMS Kotlin/JVM " + tag.removeprefix("kotlin-v"), commit],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        release.run(["git", "-c", "credential.helper=!gh auth git-credential", "push", "origin", ref],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Never force-update a release tag. load_release verifies the signature/object.
    release.run(["git", "fetch", "origin", ref + ":" + ref], stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def package_evidence(config):
    archive = release.RELEASE / "conformance-evidence.zip"
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as output:
        for path in sorted((release.RELEASE / "evidence").rglob("*")):
            if path.is_file() and path.suffix in {".xml", ".json"}:
                output.write(path, path.relative_to(release.RELEASE / "evidence").as_posix())
    release.sign(config, archive)
    release.verify_signature(config, archive)


def save_receipts(tag):
    files = [str(release.RELEASE / name) for name in RECEIPTS if (release.RELEASE / name).is_file()]
    if files:
        gh("release", "upload", tag, "--repo", REPOSITORY, "--clobber", *files)


def verify_existing(config, existing):
    restore(existing)
    manifest = release.load_release(config, require_prepared_checkout=False)
    require_release_identity(manifest, existing["tag_name"])
    if not (release.RELEASE / "deployment.json").exists():
        # The initial 0.1.0 public release predates the durable deployment receipt.
        saved = json.loads((release.RELEASE / "central-status.json").read_text())
        if saved["deploymentState"] != "PUBLISHED":
            raise release.ReleaseError("Published release lacks a published Central receipt")
        release.record_deployment(manifest, saved["deploymentId"])
    release.verify_public(config, manifest)
    return manifest


def require_release_identity(manifest, tag):
    value = tag.removeprefix("kotlin-v")
    if (manifest["tag"] != tag or manifest["version"] != value
            or manifest["coordinates"] != f"{release.NAMESPACE}:{release.ARTIFACT}:{value}"):
        raise release.ReleaseError("Saved release does not identify the requested Kotlin version")


def require_unpublished(value):
    path = f"io/github/deancochran/ftms/{value}/ftms-{value}.pom"
    try:
        release.request(release.MAVEN + "/" + path)
    except release.HttpFailure as error:
        if error.code == 404:
            return
        raise
    raise release.ReleaseError("Version is already on Central without matching release evidence; refusing to reupload")


def deliver(config, metadata, mode):
    tag = "kotlin-v" + metadata["version"]
    existing = github_release(tag)
    if existing and not existing["draft"]:
        verify_existing(config, existing)
        return "Already published; exact public artifacts and consumers verified. No release mutation."
    if mode == "verify":
        return "Credentials and full source/artifact gates passed. Unpublished version; no tag/upload/publication attempted."
    if existing:
        restore(existing)
        manifest = release.load_release(config)
        require_release_identity(manifest, tag)
    else:
        require_unpublished(metadata["version"])
        value, repo, files = release.publication(VERIFIED / "repository")
        if value != metadata["version"]:
            raise release.ReleaseError("Verified publication version mismatch")
        release.assemble(config, metadata["sourceCommit"], value, repo, files,
                         VERIFIED / "verification.log", VERIFIED / "evidence")
        ensure_tag(config, tag, metadata["sourceCommit"])
        manifest = release.load_release(config)
        require_release_identity(manifest, tag)
        package_evidence(config)
        gh("release", "create", tag, "--repo", REPOSITORY, "--verify-tag", "--draft", "--latest=false",
           "--title", "FTMS Kotlin/JVM " + value, "--notes", "Release validation in progress; not yet announced.",
           *(str(release.RELEASE / name) for name in (*CORE_ASSETS, *EVIDENCE_ASSETS)))
    try:
        release.upload(config, manifest, 1800)
        save_receipts(tag)
        release.publish(config, manifest, 1800)
        release.verify_public(config, manifest, timeout=900)
    finally:
        # Only mutable status receipts are updated, never a signed bundle/manifest.
        save_receipts(tag)
    notes = (f"Maven Central: `{manifest['coordinates']}`\n\n"
             f"Source: `{manifest['sourceCommit']}`; signed tag `{tag}`.\n\n"
             "Full canonical conformance, layout matrix, API and isolated Kotlin/Java/Android gates passed. "
             "Public artifact hashes and signatures verified; Kotlin/Java consumers executed and Android APK compiled. "
             "No live Bluetooth or Android runtime qualification is implied.\n\n"
             f"Bundle SHA-256: `{manifest['bundleSha256']}`. Signed manifest and evidence attached.")
    gh("release", "edit", tag, "--repo", REPOSITORY, "--draft=false", "--latest=false", "--notes", notes)
    return "Published to Maven Central; public hashes/signatures/consumers verified; GitHub release completed."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("gate", "bootstrap", "release", "cleanup"))
    parser.add_argument("--mode", choices=("verify", "publish"), default="verify")
    parser.add_argument("--gate-sha256")
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.action == "gate":
            gate()
        elif args.action == "bootstrap":
            bootstrap()
        elif args.action == "cleanup":
            cleanup()
        else:
            metadata = load_gate(args.gate_sha256)
            result = deliver(config_path(), metadata, args.mode)
            print(result)
            with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as summary:
                summary.write("## Kotlin release\n\n" + result + "\n")
    except (release.ReleaseError, OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        message = str(error) if isinstance(error, release.ReleaseError) else type(error).__name__
        print("CI release stopped: " + message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
