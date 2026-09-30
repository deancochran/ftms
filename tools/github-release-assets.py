#!/usr/bin/env python3
"""Safely resume a GitHub release from exact local artifact bytes."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess
from pathlib import Path

def sha256(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def plan_release(tag: str, commit: str, local: dict[str, str], release: dict | None) -> list[str]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", tag): raise ValueError("malformed release tag")
    if not re.fullmatch(r"[0-9a-f]{40}", commit): raise ValueError("release commit must be a full SHA-1")
    if release is None: raise ValueError("resolved tag identity is required even before creation")
    # This is the resolved tag object identity, never targetCommitish (which is
    # commonly the literal branch name used when the release was created).
    if release["commit"] != commit: raise ValueError("release tag resolves to a different commit")
    if release.get("exists") is False: return ["create"]
    remote = release["assets"]
    if set(remote) - set(local): raise ValueError("unexpected public release assets")
    actions = []
    for name, digest in local.items():
        if name not in remote: actions.append(f"upload:{name}")
        elif remote[name] != digest: raise ValueError(f"existing asset differs: {name}")
    return actions or ["continue"]

def command(args: list[str], *, binary=False):
    result = subprocess.run(args, check=False, capture_output=True, text=not binary)
    if result.returncode: raise RuntimeError(result.stderr if not binary else result.stderr.decode())
    return result.stdout

def remote_release(repo: str, tag: str, call=command, *, download=False) -> dict | None:
    # Resolve the tag through GitHub's commits API, which peels annotated tags.
    commit = call(["gh", "api", f"repos/{repo}/commits/{tag}", "--jq", ".sha"]).strip()
    try:
        raw = call(["gh", "api", f"repos/{repo}/releases/tags/{tag}"])
    except RuntimeError as error:
        if "HTTP 404" in str(error): return {"commit": commit, "exists": False, "assets": {}}
        raise
    data = json.loads(raw); assets = {}
    for asset in data.get("assets", []):
        name = asset.get("name")
        if not isinstance(name, str): raise ValueError("release asset without name")
        if name in assets: raise ValueError("duplicate public release asset name")
        digest = asset.get("digest")
        if not download and isinstance(digest, str) and digest.startswith("sha256:"):
            assets[name] = digest.removeprefix("sha256:")
        else:
            # Old GitHub API payloads omit digest. Download and hash rather than
            # treating the asset as missing or trusting a null digest.
            url = asset.get("url")
            if not isinstance(url, str): raise ValueError(f"release asset {name} has no API URL")
            assets[name] = hashlib.sha256(call(["gh", "api", "-H", "Accept: application/octet-stream", url], binary=True)).hexdigest()
    return {"commit": commit, "assets": assets}

def run(args):
    files = [Path(value) for value in args.files]; local = {p.name: sha256(p) for p in files}
    if len(local) != len(files): raise ValueError("duplicate local artifact names")
    release = remote_release(args.repo, args.tag)
    actions = plan_release(args.tag, args.commit, local, release)
    if actions == ["create"]:
        create = ["gh", "release", "create", args.tag, "--repo", args.repo, "--target", args.commit, "--verify-tag", "--title", args.title, "--notes-file", args.notes]
        if args.not_latest: create.append("--latest=false")
        subprocess.run([*create, *map(str, files)], check=True)
    for action in actions:
        if action.startswith("upload:"):
            name = action.split(":", 1)[1]
            subprocess.run(["gh", "release", "upload", args.tag, "--repo", args.repo, str(next(p for p in files if p.name == name)), "--clobber=false"], check=True)
    verified = remote_release(args.repo, args.tag, download=True)
    if plan_release(args.tag, args.commit, local, verified) != ["continue"]:
        raise ValueError("public release remains incomplete after upload")
    print(json.dumps({"tag": args.tag, "actions": actions, "sha256": local}, sort_keys=True))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--tag", required=True); parser.add_argument("--commit", required=True); parser.add_argument("--repo", required=True); parser.add_argument("--title", required=True); parser.add_argument("--notes", required=True); parser.add_argument("--not-latest", action="store_true"); parser.add_argument("files", nargs="+"); run(parser.parse_args())
