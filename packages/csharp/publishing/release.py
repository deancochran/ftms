"""Release-only checks for the immutable C# NuGet artifact.

This deliberately has no credentials: the workflow supplies OIDC to NuGet/login and
uses this program only to make the artifact and public-registry evidence auditable.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / "verification"))
import importlib.util
spec = importlib.util.spec_from_file_location("verify_package", HERE / "verification/verify-package.py")
verify_package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_package)

PACKAGE_ID = "DeanCochran.Ftms"
NUGET = "https://api.nuget.org/v3-flatcontainer"
NUGET_REPOSITORY_CERT_SHA256 = "1F4B311D9ACC115C8DC8018B5A49E00FCE6DA8E2855F9F014CA6F34570BC482D"

def run(*args, cwd=ROOT, env=None):
    return subprocess.run(args, cwd=cwd, env=env, check=True, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT).stdout

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def version():
    return verify_package.validate_version((HERE / "VERSION").read_text().strip())

def require_clean():
    if run("git", "status", "--porcelain", "--untracked-files=all").strip():
        raise ValueError("Release source must be clean before verification artifacts are created")

def validate_tag(value, release_version, pushed_commit):
    if value != f"csharp-v{release_version}":
        raise ValueError("Release tag must exactly match csharp-vVERSION")
    if run("git", "cat-file", "-t", f"refs/tags/{value}").strip() != "tag":
        raise ValueError("Release tag must be an annotated tag")
    if run("git", "rev-parse", f"{value}^{{commit}}").strip() != pushed_commit:
        raise ValueError("Push event commit does not match the signed tag target")
    signer = os.environ.get("CSHARP_RELEASE_SIGNER", "").strip()
    if not signer.startswith("ssh-") or len(signer.split()) != 2:
        raise ValueError("CSHARP_RELEASE_SIGNER must be the pinned SSH public key (type and base64 only)")
    with tempfile.TemporaryDirectory() as td:
        allowed = Path(td) / "allowed_signers"
        allowed.write_text(f"deancochran namespaces=\"git\" {signer}\n")
        run("git", "-c", "gpg.format=ssh", "-c", f"gpg.ssh.allowedSignersFile={allowed}", "verify-tag", value)
    tagged = run("git", "rev-list", "-n", "1", value).strip()
    head = run("git", "rev-parse", "HEAD").strip()
    if tagged != head:
        raise ValueError("Checked-out commit is not the annotated tag target")
    run("git", "merge-base", "--is-ancestor", tagged, "origin/main")

def identity_manifest(release_version):
    feed = HERE / "artifacts/packages"
    files = [feed / f"{PACKAGE_ID}.{release_version}.{ext}" for ext in ("nupkg", "snupkg")]
    if set(feed.iterdir()) != set(files):
        raise ValueError("Release feed must contain exactly the main and symbols packages")
    report = json.loads((HERE / "artifacts/package-verification.json").read_text())
    commit = run("git", "rev-parse", "HEAD").strip()
    if report["sourceCommit"] != commit or report["dirty"] or not report["complete"]:
        raise ValueError("Local verification report is incomplete, dirty, or from another commit")
    for path in files:
        if report["artifactSha256"].get(path.name) != sha(path):
            raise ValueError("Package bytes changed after consumer verification")
    manifest = {"packageId": PACKAGE_ID, "version": release_version, "sourceCommit": commit,
                "dirty": False, "files": {p.name: {"sha256": sha(p), "size": p.stat().st_size} for p in files},
                "payloads": {p.name: verify_package.audit_archive(p, release_version, p.suffix == ".snupkg") for p in files}}
    output = HERE / "artifacts/release-manifest.json"
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest

def gate(tag, pushed_commit):
    release_version = version()
    require_clean()
    validate_tag(tag, release_version, pushed_commit)
    if not re.search(r"^## " + re.escape(release_version) + r"\s*$", (HERE / "CHANGELOG.md").read_text(), re.MULTILINE):
        raise ValueError("CHANGELOG must contain the release version heading")
    env = dict(os.environ, FTMS_VERIFY_AOT="1", FTMS_AOT_RID="linux-x64")
    subprocess.run(["bash", "verification/verify.sh"], cwd=HERE, env=env, check=True)
    manifest = identity_manifest(release_version)
    print(json.dumps({"commit": manifest["sourceCommit"], "version": release_version,
                      "manifestSha256": sha(HERE / "artifacts/release-manifest.json")}, sort_keys=True))

def download(url, target, attempts=60, delay=10):
    # A package can take time to appear; only absence and transport/server errors retry.
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                target.write_bytes(response.read())
                return
        except urllib.error.HTTPError as error:
            if error.code not in (404, 408, 429) and error.code < 500:
                raise
        except urllib.error.URLError:
            pass
        if attempt == attempts - 1:
            raise RuntimeError(f"NuGet package was unavailable after bounded retries: {url}")
        time.sleep(delay)

def validate_manifest(manifest):
    if manifest["packageId"] != PACKAGE_ID or manifest["dirty"] is not False:
        raise ValueError("Invalid release identity manifest")
    release_version = verify_package.validate_version(manifest["version"])
    if release_version != version() or manifest["sourceCommit"] != run("git", "rev-parse", "HEAD").strip():
        raise ValueError("Release manifest does not identify this checkout/version")
    expected = {f"{PACKAGE_ID}.{release_version}.{ext}" for ext in ("nupkg", "snupkg")}
    if set(manifest["files"]) != expected or set(manifest["payloads"]) != expected:
        raise ValueError("Manifest must identify exactly the two release artifacts")
    for name in expected:
        path = HERE / "artifacts/packages" / name
        entry = manifest["files"][name]
        if path.stat().st_size != entry["size"] or sha(path) != entry["sha256"]:
            raise ValueError("Release artifact transfer digest mismatch")
        if verify_package.payload_manifest(path) != manifest["payloads"][name]:
            raise ValueError("Release artifact payload manifest mismatch")
    return release_version

def public_verify(manifest_path, existing=False):
    manifest = json.loads(Path(manifest_path).read_text())
    release_version = validate_manifest(manifest)
    output = HERE / "artifacts/public-package-verification.json"
    with tempfile.TemporaryDirectory(prefix="nuget-public-", dir=HERE / "artifacts") as td:
        directory = Path(td)
        public = directory / f"{PACKAGE_ID}.{release_version}.nupkg"
        download(f"{NUGET}/{PACKAGE_ID.lower()}/{release_version}/{PACKAGE_ID.lower()}.{release_version}.nupkg", public)
        # --all validates the repository signature under the explicit NuGet.org pin.
        checked = run("dotnet", "nuget", "verify", str(public), "--all", "--certificate-fingerprint", NUGET_REPOSITORY_CERT_SHA256,
                      "--verbosity", "normal", env=dict(os.environ, DOTNET_CLI_UI_LANGUAGE="en-US"))
        if "Signature type: Repository" not in checked or "Service index: https://api.nuget.org/v3/index.json" not in checked:
            raise ValueError("NuGet verification did not prove the pinned nuget.org repository signature")
        local_name = f"{PACKAGE_ID}.{release_version}.nupkg"
        local_manifest = manifest["payloads"][local_name]
        if verify_package.payload_manifest(public, True) != local_manifest:
            raise ValueError("Public nupkg payload differs from the tested artifact (only .signature.p7s may differ)")
        consumer_results = verify_package.consumers("https://api.nuget.org/v3/index.json", release_version,
                                                    directory / "consumers", "nuget.org public feed", report_prefix="public-")
        output.write_text(json.dumps({"packageId": PACKAGE_ID, "version": release_version, "complete": True,
            "source": "nuget.org public flat-container", "sourceCommit": manifest["sourceCommit"],
            "repositoryCertificateSha256": NUGET_REPOSITORY_CERT_SHA256,
            "uploadedWholeSha256": manifest["files"][local_name]["sha256"],
            "downloadedWholeSha256": sha(public), "payloadEquivalent": True, "repositorySignatureVerified": True,
            "consumers": consumer_results, "symbols": ("not submitted: main package already existed" if existing else
            "submitted to NuGet; registry indexing is asynchronous")}, indent=2) + "\n")

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("gate"); p.add_argument("--tag", required=True); p.add_argument("--pushed-commit", required=True)
    p = sub.add_parser("public-verify"); p.add_argument("--manifest", required=True); p.add_argument("--existing", action="store_true")
    args = parser.parse_args()
    if args.command == "gate": gate(args.tag, args.pushed_commit)
    else: public_verify(args.manifest, args.existing)

if __name__ == "__main__":
    main()
