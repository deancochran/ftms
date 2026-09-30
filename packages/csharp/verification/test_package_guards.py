import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location("verify_package", Path(__file__).with_name("verify-package.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


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


if __name__ == "__main__":
    unittest.main()
