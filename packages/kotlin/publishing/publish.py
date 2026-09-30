#!/usr/bin/env python3
"""Explicit, two-phase Central releases. Python stdlib only; never logs secrets."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
import zipfile

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[1]
# Survives Gradle clean; archive current/ after a release before preparing the next.
RELEASE = PACKAGE / ".releases/current"
CENTRAL = "https://central.sonatype.com/api/v1/publisher"
MAVEN = "https://repo.maven.apache.org/maven2"
NAMESPACE = "io.github.deancochran"
ARTIFACT = "ftms"


class ReleaseError(Exception):
    pass


class HttpFailure(ReleaseError):
    def __init__(self, code):
        self.code = code
        super().__init__(f"HTTP {code}; inspect the Portal for details")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ReleaseError("HTTP redirects are not permitted by the release client")


HTTP = urllib.request.build_opener(NoRedirect())


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def run(args, **kwargs):
    return subprocess.run(args, check=True, cwd=ROOT, **kwargs)


def git(*args):
    return run(["git", *args], stdout=subprocess.PIPE, text=True).stdout.strip()


def clean_commit():
    if git("status", "--porcelain", "--untracked-files=all"):
        raise ReleaseError("Release preparation/publication requires a clean checkout")
    return git("rev-parse", "HEAD")


def private_file(config, name):
    path = config / name
    for item in (config, path):
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ReleaseError("Publishing configuration must be owner-only and not symlinked")
    if not path.is_file() or config.resolve().is_relative_to(ROOT):
        raise ReleaseError("Publishing secrets must be regular files outside the repository")
    return path


def fingerprint(config):
    value = private_file(config, "signing-fingerprint").read_text().strip()
    if not re.fullmatch(r"[A-F0-9]{40}", value):
        raise ReleaseError("Expected a full uppercase OpenPGP signing fingerprint")
    return value


def signing_command(config):
    home = config / "gnupg"
    if home.is_symlink() or home.stat().st_mode & 0o077 or home.stat().st_uid != os.getuid():
        raise ReleaseError("Signing keyring must be owner-only")
    return ["gpg", "--homedir", str(home), "--batch"]


def sign(config, path):
    passfile = private_file(config, "signing-passphrase")
    run(signing_command(config) + ["--pinentry-mode", "loopback", "--passphrase-file",
        str(passfile), "--local-user", fingerprint(config) + "!", "--armor", "--detach-sign",
        "--output", str(path) + ".asc", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def verify_signature(config, path):
    result = run(signing_command(config) + ["--status-fd", "1", "--verify", str(path) + ".asc",
        str(path)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    expected = "[GNUPG:] VALIDSIG " + fingerprint(config) + " "
    if not any(line.startswith(expected) for line in result.stdout.splitlines()):
        raise ReleaseError("Signature does not match the configured release key")


def request(url, *, data=None, headers=None, method=None):
    try:
        with HTTP.open(urllib.request.Request(url, data=data, headers=headers or {}, method=method),
                       timeout=90) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        # Never print server bodies or request headers: they may echo credentials.
        error.close()
        raise HttpFailure(error.code) from None
    except urllib.error.URLError:
        raise ReleaseError("Network request failed; inspect Portal before retrying an upload") from None


def central(config, path, *, data=None, headers=None, method="POST"):
    token = private_file(config, "central-token").read_text().strip()
    try:
        decoded = base64.b64decode(token, validate=True)
        if b":" not in decoded:
            raise ValueError()
    except ValueError:
        raise ReleaseError("Invalid Central token encoding") from None
    return request(CENTRAL + path, data=data, method=method,
                   headers={**(headers or {}), "Authorization": "Bearer " + token})


def publication(repo=None):
    repo = repo or PACKAGE / "build/local-maven"
    poms = list(repo.glob("io/github/deancochran/ftms/*/*.pom"))
    if len(poms) != 1:
        raise ReleaseError("Expected exactly one clean local Maven publication")
    pom = ET.parse(poms[0]).getroot()
    ns = {"m": "http://maven.apache.org/POM/4.0.0"}
    group, artifact, version = (pom.findtext("m:" + key, namespaces=ns)
                                for key in ("groupId", "artifactId", "version"))
    if group != NAMESPACE or artifact != ARTIFACT or not re.fullmatch(r"\d+\.\d+\.\d+", version or ""):
        raise ReleaseError("Unexpected publication coordinates (stable semantic versions only)")
    stem = f"ftms-{version}"
    names = [stem + suffix for suffix in (".pom", ".module", ".jar", "-sources.jar", "-javadoc.jar")]
    files = [poms[0].parent / name for name in names]
    if not all(path.is_file() and path.stat().st_size for path in files):
        raise ReleaseError("Incomplete local Maven publication")
    return version, repo, files


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def logged(args, path):
    with path.open("w") as log:
        try:
            run(args, stdout=log, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            raise ReleaseError(f"Verification failed; see {path.relative_to(ROOT)}") from None


def prepare(config):
    if RELEASE.exists():
        raise ReleaseError("Archive the existing .releases/current evidence before preparing another bundle")
    commit = clean_commit()
    fingerprint(config)
    # Gradle clean deletes build/, so keep the in-progress log outside it.
    log = PACKAGE / ".gradle/publishing-verification.log"
    log.parent.mkdir(exist_ok=True)
    logged(["bash", str(PACKAGE / "verification/verify.sh")], log)
    if clean_commit() != commit:
        raise ReleaseError("Source changed during verification")
    version, repo, files = publication()
    assemble(config, commit, version, repo, files, log, PACKAGE / "build")


def assemble(config, commit, version, repo, files, log, evidence):
    """Sign a verified publication; CI checks its gate digest before calling this."""
    if RELEASE.exists():
        raise ReleaseError("Release evidence already exists; refusing to replace it")
    if clean_commit() != commit:
        raise ReleaseError("Source changed after verification")
    RELEASE.mkdir(parents=True)
    shutil.copyfile(log, RELEASE / "verification.log")
    for relative in ("conformance", "reports/conformance", "test-results/test"):
        shutil.copytree(evidence / relative, RELEASE / "evidence" / relative)
    with (RELEASE / "signing-public.asc").open("wb") as output:
        run(signing_command(config) + ["--armor", "--export", fingerprint(config)],
            stdout=output, stderr=subprocess.DEVNULL)
    bundle_files = {}
    stage = RELEASE / "repository"
    for source in files:
        relative = source.relative_to(repo)
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        sign(config, target)
        verify_signature(config, target)
        data = target.read_bytes()
        for algorithm in ("md5", "sha1", "sha256", "sha512"):
            Path(str(target) + "." + algorithm).write_text(hashlib.new(algorithm, data).hexdigest())
    bundle = RELEASE / "central-bundle.zip"
    with zipfile.ZipFile(bundle, "x", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                relative = path.relative_to(stage).as_posix()
                data = path.read_bytes()
                archive.writestr(relative, data)
                bundle_files[relative] = sha256(data)
    manifest = {"schemaVersion": 1, "sourceCommit": commit, "version": version,
                "coordinates": f"{NAMESPACE}:{ARTIFACT}:{version}", "tag": f"kotlin-v{version}",
                "signingFingerprint": fingerprint(config), "files": bundle_files,
                "bundleSha256": sha256(bundle.read_bytes())}
    manifest["deploymentName"] = manifest["tag"] + "-" + manifest["bundleSha256"][:16]
    write_json(RELEASE / "manifest.json", manifest)
    sign(config, RELEASE / "manifest.json")
    print(f"Prepared {manifest['coordinates']} from {commit}; no remote upload performed.")


def validate_bundle(manifest, bundle):
    if sha256(bundle.read_bytes()) != manifest["bundleSha256"]:
        raise ReleaseError("Bundle changed after verification/signing")
    prefix = f"io/github/deancochran/ftms/{manifest['version']}/"
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != set(manifest["files"]):
            raise ReleaseError("Bundle contents differ from the signed manifest")
        for name in names:
            if not name.startswith(prefix) or "/" in name[len(prefix):] or ".." in name:
                raise ReleaseError("Unexpected Maven bundle path")
            if sha256(archive.read(name)) != manifest["files"][name]:
                raise ReleaseError("Bundle artifact hash mismatch")


def load_release(config, *, require_prepared_checkout=True):
    verify_signature(config, RELEASE / "manifest.json")
    manifest = json.loads((RELEASE / "manifest.json").read_text())
    current_commit = clean_commit()
    if ((require_prepared_checkout and manifest["sourceCommit"] != current_commit)
            or manifest["signingFingerprint"] != fingerprint(config)):
        raise ReleaseError("Prepared release does not identify this clean checkout/signing key")
    validate_bundle(manifest, RELEASE / "central-bundle.zip")
    # Verify a signed, already-pushed tag. Remote tag protection is separate;
    # the immutable source commit and signed manifest are the artifact identity.
    tag = manifest["tag"]
    if git("cat-file", "-t", "refs/tags/" + tag) != "tag":
        raise ReleaseError("Release requires a signed annotated tag, not a lightweight tag")
    if git("rev-parse", tag + "^{commit}") != manifest["sourceCommit"]:
        raise ReleaseError("Release tag does not identify the verified source")
    signature = run(["git", "-c", "gpg.program=gpg", "-c", "gpg.format=openpgp", "verify-tag", "--raw", tag],
                    env={**os.environ, "GNUPGHOME": str(config / "gnupg")},
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    expected = "[GNUPG:] VALIDSIG " + fingerprint(config) + " "
    if not any(line.startswith(expected) for line in signature.stderr.splitlines()):
        raise ReleaseError("Release tag signature does not match the configured signing key")
    tag_object = git("rev-parse", "refs/tags/" + tag)
    refs = dict(line.split()[::-1] for line in git("ls-remote", "origin", "refs/tags/" + tag,
                                                 "refs/tags/" + tag + "^{}").splitlines())
    remote = refs.get("refs/tags/" + tag + "^{}", refs.get("refs/tags/" + tag))
    if remote != manifest["sourceCommit"] or refs.get("refs/tags/" + tag) != tag_object:
        raise ReleaseError("Push the verified release tag before uploading")
    manifest["tagObject"] = tag_object
    return manifest


def deployment(manifest):
    record = json.loads((RELEASE / "deployment.json").read_text())
    if any(record.get(key) != manifest[key] for key in ("bundleSha256", "sourceCommit", "tagObject")):
        raise ReleaseError("Deployment belongs to a different bundle, source commit or tag object")
    return str(uuid.UUID(record["deploymentId"]))


def status(config, deployment_id, manifest):
    result = json.loads(central(config, "/status?id=" + deployment_id))
    if result.get("deploymentId") != deployment_id:
        raise ReleaseError("Unexpected deployment identity in Central response")
    if result.get("deploymentState") in {"VALIDATED", "PUBLISHING", "PUBLISHED"}:
        expected = f"pkg:maven/{NAMESPACE}/{ARTIFACT}@{manifest['version']}"
        purls = result.get("purls")
        # Central can clear purls after the publish transition. Require exact
        # coordinates before the irreversible request; reject conflicting lists
        # afterwards, but use exact public bytes as the final artifact evidence.
        required = result["deploymentState"] == "VALIDATED" or purls not in (None, [])
        if required and purls != [expected]:
            raise ReleaseError("Central deployment coordinates differ from the prepared release")
    # Retain only public release metadata, not raw HTTP responses.
    safe = {key: result[key] for key in ("deploymentId", "deploymentState", "purls") if key in result}
    write_json(RELEASE / "central-status.json", safe)
    return safe["deploymentState"]


def wait_for(config, deployment_id, manifest, targets, timeout):
    deadline = time.monotonic() + timeout
    previous = None
    while True:
        state = status(config, deployment_id, manifest)
        if state != previous:
            print("Central deployment:", state, flush=True)
            previous = state
        if state in targets:
            return state
        if state not in {"PENDING", "VALIDATING", "VALIDATED", "PUBLISHING", "PUBLISHED"}:
            raise ReleaseError("Central validation failed; inspect the deployment in the Portal")
        if time.monotonic() >= deadline:
            raise ReleaseError("Wait timed out; deployment ID saved. Resume without uploading again.")
        time.sleep(10)


def upload(config, manifest, timeout):
    if not (RELEASE / "deployment.json").exists():
        recovered = find_deployment(config, manifest)
        if recovered:
            record_deployment(manifest, recovered)
    if not (RELEASE / "deployment.json").exists():
        boundary = "ftms-" + uuid.uuid4().hex
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="bundle"; '
                'filename="central-bundle.zip"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()
        body += (RELEASE / "central-bundle.zip").read_bytes() + f"\r\n--{boundary}--\r\n".encode()
        query = urllib.parse.urlencode({"name": manifest.get("deploymentName", manifest["tag"]),
                                       "publishingType": "USER_MANAGED"})
        deployment_id = str(uuid.UUID(central(config, "/upload?" + query, data=body,
            headers={"Content-Type": "multipart/form-data; boundary=" + boundary}).decode().strip()))
        record_deployment(manifest, deployment_id)
    wait_for(config, deployment(manifest), manifest, {"VALIDATED", "PUBLISHED"}, timeout)


def record_deployment(manifest, deployment_id):
    write_json(RELEASE / "deployment.json", {"deploymentId": str(uuid.UUID(deployment_id)),
        "bundleSha256": manifest["bundleSha256"], "sourceCommit": manifest["sourceCommit"],
        "tagObject": manifest["tagObject"]})


def find_deployment(config, manifest):
    """Recover a possibly accepted upload by exact bundle-derived name, never guess."""
    name = manifest.get("deploymentName", manifest["tag"])
    matches = []
    page = 0
    while True:
        query = urllib.parse.urlencode({"namespace": NAMESPACE, "deploymentName": name,
                                       "page": page, "size": 100})
        result = json.loads(central(config, "/deployments?" + query, method="GET"))
        matches.extend(item for item in result["deployments"] if item["deploymentName"] == name)
        page += 1
        if page >= result["pageCount"]:
            break
    if len(matches) > 1:
        raise ReleaseError("Multiple Central deployments match this bundle; refusing to choose one")
    if matches and matches[0]["deploymentState"] == "FAILED":
        raise ReleaseError("The existing Central deployment failed; inspect it instead of reuploading")
    return str(uuid.UUID(matches[0]["deploymentId"])) if matches else None


def verify_staged(config, manifest, deployment_id):
    # Compare the actual server-side artifacts, not just a locally recorded UUID.
    verified = {}
    for name, expected in manifest["files"].items():
        if name.endswith((".md5", ".sha1", ".sha256", ".sha512")):
            continue
        data = central(config, f"/deployment/{deployment_id}/download/{name}", method="GET")
        if sha256(data) != expected:
            raise ReleaseError("Staged Central artifact differs from the signed/tested bundle")
        verified[name] = expected
    write_json(RELEASE / "staged-verification.json", {"deploymentId": deployment_id,
        "sourceCommit": manifest["sourceCommit"], "bundleSha256": manifest["bundleSha256"],
        "files": verified})


def publish(config, manifest, timeout):
    deployment_id = deployment(manifest)
    state = status(config, deployment_id, manifest)
    if state == "VALIDATED":
        verify_staged(config, manifest, deployment_id)
        central(config, "/deployment/" + deployment_id, data=b"")
    elif state not in {"PUBLISHING", "PUBLISHED"}:
        raise ReleaseError("Only a VALIDATED deployment may be published")
    wait_for(config, deployment_id, manifest, {"PUBLISHED"}, timeout)


def verify_public(config, manifest, timeout=600):
    if status(config, deployment(manifest), manifest) != "PUBLISHED":
        raise ReleaseError("Central has not reported PUBLISHED")
    destination = RELEASE / "public"
    deadline = time.monotonic() + timeout
    for name, expected in manifest["files"].items():
        while True:
            try:
                data = request(MAVEN + "/" + name)
                break
            except HttpFailure as error:
                if error.code not in {404, 429, 502, 503, 504} or time.monotonic() >= deadline:
                    raise
                time.sleep(10)
        if sha256(data) != expected:
            raise ReleaseError("Public artifact differs from the signed/tested bundle: " + name)
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for path in destination.rglob("*.asc"):
        verify_signature(config, Path(str(path)[:-4]))
    logged(["bash", str(PACKAGE / "verification/verify-consumers.sh"), MAVEN,
            manifest["version"]], RELEASE / "public-consumers.log")
    write_json(RELEASE / "public-verification.json", {"sourceCommit": manifest["sourceCommit"],
        "coordinates": manifest["coordinates"], "bundleSha256": manifest["bundleSha256"],
        "repository": MAVEN, "filesVerified": len(manifest["files"]),
        "kotlinExecution": True, "javaExecution": True, "androidApkBuild": True})
    print("Verified public hashes, signatures, Java/Kotlin execution and Android APK build.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "upload", "publish", "verify"))
    parser.add_argument("--config", type=Path, default=Path.home() / ".config/ftms/publishing")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.action == "prepare":
            prepare(args.config)
        else:
            # Read-only verification may use newer tooling; upload/publish still
            # require the prepared source checkout. The original signed tag and
            # manifest remain mandatory and are never rewritten.
            manifest = load_release(args.config, require_prepared_checkout=args.action != "verify")
            if args.action == "upload":
                upload(args.config, manifest, args.timeout)
            elif args.action == "publish":
                publish(args.config, manifest, args.timeout)
            else:
                verify_public(args.config, manifest, timeout=args.timeout)
    except (ReleaseError, OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        # CalledProcessError/OSError details may include local private paths; no traceback.
        message = str(error) if isinstance(error, ReleaseError) else type(error).__name__
        print("Release stopped: " + message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
