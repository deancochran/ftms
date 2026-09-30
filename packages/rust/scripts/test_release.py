"""Offline release-policy regressions. No credentials, uploads or Git commits."""

import io
from contextlib import redirect_stdout
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

import release


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(redirect_stdout(io.StringIO()))
        temporary = tempfile.TemporaryDirectory(prefix="ftms-rust-release-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package = self.root / "packages/rust"
        self.package.mkdir(parents=True)
        self.commit = "a" * 40
        self.manifest = (
            '[package]\nname = "ftms"\nversion = "0.1.0"\nrust-version = "1.85.1"\n'
            'publish = ["crates-io"]\nrepository = "https://github.com/deancochran/ftms"\n'
        )
        (self.package / "Cargo.toml").write_text(self.manifest)
        (self.package / "rust-toolchain.toml").write_text('[toolchain]\nchannel = "1.85.1"\n')
        (self.package / "CHANGELOG.md").write_text("# Changelog\n\n## 0.1.0\n")
        shared = self.root / "shared/conformance"
        shared.mkdir(parents=True)
        (shared / "README.md").write_text("test-only comparison contract\n")
        self.dirty = ""
        self.patches = [
            patch.object(release, "PACKAGE", self.package),
            patch.object(release, "ROOT", self.root),
            patch.object(release, "git", side_effect=self.git),
            patch.object(release.time, "sleep"),
            patch.dict(os.environ, {
                "GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "push",
                "GITHUB_REPOSITORY": "deancochran/ftms", "GITHUB_REF_TYPE": "tag",
                "GITHUB_REF_NAME": "rust-v0.1.0", "GITHUB_SHA": self.commit,
            }),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.directory = self.package / "target/distribution"
        self.directory.mkdir(parents=True)
        self.archive = self.directory / "ftms-0.1.0.crate"
        self.make_archive()
        self.runs = []
        self.runner = patch.object(release, "run", side_effect=self.run_command)
        self.runner.start()
        self.addCleanup(self.runner.stop)
        self.record = {
            "schemaVersion": 1, "name": "ftms", "version": "0.1.0", "tag": "rust-v0.1.0",
            "commit": self.commit, "dirty": False, "archive": self.archive.name,
            "sha256": release.sha256(self.archive), "archiveConsumer": "passed",
            "rustc": "rustc 1.85.1 (test)", "cargo": "cargo 1.85.1 (test)",
            "sharedInputSha256": release.shared_identity(),
        }
        self.write_record()

    def git(self, *args):
        if args[0] == "status":
            return self.dirty
        if args[0] == "rev-parse":
            return self.commit
        if args[:2] == ("merge-base", "--is-ancestor"):
            return ""
        self.fail(f"unexpected Git operation {args}")

    def run_command(self, command, **kwargs):
        self.runs.append((command, kwargs))
        if command == ["rustc", "--version"]:
            return "rustc 1.85.1 (test)"
        if command == ["cargo", "--version"]:
            return "cargo 1.85.1 (test)"
        return None

    def make_archive(self, extra=None, vcs=None):
        entries = {
            "Cargo.toml": self.manifest, "Cargo.toml.orig": self.manifest,
            "Cargo.lock": "version = 4\n", "LICENSE": "MIT", "README.md": "FTMS",
            "CHANGELOG.md": "## 0.1.0\n", "src/lib.rs": "#![no_std]\n",
            ".cargo_vcs_info.json": json.dumps(vcs or {
                "git": {"sha1": self.commit, "dirty": False}, "path_in_vcs": "packages/rust"}),
        }
        with tarfile.open(self.archive, "w:gz") as archive:
            for name, data in entries.items():
                content = data.encode()
                info = tarfile.TarInfo(f"ftms-0.1.0/{name}")
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
            if extra is not None:
                if isinstance(extra, str):
                    extra = tarfile.TarInfo(extra)
                archive.addfile(extra, io.BytesIO(b""))

    def write_record(self):
        release.write_json(self.directory / "release.json", self.record)

    def registry_value(self, **changes):
        return {"version": {"crate": "ftms", "num": "0.1.0", "yanked": False,
                            "checksum": self.record["sha256"], **changes}}

    def registry_evidence(self):
        release.write_json(self.directory / "registry-evidence.json", {
            "schemaVersion": 1, "registry": release.REGISTRY, "name": "ftms",
            "version": "0.1.0", "commit": self.commit, "sha256": self.record["sha256"],
            "registryConsumer": "passed",
        })

    def github_value(self):
        return {"tag_name": "rust-v0.1.0", "draft": False, "name": "FTMS Rust 0.1.0",
                "body": release.release_notes(release.manifest(), self.commit), "prerelease": False,
                "assets": [{"name": n} for n in [self.archive.name, "release.json", "registry-evidence.json", "SHA256SUMS"]]}

    def downloads(self, command, **kwargs):
        if command[:3] == ["gh", "release", "download"]:
            name = command[command.index("--pattern") + 1]
            target = Path(command[command.index("--dir") + 1]) / name
            shutil.copyfile(self.directory / name, target)
        return self.run_command(command, **kwargs)

    def test_version_and_pinned_toolchain(self):
        for version in ["0.1.0", "1.0.0-rc.1", "2.3.4-beta-2"]:
            release.require_version(version)
        for version in ["01.0.0", "1.0", "1.0.0+build", "1.0.0-01", "1.0.0\n", "../1.0.0"]:
            with self.subTest(version=version), self.assertRaises(release.ReleaseError):
                release.require_version(version)
        self.assertEqual(release.toolchain(), "1.85.1")
        (self.package / "rust-toolchain.toml").write_text('[toolchain]\nchannel = "stable"\n')
        with self.assertRaises(release.ReleaseError):
            release.toolchain()

    def test_tag_identity_clean_tree_and_main_ancestry(self):
        self.assertEqual(release.validate_tag(actions=True)[2], "rust-v0.1.0")
        for key, value in [("GITHUB_REF_TYPE", "branch"), ("GITHUB_REF_NAME", "rust-v0.2.0"),
                           ("GITHUB_ACTIONS", "false"), ("GITHUB_EVENT_NAME", "workflow_dispatch"),
                           ("GITHUB_REPOSITORY", "other/ftms")]:
            with self.subTest(key=key), patch.dict(os.environ, {key: value}), self.assertRaises(release.ReleaseError):
                release.validate_tag(actions=True)
        self.dirty = "?? unrelated-file"
        with self.assertRaises(release.ReleaseError):
            release.validate_tag()
        self.dirty = ""
        def not_main(*args):
            if args[0] == "merge-base":
                raise release.ReleaseError("not on main")
            return self.git(*args)
        with patch.object(release, "git", side_effect=not_main), self.assertRaises(release.ReleaseError):
            release.validate_tag()
        (self.package / "CHANGELOG.md").write_text("## Unreleased\n")
        with self.assertRaises(release.ReleaseError):
            release.validate_tag()

    def test_moved_tag_or_event_commit_is_rejected(self):
        for moved in ["refs/tags/rust-v0.1.0^{commit}", self.commit + "^{commit}"]:
            def mismatched(*args):
                return "b" * 40 if len(args) > 1 and args[1] == moved else self.git(*args)
            with patch.object(release, "git", side_effect=mismatched), self.assertRaises(release.ReleaseError):
                release.validate_tag(actions=True)

    def test_archive_content_and_traversal_guards(self):
        self.assertEqual(release.inspect_archive(self.archive)["commit"], self.commit)
        for entry in ["/outside", "ftms-0.1.0/../outside", "other/src/lib.rs",
                      "ftms-0.1.0/src/lib.rs", "ftms-0.1.0/scripts/release.py", "ftms-0.1.0/.gitignore",
                      "ftms-0.1.0/.toolchain/cargo/credentials.toml", "ftms-0.1.0/src\\escape"]:
            self.make_archive(extra=entry)
            with self.subTest(entry=entry), self.assertRaises(release.ReleaseError):
                release.inspect_archive(self.archive)
        for kind in [tarfile.SYMTYPE, tarfile.LNKTYPE]:
            link = tarfile.TarInfo("ftms-0.1.0/src/link")
            link.type = kind
            link.linkname = "../../outside"
            self.make_archive(extra=link)
            with self.assertRaises(release.ReleaseError):
                release.inspect_archive(self.archive)

    def test_archive_source_path_and_dirty_flag_validation(self):
        for vcs in [{"git": {"sha1": self.commit}, "path_in_vcs": "other/package"},
                    {"git": {"sha1": self.commit, "dirty": 1}, "path_in_vcs": "packages/rust"}]:
            self.make_archive(vcs=vcs)
            with self.assertRaises(release.ReleaseError):
                release.inspect_archive(self.archive)

    def test_prepared_record_binds_version_source_inputs_tools_and_hash(self):
        data = release.manifest()
        self.assertEqual(release.checked_record(self.directory, data, self.commit), self.record)
        original = self.record.copy()
        for key, value in [("version", "0.2.0"), ("commit", "b" * 40), ("dirty", True),
                           ("dirty", 0), ("schemaVersion", True), ("archive", "../wrong"),
                           ("sha256", "0" * 64), ("sharedInputSha256", {}),
                           ("rustc", "rustc 1.99.0 (test)"), ("archiveConsumer", "failed")]:
            self.record = {**original, key: value}
            self.write_record()
            with self.subTest(key=key), self.assertRaises(release.ReleaseError):
                release.checked_record(self.directory, data, self.commit)

    def test_output_cannot_escape_ignored_target(self):
        with self.assertRaises(release.ReleaseError):
            release.output_path(self.package / "src/generated")

    def test_prepare_requires_clean_source_unless_explicit_candidate(self):
        self.dirty = "?? source"
        with patch.object(release, "package") as package, self.assertRaises(release.ReleaseError):
            release.prepare(self.directory)
        package.assert_not_called()

    def test_http_absence_is_only_404_not_auth_rate_limit_or_outage(self):
        for code in [401, 403, 429, 500, 502]:
            error = urllib.error.HTTPError("https://crates.io", code, "test", {}, None)
            with patch.object(release, "open_request", side_effect=error), self.subTest(code=code), self.assertRaises(release.ReleaseError):
                release.json_get("https://crates.io/test", missing=True)
        error = urllib.error.HTTPError("https://crates.io", 404, "test", {}, None)
        with patch.object(release, "open_request", side_effect=error):
            self.assertIsNone(release.json_get("https://crates.io/test", missing=True))
        with patch.object(release, "open_request", side_effect=urllib.error.URLError("offline")), self.assertRaises(release.ReleaseError):
            release.json_get("https://crates.io/test", missing=True)

    def test_http_credentials_are_github_only_and_never_redirected(self):
        for url, token in [("https://crates.io/test", None),
                           ("https://api.github.com/repos/deancochran/ftms/releases", "unit-test-github")]:
            response = io.BytesIO(b"{}")
            response.status = 200
            with patch.object(release, "open_request", return_value=response) as request:
                release.json_get(url, token=token)
            self.assertEqual(request.call_args.args[0].get_header("Authorization"),
                             None if token is None else "Bearer " + token)
        for url in ["https://crates.io/test", "http://api.github.com/repos/deancochran/ftms/test",
                    "https://evil.example/repos/deancochran/ftms/test"]:
            with patch.object(release, "open_request") as request, self.assertRaises(release.ReleaseError):
                release.json_get(url, token="unit-test-github")
            request.assert_not_called()
        self.assertIsNone(release.NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.example"))

    def test_malformed_json_response_fails_closed(self):
        for data in [b"null", b"[]", b"not JSON"]:
            response = io.BytesIO(data)
            response.status = 200
            with patch.object(release, "open_request", return_value=response), self.assertRaises(release.ReleaseError):
                release.json_get("https://crates.io/test", missing=True)

    def test_registry_rejects_conflict_yank_or_wrong_identity(self):
        for change in [{"checksum": "b" * 64}, {"yanked": True}, {"yanked": None},
                       {"crate": "other"}, {"num": "0.2.0"}]:
            with patch.object(release, "json_get", return_value=self.registry_value(**change)), self.subTest(change=change), self.assertRaises(release.ReleaseError):
                release.registry_version(self.record)

    def test_publish_dry_run_never_uploads_or_needs_a_token(self):
        with patch.object(release, "package", return_value=self.archive), patch.object(release, "json_get", return_value=None):
            release.publish(self.directory)
        self.assertFalse(any(command[:2] == ["cargo", "publish"] for command, _ in self.runs))
        self.assertFalse((self.directory / "registry-evidence.json").exists())

    def test_different_rebuilt_bytes_block_before_registry_and_upload(self):
        changed = self.directory / "changed.crate"
        changed.write_bytes(self.archive.read_bytes() + b"changed")
        with patch.object(release, "package", return_value=changed), patch.object(release, "json_get") as network, self.assertRaises(release.ReleaseError):
            release.publish(self.directory, execute=True)
        network.assert_not_called()

    def test_published_matching_version_is_noop_then_installed(self):
        with patch.object(release, "package", return_value=self.archive), patch.object(release, "json_get", return_value=self.registry_value()):
            release.publish(self.directory, execute=True)
        self.assertFalse(any(command[:2] == ["cargo", "publish"] for command, _ in self.runs))
        self.assertTrue(any("--registry-version" in command for command, _ in self.runs))
        self.assertEqual(json.loads((self.directory / "registry-evidence.json").read_text())["registryConsumer"], "passed")

    def test_upload_token_is_supplied_only_to_cargo_upload(self):
        with patch.dict(os.environ, {"CARGO_REGISTRY_TOKEN": "unit-test-credential", "GH_TOKEN": "unit-test-github"}), patch.object(release, "package", return_value=self.archive), patch.object(release, "json_get", side_effect=[None, self.registry_value()]):
            release.publish(self.directory, execute=True)
            self.assertNotIn("CARGO_REGISTRY_TOKEN", release.public_env())
            self.assertNotIn("GH_TOKEN", release.public_env())
        uploads = [(cmd, kw) for cmd, kw in self.runs if cmd[:2] == ["cargo", "publish"]]
        self.assertEqual(len(uploads), 1)
        self.assertIn("--locked", uploads[0][0])
        self.assertIn("--no-verify", uploads[0][0])
        self.assertEqual(uploads[0][1]["env"]["CARGO_REGISTRY_TOKEN"], "unit-test-credential")
        self.assertNotIn("GH_TOKEN", uploads[0][1]["env"])

    def test_missing_token_does_not_claim_publication(self):
        with patch.dict(os.environ, {"CARGO_REGISTRY_TOKEN": ""}), patch.object(release, "package", return_value=self.archive), patch.object(release, "json_get", return_value=None), self.assertRaises(release.ReleaseError):
            release.publish(self.directory, execute=True)
        self.assertFalse((self.directory / "registry-evidence.json").exists())

    def test_failed_upload_is_not_retried_or_recorded_as_success(self):
        def failed(command, **kwargs):
            result = self.run_command(command, **kwargs)
            if command[:2] == ["cargo", "publish"]:
                raise release.ReleaseError("simulated upload failure")
            return result
        with patch.dict(os.environ, {"CARGO_REGISTRY_TOKEN": "unit-test-credential"}), patch.object(release, "package", return_value=self.archive), patch.object(release, "json_get", return_value=None), patch.object(release, "run", side_effect=failed), self.assertRaises(release.ReleaseError):
            release.publish(self.directory, execute=True)
        self.assertEqual(sum(cmd[:2] == ["cargo", "publish"] for cmd, _ in self.runs), 1)
        self.assertFalse((self.directory / "registry-evidence.json").exists())

    def test_delayed_api_and_index_visibility_never_repeat_the_upload(self):
        consumers = 0
        def delayed(command, **kwargs):
            nonlocal consumers
            result = self.run_command(command, **kwargs)
            if "--registry-version" in command:
                consumers += 1
                if consumers < 3:
                    raise release.ReleaseError("index not ready")
            return result
        replies = [None, None, None, self.registry_value(), self.registry_value(), self.registry_value()]
        with patch.dict(os.environ, {"CARGO_REGISTRY_TOKEN": "unit-test-credential"}), patch.object(release, "package", return_value=self.archive), patch.object(release, "json_get", side_effect=replies), patch.object(release, "run", side_effect=delayed):
            release.publish(self.directory, execute=True)
        self.assertEqual(sum(cmd[:2] == ["cargo", "publish"] for cmd, _ in self.runs), 1)
        self.assertEqual(consumers, 3)
        self.assertTrue((self.directory / "registry-evidence.json").exists())

    def test_retry_budget_exhaustion_never_claims_public_installation(self):
        with patch.dict(os.environ, {"CARGO_REGISTRY_TOKEN": "unit-test-credential"}), patch.object(release, "package", return_value=self.archive), patch.object(release, "json_get", return_value=None), self.assertRaises(release.ReleaseError):
            release.publish(self.directory, execute=True)
        self.assertEqual(sum(cmd[:2] == ["cargo", "publish"] for cmd, _ in self.runs), 1)
        self.assertFalse((self.directory / "registry-evidence.json").exists())

    def test_github_creation_requires_public_installation_evidence(self):
        with self.assertRaises(FileNotFoundError):
            release.github_release(self.directory)
        self.registry_evidence()
        with patch.dict(os.environ, {"GH_TOKEN": "unit-test-github"}), patch.object(release, "registry_version", return_value={}), patch.object(release, "json_get", side_effect=[None, self.github_value()]), patch.object(release, "run", side_effect=self.downloads):
            release.github_release(self.directory)
        create = [cmd for cmd, _ in self.runs if cmd[:3] == ["gh", "release", "create"]]
        self.assertEqual(len(create), 1)
        self.assertIn("--verify-tag", create[0])
        self.assertIn("--latest=false", create[0])

    def test_existing_github_release_requires_identical_assets(self):
        self.registry_evidence()
        with patch.dict(os.environ, {"GH_TOKEN": "unit-test-github"}), patch.object(release, "registry_version", return_value={}), patch.object(release, "json_get", return_value=self.github_value()), patch.object(release, "run", side_effect=self.downloads):
            release.github_release(self.directory)
        self.assertFalse(any(cmd[:3] == ["gh", "release", "create"] for cmd, _ in self.runs))

    def test_github_metadata_and_asset_name_conflicts_are_rejected(self):
        value = self.github_value()
        for key, changed in [("name", "wrong"), ("body", "misleading"), ("body", None),
                             ("prerelease", True), ("draft", True), ("assets", []),
                             ("assets", value["assets"] + [{"name": "unexpected.bin"}])]:
            with self.subTest(key=key), self.assertRaises(release.ReleaseError):
                release.matching_github_metadata({**value, key: changed}, "rust-v0.1.0",
                    release.manifest(), value["body"], [a["name"] for a in value["assets"]])

    def test_github_conflicting_asset_bytes_are_never_overwritten(self):
        self.registry_evidence()
        def changed(command, **kwargs):
            result = self.downloads(command, **kwargs)
            if command[:3] == ["gh", "release", "download"]:
                name = command[command.index("--pattern") + 1]
                (Path(command[command.index("--dir") + 1]) / name).write_bytes(b"wrong")
            return result
        with patch.dict(os.environ, {"GH_TOKEN": "unit-test-github"}), patch.object(release, "registry_version", return_value={}), patch.object(release, "json_get", return_value=self.github_value()), patch.object(release, "run", side_effect=changed), self.assertRaises(release.ReleaseError):
            release.github_release(self.directory)
        self.assertFalse(any(cmd[:3] == ["gh", "release", "create"] for cmd, _ in self.runs))


if __name__ == "__main__":
    unittest.main()
