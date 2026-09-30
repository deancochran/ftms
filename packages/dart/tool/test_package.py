import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from release import validate_tag
from verify_package import archive_bytes, extract_checked, registry_environment, require_current_package


class PackageTests(unittest.TestCase):
    def test_ambient_registry_cannot_redirect_public_consumer(self):
        with patch.dict(os.environ, {"PUB_HOSTED_URL": "https://alternate.invalid", "PUB_CACHE": "old"}):
            env = registry_environment(Path("fresh"))
            self.assertEqual(env["PUB_HOSTED_URL"], "https://pub.dev")
            self.assertEqual(env["PUB_CACHE"], "fresh")

    def test_stale_source_or_manifest_cannot_certify_consumer(self):
        evidence = {"complete": True, "name": "deancochran_ftms", "version": "0.1.0",
                    "sourceCommit": "A", "dirty": False, "files": {}}
        with patch("verify_package.provenance", return_value={"sourceCommit": "B", "dirty": False}), \
                self.assertRaises(ValueError):
            require_current_package(evidence)
        with patch("verify_package.provenance", return_value={"sourceCommit": "A", "dirty": False}), \
                patch("verify_package.distribution_files", return_value={}):
            require_current_package(evidence)
            evidence["files"] = {"changed.dart": "wrong"}
            with self.assertRaises(ValueError):
                require_current_package(evidence)

    def test_archive_is_reproducible_and_rejects_bad_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "lib.dart"
            source.write_text("library;\n")
            first = archive_bytes({"lib/main.dart": source})
            self.assertEqual(first, archive_bytes({"lib/main.dart": source}))
            archive = root / "package.tar.gz"
            archive.write_bytes(first)
            with self.assertRaises(ValueError):
                extract_checked(archive, root / "out", {"lib/main.dart": "wrong"})

    def test_path_traversal_and_links_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, link in [("../escape", False), ("link", True)]:
                archive = root / "bad.tar.gz"
                with tarfile.open(archive, "w:gz") as tar:
                    item = tarfile.TarInfo(name)
                    if link:
                        item.type = tarfile.SYMTYPE
                        item.linkname = "../escape"
                    else:
                        item.size = 1
                    tar.addfile(item, None if link else io.BytesIO(b"x"))
                with self.assertRaises(ValueError):
                    extract_checked(archive, root / "out", {name: "ignored"})

    def test_tag_and_dirty_gates_fail_before_any_external_action(self):
        with self.assertRaises(ValueError):
            validate_tag("v0.1.0")
        with patch("release.provenance", return_value={"dirty": True}), self.assertRaises(ValueError):
            validate_tag("dart-v0.1.0")


if __name__ == "__main__":
    unittest.main()
