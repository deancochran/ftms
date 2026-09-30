#!/usr/bin/env python3
"""Package, identify, and publish the Rust port. Python 3.12+; stdlib only.

Preparation is credential-free. Publication is opt-in, Actions/tag-only, and
uses Cargo rather than a custom registry upload protocol. Cargo regenerates the
archive: compare its reproducible bytes before upload and the registry checksum
afterward. Never print or persist credentials.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent.parent
REGISTRY = "https://crates.io"
USER_AGENT = "ftms-rust-release (https://github.com/deancochran/ftms)"
# Bounded propagation recovery: 4m15s of backoff plus request/consumer time.
# Never retry the irreversible upload itself.
REGISTRY_DELAYS = (0, 5, 10, 20, 40, 60, 60, 60)
SEMVER = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*)?"
)


class ReleaseError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise ReleaseError(message)


def require_version(version):
    require(isinstance(version, str) and SEMVER.fullmatch(version),
            "version must be SemVer without build metadata")


def public_env():
    # Child builds/consumers must not inherit publishing credentials.
    return {k: v for k, v in os.environ.items()
            if not k.endswith("_TOKEN") and k not in {"ACTIONS_ID_TOKEN_REQUEST_TOKEN"}}


def run(command, *, cwd=None, env=None, capture=False):
    result = subprocess.run(command, cwd=cwd or PACKAGE,
                            env=public_env() if env is None else env,
                            text=True, capture_output=capture)
    require(result.returncode == 0, f"{command[0]} command failed (exit {result.returncode})")
    return result.stdout.strip() if capture else None


def git(*args):
    return run(["git", *args], cwd=ROOT, capture=True)


def manifest():
    data = tomllib.loads((PACKAGE / "Cargo.toml").read_text(encoding="utf-8"))["package"]
    require(data["name"] == "ftms", "unexpected crate identity; review release policy before renaming")
    require_version(data["version"])
    require(data.get("publish") == ["crates-io"], "manifest must restrict publication to crates.io")
    require(data.get("repository") == "https://github.com/deancochran/ftms", "unexpected repository")
    return data


def toolchain():
    channel = tomllib.loads((PACKAGE / "rust-toolchain.toml").read_text(encoding="utf-8"))["toolchain"]["channel"]
    require(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", channel), "release toolchain must be an exact version")
    require(channel == manifest()["rust-version"], "release toolchain and MSRV must match")
    return channel


def source_state(allow_dirty=False):
    commit = git("rev-parse", "HEAD")
    dirty = bool(git("status", "--porcelain", "--untracked-files=all"))
    require(re.fullmatch(r"[0-9a-f]{40}", commit), "invalid source commit")
    require(allow_dirty or not dirty, "release requires a clean tracked checkout")
    return commit, dirty


def validate_tag(actions=False):
    data = manifest()
    commit, _ = source_state()
    tag = f'rust-v{data["version"]}'
    require(os.environ.get("GITHUB_REF_TYPE") == "tag", "release requires a tag event")
    require(os.environ.get("GITHUB_REF_NAME") == tag, "tag must exactly match Cargo.toml version")
    require(git("rev-parse", f"refs/tags/{tag}^{{commit}}") == commit, "tag does not identify this commit")
    if actions:
        require(os.environ.get("GITHUB_ACTIONS") == "true"
                and os.environ.get("GITHUB_EVENT_NAME") == "push"
                and os.environ.get("GITHUB_REPOSITORY") == "deancochran/ftms",
                "publication is restricted to this repository's tag-push workflow")
        require(git("rev-parse", f'{os.environ.get("GITHUB_SHA", "invalid")}^{{commit}}') == commit,
                "event and checkout commits differ")
    git("merge-base", "--is-ancestor", commit, "origin/main")
    headings = (PACKAGE / "CHANGELOG.md").read_text(encoding="utf-8").splitlines()
    require(f'## {data["version"]}' in headings, "missing versioned changelog entry")
    return data, commit, tag


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def output_path(path):
    path = Path(path).resolve()
    require(path.is_relative_to((PACKAGE / "target").resolve()), "release output must be under packages/rust/target")
    path.mkdir(parents=True, exist_ok=True)
    return path


def inspect_archive(path):
    """Reject dangerous/unintended archive content before any extraction."""
    require(Path(path).stat().st_size <= 10 * 1024 * 1024, "oversized crate archive")
    allowed = {"Cargo.toml", "Cargo.toml.orig", "Cargo.lock", "LICENSE", "README.md",
               "CHANGELOG.md", ".cargo_vcs_info.json"}
    required = {"Cargo.toml", "Cargo.toml.orig", "Cargo.lock", "LICENSE", "README.md",
                "CHANGELOG.md", ".cargo_vcs_info.json", "src/lib.rs"}
    contents = {}
    prefix = None
    total = 0
    with tarfile.open(path, "r:gz") as archive:
        for entry in archive:
            parts = PurePosixPath(entry.name).parts
            require(entry.isfile() and len(parts) >= 2 and not entry.name.startswith("/")
                    and "\\" not in entry.name and ":" not in entry.name
                    and all(part not in {".", "..", ""} for part in entry.name.split("/")),
                    "unsafe archive member")
            prefix = prefix or parts[0]
            require(parts[0] == prefix, "multiple archive roots")
            relative = "/".join(parts[1:])
            require(relative not in contents, "duplicate archive member")
            require(len(contents) < 512 and entry.size >= 0, "invalid archive size/member count")
            require(relative in allowed or relative.startswith(("src/", "docs/")),
                    "unexpected file in public crate")
            total += entry.size
            require(total <= 50 * 1024 * 1024, "oversized extracted crate")
            contents[relative] = archive.extractfile(entry).read()
    require(required <= contents.keys(), "missing required package files")
    data = tomllib.loads(contents["Cargo.toml"].decode("utf-8"))["package"]
    require_version(data["version"])
    require(data["name"] == "ftms" and prefix == f'ftms-{data["version"]}', "archive identity mismatch")
    require(data.get("publish") == ["crates-io"], "archive has an unexpected registry policy")
    vcs = json.loads(contents[".cargo_vcs_info.json"])
    require(vcs.get("path_in_vcs") == "packages/rust", "unexpected archive source path")
    require(re.fullmatch(r"[0-9a-f]{40}", vcs["git"]["sha1"]), "invalid archive commit")
    require(type(vcs["git"].get("dirty", False)) is bool, "invalid archive dirty flag")
    return {"name": data["name"], "version": data["version"], "commit": vcs["git"]["sha1"],
            "dirty": vcs["git"].get("dirty", False), "files": sorted(contents)}


def package(target, allow_dirty=False):
    target = Path(target).resolve()
    args = ["cargo", "package", "--locked", "--manifest-path", str(PACKAGE / "Cargo.toml")]
    if allow_dirty:
        args.append("--allow-dirty")
    env = public_env()
    env["CARGO_TARGET_DIR"] = str(target)
    run(args, env=env)
    data = manifest()
    result = target / "package" / f'{data["name"]}-{data["version"]}.crate'
    inspect_archive(result)
    return result


def shared_identity():
    files = sorted(p for folder in [ROOT / "shared/conformance", ROOT / "shared/protocol"]
                   for p in folder.rglob("*") if p.suffix in {".json", ".md"})
    require(files, "canonical shared contracts are missing")
    # Identity of inputs, not an assertion that every corpus is implemented.
    return {p.relative_to(ROOT).as_posix(): sha256(p) for p in files}


def write_json(path, data):
    Path(path).write_text(json.dumps(data, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def sums(directory, registry=False):
    data = json.loads((directory / "release.json").read_text(encoding="utf-8"))
    names = [data["archive"], "release.json"] + (["registry-evidence.json"] if registry else [])
    (directory / "SHA256SUMS").write_text(
        "".join(f"{sha256(directory / name)}  {name}\n" for name in names), encoding="utf-8")


def prepare(directory, allow_dirty=False):
    directory = output_path(directory)
    data = manifest()
    commit, dirty = source_state(allow_dirty)
    built = package(PACKAGE / "target/release-build", allow_dirty)
    identity = inspect_archive(built)
    require(identity["commit"] == commit and identity["dirty"] == dirty, "archive source identity mismatch")
    destination = directory / built.name
    shutil.copyfile(built, destination)
    run([sys.executable, str(PACKAGE / "scripts/consumer.py"), "--archive", str(destination)])
    record = {
        "schemaVersion": 1, "name": data["name"], "version": data["version"],
        "tag": f'rust-v{data["version"]}', "commit": commit, "dirty": dirty,
        "archive": built.name, "sha256": sha256(destination),
        "rustc": run(["rustc", "--version"], capture=True),
        "cargo": run(["cargo", "--version"], capture=True),
        "sharedInputSha256": shared_identity(), "archiveConsumer": "passed",
    }
    write_json(directory / "release.json", record)
    sums(directory)
    print(f'Prepared {built.name}; sha256={record["sha256"]}; dirty={dirty}')
    return record


def checked_record(directory, data, commit):
    directory = output_path(directory)
    record = json.loads((directory / "release.json").read_text(encoding="utf-8"))
    require(isinstance(record, dict), "invalid prepared evidence object")
    name = f'{data["name"]}-{data["version"]}.crate'
    expected = {"schemaVersion": 1, "name": data["name"], "version": data["version"],
                "tag": f'rust-v{data["version"]}', "commit": commit, "dirty": False,
                "archive": name, "archiveConsumer": "passed", "sharedInputSha256": shared_identity()}
    require(all(record.get(k) == v for k, v in expected.items()), "prepared evidence does not match clean release source")
    require(type(record.get("dirty")) is bool and type(record.get("schemaVersion")) is int,
            "invalid evidence field types")
    require(record.get("rustc") == run(["rustc", "--version"], capture=True)
            and record.get("cargo") == run(["cargo", "--version"], capture=True), "prepared toolchain mismatch")
    require(record["rustc"].startswith(f"rustc {toolchain()} ")
            and record["cargo"].startswith(f"cargo {toolchain()} "), "publication requires the pinned MSRV toolchain")
    archive = directory / name
    identity = inspect_archive(archive)
    require(identity["commit"] == commit and not identity["dirty"], "archive is not from the clean release commit")
    require(identity["name"] == data["name"] and identity["version"] == data["version"], "archive version mismatch")
    require(record.get("sha256") == sha256(archive), "prepared archive checksum mismatch")
    return record


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # In particular, never forward GitHub authorization to a redirected host.
        return None


def open_request(request):
    return urllib.request.build_opener(NoRedirect()).open(request, timeout=30)


def json_get(url, missing=False, token=None):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if token is not None:
        location = urllib.parse.urlsplit(url)
        require(location.scheme == "https" and location.netloc == "api.github.com"
                and location.path.startswith("/repos/deancochran/ftms/"), "refusing to send GitHub authorization to another destination")
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with open_request(request) as response:
            require(response.status == 200, "unexpected registry response")
            result = json.load(response)
            require(isinstance(result, dict), "invalid registry response object")
            return result
    except urllib.error.HTTPError as error:
        code = error.code
        error.close()
        if code == 404 and missing:
            return None
        raise ReleaseError(f"registry request failed: HTTP {code}") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        raise ReleaseError("registry request failed; publication state is unknown") from None


def registry_version(record):
    result = json_get(f'{REGISTRY}/api/v1/crates/{record["name"]}/{record["version"]}', missing=True)
    if result is None:
        return None
    value = result.get("version", {})
    require(isinstance(value, dict), "invalid registry version object")
    require(value.get("crate") == record["name"] and value.get("num") == record["version"], "registry version identity mismatch")
    require(value.get("checksum") == record["sha256"], "version already exists with different bytes; refusing to publish")
    require(value.get("yanked") is False, "published version is yanked; refusing automatic repair")
    return value


def publish(directory, execute=False):
    data, commit, _ = validate_tag(actions=execute)
    directory = output_path(directory)
    record = checked_record(directory, data, commit)
    # Cargo has no stable prebuilt-archive publish option. Rebuild with the same
    # pinned compiler before granting the upload process its credential.
    rebuilt = package(PACKAGE / "target/release-rebuild")
    require(sha256(rebuilt) == record["sha256"], "archive is not reproducible from the release checkout")
    exists = registry_version(record) is not None
    if not execute:
        print(f'Publish preflight passed; already published={exists}; no upload attempted.')
        return
    if not exists:
        token = os.environ.get("CARGO_REGISTRY_TOKEN")
        require(bool(token), "CARGO_REGISTRY_TOKEN environment secret is missing")
        env = public_env()
        env["CARGO_REGISTRY_TOKEN"] = token
        env["CARGO_TARGET_DIR"] = str(PACKAGE / "target/release-rebuild")
        # Already built and consumed in the verification job and above. Avoid
        # forwarding the credential to compiler/build-script child processes.
        run(["cargo", "publish", "--locked", "--no-verify", "--registry", "crates-io"], env=env)
        require(sha256(rebuilt) == record["sha256"], "Cargo regenerated different bytes during publication; inspect registry before retrying")
    for delay in REGISTRY_DELAYS:
        if delay:
            time.sleep(delay)
        if registry_version(record) is None:
            continue
        # API visibility need not mean the Cargo index/CDN has propagated yet.
        # Recreate the isolated consumer, not the upload, on a transient failure.
        try:
            run([sys.executable, str(PACKAGE / "scripts/consumer.py"), "--registry-version", data["version"]])
        except ReleaseError:
            continue
        break
    else:
        raise ReleaseError("public registry installation did not converge within the retry budget; rerun at the same tag, never republish changed bytes")
    evidence = {"schemaVersion": 1, "registry": REGISTRY, "name": data["name"],
                "version": data["version"], "commit": commit, "sha256": record["sha256"],
                "registryConsumer": "passed"}
    write_json(directory / "registry-evidence.json", evidence)
    sums(directory, registry=True)
    print("Public registry checksum and isolated installation verified; no existing version was overwritten.")


def release_notes(data, commit):
    lines = (PACKAGE / "CHANGELOG.md").read_text(encoding="utf-8").splitlines()
    start = lines.index(f'## {data["version"]}') + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    changes = "\n".join(lines[start:end]).strip()
    return (f'Rust `{data["name"]}` {data["version"]}, source `{commit}`.\n\n'
            f'{changes}\n\n'
            'Gated host tests, extracted-package and public-registry consumers passed.\n'
            'SHA256SUMS pins the source archive and release/install evidence.\n'
            'No MCU execution, Rust device interoperability or Bluetooth qualification is implied.\n')


def matching_github_metadata(value, tag, data, notes, names):
    require(isinstance(value, dict), "missing GitHub release object")
    require(value.get("tag_name") == tag and value.get("draft") is False
            and value.get("name") == f'FTMS Rust {data["version"]}'
            and isinstance(value.get("body"), str)
            and value["body"].replace("\r\n", "\n") == notes
            and value.get("prerelease") is ("-" in data["version"]), "GitHub release metadata conflicts; refusing to modify it")
    assets = value.get("assets", [])
    require(isinstance(assets, list) and all(isinstance(a, dict) for a in assets)
            and len(assets) == len(names) and {a.get("name") for a in assets} == set(names),
            "GitHub release asset names conflict; refusing to modify them")


def github_release(directory):
    data, commit, tag = validate_tag(actions=True)
    directory = output_path(directory)
    record = checked_record(directory, data, commit)
    evidence = json.loads((directory / "registry-evidence.json").read_text(encoding="utf-8"))
    require(evidence == {"schemaVersion": 1, "registry": REGISTRY, "name": data["name"],
                         "version": data["version"], "commit": commit, "sha256": record["sha256"],
                         "registryConsumer": "passed"}, "missing matching public-installation evidence")
    require(registry_version(record) is not None, "published version is missing")
    sums(directory, registry=True)
    names = [record["archive"], "release.json", "registry-evidence.json", "SHA256SUMS"]
    repo = "deancochran/ftms"
    env = public_env()
    require(bool(os.environ.get("GH_TOKEN")), "GitHub release credential is missing")
    env["GH_TOKEN"] = os.environ["GH_TOKEN"]
    url = f"https://api.github.com/repos/{repo}/releases/tags/{tag}"
    existing = json_get(url, missing=True, token=env["GH_TOKEN"])
    text = release_notes(data, commit)
    notes = directory / "notes.md"
    notes.write_text(text, encoding="utf-8")
    if existing is None:
        command = ["gh", "release", "create", tag, *[str(directory / name) for name in names],
                   "--repo", repo, "--verify-tag", "--title", f'FTMS Rust {data["version"]}',
                   "--notes-file", str(notes), "--latest=false"]
        if "-" in data["version"]:
            command.append("--prerelease")
        run(command, env=env)
        existing = json_get(url, token=env["GH_TOKEN"])
    matching_github_metadata(existing, tag, data, text, names)
    with tempfile.TemporaryDirectory(prefix="ftms-rust-release-check-") as temp:
        for name in names:
            run(["gh", "release", "download", tag, "--repo", repo, "--pattern", name, "--dir", temp], env=env)
            require(sha256(Path(temp) / name) == sha256(directory / name), "GitHub assets differ; refusing overwrite")
    print("Matching GitHub release metadata and asset bytes verified; existing releases are never overwritten.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("toolchain")
    sub.add_parser("validate-tag")
    prep = sub.add_parser("prepare")
    prep.add_argument("--output", type=Path, default=PACKAGE / "target/distribution")
    prep.add_argument("--allow-dirty", action="store_true")
    for name in ["publish", "github-release"]:
        command = sub.add_parser(name)
        command.add_argument("--artifact-dir", type=Path, required=True)
        if name == "publish":
            command.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.command == "toolchain":
        print(toolchain())
    elif args.command == "validate-tag":
        print(validate_tag()[2])
    elif args.command == "prepare":
        prepare(args.output, args.allow_dirty)
    elif args.command == "publish":
        publish(args.artifact_dir, args.execute)
    else:
        github_release(args.artifact_dir)


if __name__ == "__main__":
    try:
        main()
    except (ReleaseError, OSError, KeyError, ValueError, tarfile.TarError) as error:
        # No response bodies, environment values, tokens or request headers.
        print(f"Rust release failed: {error}", file=sys.stderr)
        sys.exit(1)
