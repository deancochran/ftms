import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest import mock
import urllib.error
import subprocess
import os
import copy

spec = importlib.util.spec_from_file_location("verify_package", Path(__file__).with_name("verify-package.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

release_spec = importlib.util.spec_from_file_location("release", Path(__file__).parents[1] / "publishing/release.py")
release = importlib.util.module_from_spec(release_spec)
release_spec.loader.exec_module(release)


class PackageGuardTests(unittest.TestCase):
    def test_canonical_version(self):
        for version in ("0.1.0-alpha.1", "1.0.0", "2147483647.0.0"):
            self.assertEqual(module.validate_version(version), version)
        for version in ("1.2", "1.2.3.0", "01.2.3", "1.02.3", "1.2.03", "1.2.3+build.7",
                        "1.2.3-alpha.01", "1.2.3-Alpha", "2147483648.0.0", "1.2.3\n", ""):
            with self.subTest(version=version), self.assertRaises(ValueError):
                module.validate_version(version)

    def test_signature_is_only_permitted_payload_difference(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for name, payload, signature in (("local", b"same", False), ("public", b"same", True), ("changed", b"different", True)):
                with zipfile.ZipFile(directory / name, "w") as archive:
                    archive.writestr("lib/net10.0/DeanCochran.Ftms.dll", payload)
                    if signature:
                        archive.writestr(".signature.p7s", b"test-only-not-a-valid-signature")
            local = module.payload_manifest(directory / "local")
            self.assertEqual(local, module.payload_manifest(directory / "public", True))
            self.assertNotEqual(local, module.payload_manifest(directory / "changed", True))
            with self.assertRaises(ValueError):
                module.payload_manifest(directory / "public")
        # Payload equivalence is deliberately NOT a cryptographic signature check.

    def test_archive_rejects_path_traversal_and_duplicate_entries(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../escape", b"bad")
            with self.assertRaises(ValueError):
                module.payload_manifest(path)
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("duplicate", b"a")
                with self.assertWarns(UserWarning):
                    archive.writestr("duplicate", b"b")
            with self.assertRaises(ValueError):
                module.payload_manifest(path)

    def test_public_mode_reports_its_source_label(self):
        self.assertEqual(module.consumers.__defaults__, ("isolated local NuGet feed", ""))

    def test_public_download_retries_only_absence_and_transient_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "package.nupkg"
            missing = urllib.error.HTTPError("https://example.invalid", 404, "missing", {}, None)
            forbidden = urllib.error.HTTPError("https://example.invalid", 403, "forbidden", {}, None)
            with mock.patch.object(release.urllib.request, "urlopen", side_effect=forbidden):
                with self.assertRaises(urllib.error.HTTPError):
                    release.download("https://example.invalid", target)

            with mock.patch.object(release.urllib.request, "urlopen", side_effect=missing), mock.patch.object(release.time, "sleep"):
                with self.assertRaises(RuntimeError):
                    release.download("https://example.invalid", target, attempts=3, delay=0)

    def test_manifest_binds_exact_artifacts_and_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            feed = root / "artifacts/packages"
            feed.mkdir(parents=True)
            files = {}
            payloads = {}
            for ext in ("nupkg", "snupkg"):
                path = feed / f"DeanCochran.Ftms.0.1.0-alpha.1.{ext}"
                with zipfile.ZipFile(path, "w") as archive:
                    archive.writestr("test-entry", b"test-only")
                files[path.name] = {"sha256": release.sha(path), "size": path.stat().st_size}
                payloads[path.name] = module.payload_manifest(path)
            manifest = {"packageId": "DeanCochran.Ftms", "version": "0.1.0-alpha.1", "sourceCommit": "a" * 40,
                        "dirty": False, "files": files, "payloads": payloads}
            with mock.patch.object(release, "HERE", root), mock.patch.object(release, "run", return_value="a" * 40), mock.patch.object(release, "version", return_value="0.1.0-alpha.1"):
                self.assertEqual(release.validate_manifest(manifest), "0.1.0-alpha.1")
                for key, bad in (("dirty", True), ("sourceCommit", "b" * 40), ("version", "0.1.0-alpha.2"), ("packageId", "Other")):
                    changed = copy.deepcopy(manifest)
                    changed[key] = bad
                    with self.subTest(key=key), self.assertRaises(ValueError):
                        release.validate_manifest(changed)
                changed = copy.deepcopy(manifest)
                changed["files"]["unexpected"] = {}
                with self.assertRaises(ValueError):
                    release.validate_manifest(changed)
                path.write_bytes(b"tampered")
                with self.assertRaises(ValueError):
                    release.validate_manifest(manifest)

    def test_real_signed_tag_and_rejected_identity_variants(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def git(*args):
                return subprocess.check_output(["git", *args], cwd=root, text=True, stderr=subprocess.PIPE).strip()
            git("init", "-b", "main")
            git("config", "user.name", "Release Test")
            git("config", "user.email", "release@example.invalid")
            git("config", "commit.gpgsign", "false")
            git("commit", "--allow-empty", "-m", "fixture")
            git("update-ref", "refs/remotes/origin/main", "HEAD")
            key = root / "key"
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
            signer = " ".join(key.with_suffix(".pub").read_text().split()[:2])
            tag = "csharp-v0.1.0-alpha.1"
            git("-c", "gpg.format=ssh", "-c", f"user.signingkey={key}", "tag", "-s", tag, "-m", "test release")
            tag_object = git("rev-parse", tag)
            # Existing run() default captures the product root; replace only the cwd wrapper.
            def run_in_fixture(*args, **kwargs):
                return subprocess.check_output(args, cwd=root, env=kwargs.get("env"), text=True, stderr=subprocess.PIPE)
            with mock.patch.object(release, "run", side_effect=run_in_fixture), mock.patch.dict(os.environ, {"CSHARP_RELEASE_SIGNER": signer}):
                release.validate_tag(tag, "0.1.0-alpha.1", tag_object)
                with self.assertRaises(ValueError):
                    release.validate_tag(tag, "0.1.0-alpha.2", tag_object)
                with self.assertRaises(ValueError):
                    release.validate_tag(tag, "0.1.0-alpha.1", "0" * 40)
                git("commit", "--allow-empty", "-m", "different checkout")
                with self.assertRaises(ValueError):
                    release.validate_tag(tag, "0.1.0-alpha.1", tag_object)


if __name__ == "__main__":
    unittest.main()
