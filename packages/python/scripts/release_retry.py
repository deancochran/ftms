"""Plan a PyPI retry without accepting different immutable files."""
from __future__ import annotations
import argparse, hashlib, json, shutil, urllib.error, urllib.request
from pathlib import Path

PACKAGE = "deancochran-ftms"
def plan(version, expected, fetch):
    try: data = json.loads(fetch(f"https://pypi.org/pypi/{PACKAGE}/{version}/json"))
    except urllib.error.HTTPError as error:
        if error.code == 404: return list(expected)
        raise
    remote = {x.get("filename"): x.get("digests", {}).get("sha256") for x in data.get("urls", [])}
    missing=[]
    for name, digest in expected.items():
        if name not in remote: missing.append(name)
        elif remote[name] != digest: raise ValueError(f"existing PyPI artifact differs or lacks digest: {name}")
    return missing
def main():
    p=argparse.ArgumentParser(); p.add_argument("--version",required=True); p.add_argument("--wheel-sha256",required=True); p.add_argument("--sdist-sha256",required=True); p.add_argument("--dist",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    expected={f"deancochran_ftms-{a.version}-py3-none-any.whl":a.wheel_sha256,f"deancochran_ftms-{a.version}.tar.gz":a.sdist_sha256}
    missing=plan(a.version, expected, lambda u: urllib.request.urlopen(u,timeout=30).read())
    for name, digest in expected.items():
        if hashlib.sha256((a.dist / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"local artifact differs: {name}")
    # Never let leftovers from a previous invocation expand the upload set.
    a.output.mkdir(parents=True,exist_ok=False)
    for name in missing: shutil.copyfile(a.dist/name,a.output/name)
    print(f"publish={'true' if missing else 'false'}")
if __name__ == "__main__": main()
