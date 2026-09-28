#!/usr/bin/env python3
"""Build and validate deterministic FTMS C source archives; never publish."""
import argparse, gzip, hashlib, io, json, re, subprocess, tarfile
from pathlib import Path, PurePosixPath

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[1]
SEMVER = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
HEX = re.compile(r"[0-9a-f]{64}$")

def git(*args): return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
def version_value():
    value = (PACKAGE / "VERSION").read_text().strip()
    if not SEMVER.fullmatch(value): raise ValueError("invalid C package VERSION")
    return value
def package_files(version):
    files = {n: (PACKAGE / n).read_bytes() for n in ("VERSION", "CMakeLists.txt", "conanfile.py", "CHANGELOG.md")}
    files["LICENSE"] = (ROOT / "LICENSE").read_bytes()
    for pattern in ("src/*.c", "include/ftms/*.h", "cmake/*.in"):
        for path in sorted(PACKAGE.glob(pattern)): files[path.relative_to(PACKAGE).as_posix()] = path.read_bytes()
    files["README.md"] = (PACKAGE / "INSTALL.md").read_bytes()
    return files
def ensure_release(version):
    if git("status", "--porcelain", "--untracked-files=all"): raise ValueError("--release requires a clean tracked and untracked checkout")
    tag = f"c-v{version}"
    if git("rev-parse", f"refs/tags/{tag}^{{commit}}") != git("rev-parse", "HEAD"):
        raise ValueError(f"--release requires HEAD to be tagged {tag}")
    return tag
def build(release=False):
    version = version_value(); tag = ensure_release(version) if release else None; files = package_files(version)
    identity = {"packageVersion": version, "releaseCandidate": True, "released": False, "releaseArtifact": release,
                "releaseTag": tag, "sourceCommit": git("rev-parse", "HEAD"),
                "dirty": bool(git("status", "--porcelain", "--untracked-files=all")),
                "files": {n: hashlib.sha256(v).hexdigest() for n, v in sorted(files.items())}}
    files["SOURCE.json"] = (json.dumps(identity, indent=2, sort_keys=True) + "\n").encode()
    out = PACKAGE / "build" / "source-candidate"; out.mkdir(parents=True, exist_ok=True)
    archive = out / f"ftms-c-{version}.tar.gz"
    with archive.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
        with tarfile.open(fileobj=zipped, mode="w") as tar:
            for name, data in sorted(files.items()):
                item = tarfile.TarInfo(f"ftms-c-{version}/{name}"); item.size = len(data); item.mode = 0o644; item.mtime = 0
                tar.addfile(item, io.BytesIO(data))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest(); archive.with_name(archive.name + ".sha256").write_text(f"{digest}  {archive.name}\n")
    print(archive); print("sha256=" + digest); return archive
def safe_member(name, prefix):
    if "\\" in name or not name.startswith(prefix): return False
    rest = name[len(prefix):]; path = PurePosixPath(rest)
    return bool(rest) and not path.is_absolute() and all(p not in ("", ".", "..") and ":" not in p for p in rest.split("/"))
def verify(archive):
    archive = Path(archive); sidecar = archive.with_name(archive.name + ".sha256")
    fields = sidecar.read_text(encoding="utf-8").splitlines()
    if len(fields) != 1 or not re.fullmatch(rf"([0-9a-f]{{64}})  {re.escape(archive.name)}", fields[0]): raise ValueError("invalid checksum sidecar")
    if hashlib.sha256(archive.read_bytes()).hexdigest() != fields[0][:64]: raise ValueError("archive checksum sidecar does not match")
    prefix = archive.name.removesuffix(".tar.gz") + "/"
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers(); names = [m.name for m in members]
        if len(names) != len(set(names)) or any(not safe_member(m.name, prefix) or not m.isfile() for m in members): raise ValueError("archive contains unsafe or duplicate members")
        data = {m.name[len(prefix):]: tar.extractfile(m).read() for m in members}
    if "SOURCE.json" not in data: raise ValueError("SOURCE.json missing")
    identity = json.loads(data.pop("SOURCE.json")); manifest = identity.get("files")
    if not (isinstance(identity.get("packageVersion"), str) and SEMVER.fullmatch(identity["packageVersion"]) and isinstance(identity.get("sourceCommit"), str) and re.fullmatch(r"[0-9a-f]{40}", identity["sourceCommit"]) and isinstance(identity.get("dirty"), bool) and isinstance(identity.get("releaseCandidate"), bool) and identity.get("released") is False and isinstance(identity.get("releaseArtifact"), bool) and (identity.get("releaseTag") is None or identity["releaseTag"] == "c-v" + identity["packageVersion"]) and isinstance(manifest, dict) and all(isinstance(k, str) and isinstance(v, str) and HEX.fullmatch(v) for k,v in manifest.items())): raise ValueError("invalid source identity")
    expected_names = set(package_files(identity["packageVersion"]))
    if set(data) != expected_names or set(manifest) != expected_names or any(hashlib.sha256(data[n]).hexdigest() != manifest[n] for n in data): raise ValueError("SOURCE.json manifest does not exactly match allowed archive files")
    if archive.name != f"ftms-c-{identity['packageVersion']}.tar.gz" or data["VERSION"].decode().strip() != identity["packageVersion"]:
        raise ValueError("archive name, VERSION and manifest version disagree")
    if identity["releaseArtifact"]:
        if identity["dirty"] or identity["releaseTag"] != "c-v" + identity["packageVersion"]:
            raise ValueError("release artifact must be clean and tagged")
    elif identity["releaseTag"] is not None:
        raise ValueError("candidate cannot claim a release tag")
    print("verified " + str(archive)); return identity
if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--release", action="store_true"); parser.add_argument("--verify", type=Path)
    args = parser.parse_args(); verify(args.verify) if args.verify else build(args.release)
