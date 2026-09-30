#!/usr/bin/env python3
"""Fail-closed release evidence assembly; publication is a separate workflow step."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def git(*arguments):
    return subprocess.check_output(["git", *arguments], cwd=ROOT, text=True).strip()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    tag, evidence = sys.argv[1], Path(sys.argv[2])
    version = (ROOT / "packages/swift/VERSION").read_text().strip()
    require(re.fullmatch(r"\d+\.\d+\.\d+", version), "invalid Swift version")
    require(tag == f"swift-v{version}", "tag differs from package version")
    require(f"## {version}" in (ROOT / "packages/swift/CHANGELOG.md").read_text().splitlines(), "missing changelog")
    head = git("rev-parse", "HEAD")
    require(git("rev-parse", f"{tag}^{{commit}}") == head, "tag differs from checked-out source")
    require(not git("status", "--porcelain"), "release requires clean source")
    subprocess.run(["git", "merge-base", "--is-ancestor", head, "origin/main"], cwd=ROOT, check=True)
    output = ROOT / ".build/swift-release"
    output.mkdir(parents=True, exist_ok=True)
    assets = []
    for host in ["linux", "apple"]:
        for kind in ["verification", "consumer"]:
            source = evidence / f"swift-{host}-evidence" / f"swift-{kind}-report.json"
            report = json.loads(source.read_text())
            if kind == "verification":
                require(report.get("swiftVerification") == "passed" and report.get("consumer") == "passed", "native verification failed")
                require(report.get("gitHead") == head and report.get("sourceDirty") is False, "native evidence source mismatch")
                totals = report["nativeCaseReport"]["totals"]
                require(totals["passed"] == totals["discovered"] == 282 and all(totals[k] == 0 for k in ["failed", "skipped", "unsupported", "unresolved"]), "incomplete corpus evidence")
                for name, digest in report["sha256"].items():
                    require(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, f"corpus identity mismatch: {name}")
            else:
                require(report.get("passed") is True and report.get("resolvedCommit") == head and report.get("revision") == tag, "tag installation did not pass at release source")
                require(report.get("repository") == "https://github.com/deancochran/ftms.git", "consumer evidence must use the canonical public repository")
                if host == "apple":
                    require({b["platform"] for b in report["appleBuilds"] if b["passed"] and b.get("resolvedCommit") == head} == {"macos", "ios", "tvos", "watchos", "visionos"}, "incomplete Apple SDK evidence")
            target = output / f"swift-{host}-{kind}.json"
            target.write_bytes(source.read_bytes())
            assets.append(target)
    (output / "SHA256SUMS").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in assets))
    (output / "notes.md").write_text(f'''Native Swift FTMS protocol package **{version}**.

Source commit: `{head}`. Specification: FTMS 1.0 + EC23224. Corpus versions and
SHA-256 identities are recorded in the attached verification reports.

Install with SwiftPM (Swift 6.0+), then select product `FTMS`:

```swift
.package(url: "https://github.com/deancochran/ftms.git", revision: "{tag}")
```

For an immutable pin, replace the tag with `{head}`. Do **not** use `from:` or
`.exact()` semantic-version requirements in this multi-package repository: its
ordinary `v*` version tags belong to npm, not Swift.

Verified on Linux and macOS: 282 canonical fixtures, 181,760 measurement layouts,
46 sentinel cases, 47 reserved-bit cases, 315 incomplete prefixes, release builds
and isolated public Git/tag consumers. The installed consumer also compiled for
macOS 13, iOS 16, tvOS 16, watchOS 9 and visionOS 1 deployment targets using Apple SDKs.
These are SDK build results, not
runtime tests on every OS version or on physical Apple devices.

Includes Features, five ranges, all six measurement families, all 21 controls,
responses/statuses, range inspection and static capabilities. No BLE lifecycle,
manufacturer-specific behavior, real-device interoperability or Bluetooth
qualification is claimed. npm/C releases and tags are unchanged.

See [package documentation](https://github.com/deancochran/ftms/blob/{tag}/packages/swift/README.md)
and [changelog](https://github.com/deancochran/ftms/blob/{tag}/packages/swift/CHANGELOG.md).
''')


if __name__ == "__main__":
    main()
