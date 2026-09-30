"""Compile/test a real Flutter consumer of the extracted Dart distribution."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from corpus import PACKAGE, provenance, sha256
from verify import run
from verify_package import extract_checked, registry_environment, require_current_package, version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("android", "ios"), required=True)
    args = parser.parse_args()
    flutter = os.environ.get("FLUTTER") or shutil.which("flutter")
    if not flutter:
        raise RuntimeError("Flutter SDK required; this check cannot be skipped as passing")
    output = PACKAGE / "build" / f"flutter-{args.target}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('{"complete":false}\n')
    evidence = json.loads((PACKAGE / "build/distribution/package-verification.json").read_text())
    require_current_package(evidence)
    archive = PACKAGE / f"build/distribution/deancochran_ftms-{version()}.tar.gz"
    if sha256(archive) != evidence["archiveSha256"]:
        raise ValueError("Package archive digest mismatch")
    with tempfile.TemporaryDirectory(prefix="ftms-dart-flutter-", dir=Path.home() / ".cache") as temporary:
        root = Path(temporary)
        package, consumer = root / "package", root / "consumer"
        extract_checked(archive, package, evidence["files"])
        env = registry_environment(root / "cache")
        run(flutter, "create", "--empty", "--platforms=android,ios", "--project-name=ftms_consumer",
            str(consumer), cwd=root, env=env)
        pubspec = consumer / "pubspec.yaml"
        contents = pubspec.read_text()
        if contents.count("\ndependencies:\n") != 1:
            raise ValueError("Unexpected Flutter template manifest")
        pubspec.write_text(contents.replace("\ndependencies:\n",
            f"\ndependencies:\n  deancochran_ftms:\n    path: '{package.as_posix()}'\n"))
        shutil.copyfile(package / "example/main.dart", consumer / "lib/protocol_example.dart")
        (consumer / "lib/main.dart").write_text(
            "import 'package:flutter/material.dart';\n"
            "import 'protocol_example.dart' as protocol;\n"
            "void main() { protocol.main(); runApp(const MaterialApp(home: Text('FTMS consumer'))); }\n")
        test = consumer / "test/protocol_test.dart"
        test.parent.mkdir(exist_ok=True)
        test.write_text("import 'package:flutter_test/flutter_test.dart';\n"
                        "import '../lib/protocol_example.dart' as protocol;\n"
                        "void main() { test('installed FTMS public interface', protocol.main); }\n")
        run(flutter, "pub", "get", cwd=consumer, env=env)
        run(flutter, "test", "test/protocol_test.dart", cwd=consumer, env=env)
        if args.target == "android":
            run(flutter, "build", "apk", "--debug", "--no-pub", cwd=consumer, env=env)
        else:
            run(flutter, "build", "ios", "--simulator", "--debug", "--no-codesign", "--no-pub", cwd=consumer, env=env)
    require_current_package(evidence)
    output.write_text(json.dumps({**provenance(), "complete": True, "target": args.target,
        "flutter": json.loads(subprocess.check_output([flutter, "--version", "--machine"], text=True)),
        "packageArchiveSha256": evidence["archiveSha256"], "deviceExecution": False}, indent=2) + "\n")


if __name__ == "__main__":
    main()
