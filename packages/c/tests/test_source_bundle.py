import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

PACKAGE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("source_bundle", PACKAGE / "scripts/source-bundle.py")
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


class SourceBundleSafety(unittest.TestCase):
    def setUp(self):
        (PACKAGE / "build").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=PACKAGE / "build", prefix="bundle-tests-")
        self.addCleanup(self.temp.cleanup)
        self.version = bundle.version_value()
        self.archive = Path(self.temp.name) / f"ftms-c-{self.version}.tar.gz"
        self.files = bundle.package_files(self.version)
        self.identity = {"packageVersion": self.version, "releaseCandidate": True,
                         "released": False, "releaseArtifact": False, "releaseTag": None,
                         "sourceCommit": "0" * 40, "dirty": True}

    def write(self, *, extra=None, corrupt_manifest=False):
        identity = dict(self.identity)
        identity["files"] = {name: hashlib.sha256(value).hexdigest() for name, value in self.files.items()}
        if corrupt_manifest:
            identity["files"]["VERSION"] = "0" * 64
        files = {**self.files, "SOURCE.json": json.dumps(identity).encode()}
        with tarfile.open(self.archive, "w:gz") as tar:
            for name, value in files.items():
                member = tarfile.TarInfo(f"ftms-c-{self.version}/{name}")
                member.size = len(value)
                tar.addfile(member, io.BytesIO(value))
            if extra:
                tar.addfile(extra, io.BytesIO(b""))
        digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.archive.with_name(self.archive.name + ".sha256").write_text(f"{digest}  {self.archive.name}\n")

    def verify(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return bundle.verify(self.archive)

    def test_valid_exact_manifest(self):
        self.write()
        self.assertEqual(self.verify()["packageVersion"], self.version)

    def test_corrupt_bytes_and_sidecar_name(self):
        self.write()
        self.archive.write_bytes(self.archive.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.verify()
        self.write()
        sidecar = self.archive.with_name(self.archive.name + ".sha256")
        sidecar.write_text(sidecar.read_text().replace(self.archive.name, "wrong.tar.gz"))
        with self.assertRaisesRegex(ValueError, "sidecar"):
            self.verify()

    def test_manifest_digest_and_undeclared_files(self):
        self.write(corrupt_manifest=True)
        with self.assertRaisesRegex(ValueError, "manifest"):
            self.verify()
        self.files["not-a-package-file"] = b"not allowed even with a valid manifest digest"
        self.write()
        with self.assertRaisesRegex(ValueError, "manifest"):
            self.verify()

    def test_duplicate_member_with_recomputed_checksum(self):
        self.write(extra=tarfile.TarInfo(f"ftms-c-{self.version}/VERSION"))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.verify()

    def test_unsafe_paths_and_links(self):
        for name in ["../escape", "/absolute", "src\\escape", "src/../escape", "src//escape", "C:/escape"]:
            with self.subTest(name=name):
                self.write(extra=tarfile.TarInfo(f"ftms-c-{self.version}/{name}"))
                with self.assertRaisesRegex(ValueError, "unsafe"):
                    self.verify()
        for kind in [tarfile.SYMTYPE, tarfile.LNKTYPE]:
            member = tarfile.TarInfo(f"ftms-c-{self.version}/link")
            member.type = kind
            member.linkname = "../outside"
            self.write(extra=member)
            with self.assertRaisesRegex(ValueError, "unsafe"):
                self.verify()

    def test_version_consistency(self):
        self.files["VERSION"] = b"99.0.0\n"
        self.write()
        with self.assertRaisesRegex(ValueError, "version disagree"):
            self.verify()

    def test_release_metadata_cannot_claim_dirty_or_untagged_release(self):
        self.identity["releaseArtifact"] = True
        self.write()
        with self.assertRaisesRegex(ValueError, "clean and tagged"):
            self.verify()
        self.identity.update(dirty=False, releaseTag=f"c-v{self.version}")
        self.write()
        self.assertTrue(self.verify()["releaseArtifact"])

    def test_release_requires_clean_matching_commit(self):
        with mock.patch.object(bundle, "git", return_value="dirty"), self.assertRaises(ValueError):
            bundle.ensure_release(self.version)
        with mock.patch.object(bundle, "git", side_effect=["", "a" * 40, "b" * 40]), self.assertRaises(ValueError):
            bundle.ensure_release(self.version)
        with mock.patch.object(bundle, "git", side_effect=["", "a" * 40, "a" * 40]):
            self.assertEqual(bundle.ensure_release(self.version), f"c-v{self.version}")

    def test_registry_generation_requires_release_metadata(self):
        self.write()
        output = Path(self.temp.name) / "recipe"
        command = [sys.executable, str(PACKAGE / "scripts/prepare-registry-recipes.py"),
                   str(self.archive), "--tag", f"c-v{self.version}", "--output", str(output)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())
        self.identity.update(releaseArtifact=True, dirty=False, releaseTag=f"c-v{self.version}")
        self.write()
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        recipe = (output / "portfile.cmake").read_text()
        self.assertIn(hashlib.sha512(self.archive.read_bytes()).hexdigest(), recipe)
        self.assertIn(f"releases/download/c-v{self.version}", recipe)
        self.assertNotIn("$ENV{FTMS", recipe)


if __name__ == "__main__":
    unittest.main()
