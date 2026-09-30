"""Offline workflow safety tests. All registry/GitHub calls are mocked."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import ci_release as ci
import publish as release

WORKFLOW = release.ROOT / ".github/workflows/release-kotlin.yml"


class CIReleaseTest(unittest.TestCase):
    def setUp(self):
        preferred = "/tmp/opencode" if os.access("/tmp/opencode", os.W_OK | os.X_OK) else None
        self.temp = tempfile.TemporaryDirectory(prefix="ftms-ci-", dir=preferred)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.package = self.path / "repo/packages/kotlin"
        self.package.mkdir(parents=True)
        self.verified = self.package / ".releases/verified"
        self.verified.mkdir(parents=True)
        self.output = self.package / ".releases/current"
        self.config = self.path / "secrets"
        self.config.mkdir(mode=0o700)
        self.env = {"GITHUB_ACTIONS": "true", "GITHUB_REPOSITORY": ci.REPOSITORY,
                    "GITHUB_EVENT_NAME": "push", "GITHUB_REF_TYPE": "branch", "GITHUB_REF_NAME": "main",
                    "RUNNER_TEMP": str(self.path / "runner")}
        for target, name, value in ((release, "PACKAGE", self.package), (release, "ROOT", self.path / "repo"),
                                    (release, "RELEASE", self.output), (ci, "VERIFIED", self.verified)):
            context = patch.object(target, name, value)
            context.start()
            self.addCleanup(context.stop)
        self.environment = patch.dict(os.environ, self.env)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        (self.package / "VERSION").write_text("0.2.0\n")
        (self.package / "CHANGELOG.md").write_text("# Changelog\n\n## 0.2.0\n")
        self.metadata = {"sourceCommit": "commit", "version": "0.2.0"}
        self.manifest = {**self.metadata, "tag": "kotlin-v0.2.0", "bundleSha256": "hash",
                         "coordinates": "io.github.deancochran:ftms:0.2.0"}

    def test_version_and_changelog_are_exact(self):
        self.assertEqual("0.2.0", ci.version())
        for bad in ("0.02.0", "v0.2.0", "0.2.0-SNAPSHOT", "0.2.0\n0.3.0"):
            (self.package / "VERSION").write_text(bad)
            with self.subTest(version=bad), self.assertRaises(release.ReleaseError):
                ci.version()
        (self.package / "VERSION").write_text("0.3.0")
        with self.assertRaises(release.ReleaseError):
            ci.version()

    def test_secretful_jobs_require_main_or_matching_tag(self):
        with patch.object(release, "clean_commit", return_value="commit"), patch.object(release, "run") as run:
            self.assertEqual(("commit", "0.2.0"), ci.source_identity())
            run.assert_called_with(["git", "merge-base", "--is-ancestor", "commit", "origin/main"])
            for kind, name in (("branch", "feature"), ("tag", "kotlin-v0.1.0"), ("tag", "v0.2.0")):
                with patch.dict(os.environ, {"GITHUB_REF_TYPE": kind, "GITHUB_REF_NAME": name}), \
                        self.assertRaises(release.ReleaseError):
                    ci.source_identity()
            with patch.dict(os.environ, {"GITHUB_REPOSITORY": "someone/fork"}), self.assertRaises(release.ReleaseError):
                ci.source_identity()

    def test_pr_gate_is_non_secretful(self):
        with patch.dict(os.environ, {"GITHUB_EVENT_NAME": "pull_request", "GITHUB_REF_NAME": "9/merge"}), \
                patch.object(release, "clean_commit", return_value="commit"), patch.object(release, "run") as run:
            self.assertEqual(("commit", "0.2.0"), ci.source_identity())
        run.assert_not_called()

    def write_gate(self):
        (self.verified / "binary.jar").write_bytes(b"exact-tested-bytes")
        data = {**self.metadata, "files": {"binary.jar": release.sha256(b"exact-tested-bytes")}}
        release.write_json(self.verified / "gate.json", data)
        return release.sha256((self.verified / "gate.json").read_bytes())

    def test_gate_binds_commit_version_metadata_and_every_file(self):
        expected = self.write_gate()
        with patch.object(ci, "source_identity", return_value=("commit", "0.2.0")):
            self.assertEqual("commit", ci.load_gate(expected)["sourceCommit"])
            with self.assertRaises(release.ReleaseError):
                ci.load_gate("wrong-digest")
            (self.verified / "binary.jar").write_bytes(b"modified")
            with self.assertRaises(release.ReleaseError):
                ci.load_gate(expected)
            expected = self.write_gate()
            (self.verified / "unexpected").write_text("extra")
            with self.assertRaises(release.ReleaseError):
                ci.load_gate(expected)
        with patch.object(ci, "source_identity", return_value=("other-commit", "0.2.0")), self.assertRaises(release.ReleaseError):
            ci.load_gate(expected)

    def test_config_cannot_be_inside_checkout_or_outside_actions(self):
        self.assertEqual(self.path / "runner/ftms-kotlin-publishing", ci.config_path())
        with patch.dict(os.environ, {"RUNNER_TEMP": str(release.ROOT)}), self.assertRaises(release.ReleaseError):
            ci.config_path()
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}), self.assertRaises(release.ReleaseError):
            ci.config_path()

    def test_verify_mode_never_creates_or_publishes(self):
        with patch.object(ci, "github_release", return_value=None), patch.object(ci, "gh") as gh, \
                patch.object(release, "assemble") as assemble, patch.object(release, "upload") as upload, \
                patch.object(ci, "ensure_tag") as tag:
            self.assertIn("no tag/upload/publication", ci.deliver(self.config, self.metadata, "verify"))
        gh.assert_not_called()
        assemble.assert_not_called()
        upload.assert_not_called()
        tag.assert_not_called()

    def test_existing_public_release_is_verified_never_overwritten(self):
        existing = {"draft": False, "tag_name": "kotlin-v0.2.0"}
        for mode in ("verify", "publish"):
            with self.subTest(mode=mode), patch.object(ci, "github_release", return_value=existing), \
                    patch.object(ci, "verify_existing") as verify, patch.object(release, "upload") as upload, \
                    patch.object(ci, "gh") as gh:
                self.assertIn("Already published", ci.deliver(self.config, self.metadata, mode))
                verify.assert_called_once_with(self.config, existing)
                upload.assert_not_called()
                gh.assert_not_called()

    def test_untracked_central_version_cannot_be_reuploaded(self):
        with patch.object(release, "request", return_value=b"pom"), self.assertRaises(release.ReleaseError):
            ci.require_unpublished("0.2.0")
        with patch.object(release, "request", side_effect=release.HttpFailure(404)):
            ci.require_unpublished("0.2.0")
        with patch.object(release, "request", side_effect=release.HttpFailure(401)), self.assertRaises(release.HttpFailure):
            ci.require_unpublished("0.2.0")

    def test_wrong_saved_version_is_rejected(self):
        ci.require_release_identity(self.manifest, "kotlin-v0.2.0")
        with self.assertRaises(release.ReleaseError):
            ci.require_release_identity(self.manifest, "kotlin-v0.3.0")

    def test_draft_resume_uses_saved_bundle_not_a_rebuild(self):
        calls = []
        with patch.object(ci, "github_release", return_value={"draft": True}), patch.object(ci, "restore"), \
                patch.object(release, "load_release", return_value=self.manifest), \
                patch.object(ci, "validate_evidence"), \
                patch.object(release, "assemble") as assemble, patch.object(ci, "save_receipts", side_effect=lambda _: calls.append("receipt")), \
                patch.object(release, "upload", side_effect=lambda *_: calls.append("upload")), \
                patch.object(release, "publish", side_effect=lambda *_: calls.append("publish")), \
                patch.object(release, "verify_public", side_effect=lambda *_, **kw: calls.append("verify")), \
                patch.object(ci, "gh", side_effect=lambda *_: calls.append("announce")):
            ci.deliver(self.config, self.metadata, "publish")
        assemble.assert_not_called()
        self.assertEqual(["upload", "receipt", "publish", "verify", "receipt", "announce"], calls)

    def test_verification_failure_keeps_release_draft_and_saves_receipts(self):
        with patch.object(ci, "github_release", return_value={"draft": True}), patch.object(ci, "restore"), \
                patch.object(release, "load_release", return_value=self.manifest), patch.object(release, "upload"), \
                patch.object(ci, "validate_evidence"), \
                patch.object(release, "publish"), patch.object(release, "verify_public", side_effect=release.ReleaseError("mismatch")), \
                patch.object(ci, "save_receipts") as save, patch.object(ci, "gh") as gh, \
                self.assertRaises(release.ReleaseError):
            ci.deliver(self.config, self.metadata, "publish")
        self.assertEqual(2, save.call_count)
        gh.assert_not_called()

    def test_only_receipts_may_be_updated_in_draft(self):
        self.output.mkdir()
        for name in (*ci.CORE_ASSETS, *ci.RECEIPTS):
            (self.output / name).write_text("data")
        with patch.object(ci, "gh") as gh:
            ci.save_receipts("kotlin-v0.2.0")
        args = gh.call_args.args
        self.assertIn("--clobber", args)
        for name in ci.CORE_ASSETS:
            self.assertNotIn(str(self.output / name), args)

    def test_incomplete_saved_release_is_not_replaced(self):
        with self.assertRaises(release.ReleaseError):
            ci.restore({"assets": [{"name": "manifest.json"}]})
        with self.assertRaises(release.ReleaseError):
            ci.restore({"assets": [{"name": name} for name in ci.CORE_ASSETS]})

    def test_draft_aware_discovery_paginates_and_refuses_duplicates(self):
        draft = {"tag_name": "kotlin-v0.2.0", "draft": True, "assets": []}
        other = [{"tag_name": f"v0.0.{i}", "draft": False} for i in range(100)]
        results = [subprocess.CompletedProcess([], 0, json.dumps(page).encode(), b"") for page in (other, [draft])]
        with patch.object(ci, "gh", side_effect=results) as gh:
            self.assertEqual(draft, ci.github_release("kotlin-v0.2.0"))
            self.assertTrue(gh.call_args.args[1].endswith("page=2"))
        result = subprocess.CompletedProcess([], 0, json.dumps([draft, draft]).encode(), b"")
        with patch.object(ci, "gh", return_value=result), self.assertRaises(release.ReleaseError):
            ci.github_release("kotlin-v0.2.0")
        with patch.object(ci, "gh", side_effect=subprocess.CalledProcessError(1, "gh")), \
                self.assertRaises(subprocess.CalledProcessError):
            ci.github_release("kotlin-v0.2.0")

    def test_verify_mode_checks_central_published_draft_without_mutation(self):
        self.output.mkdir()
        (self.output / "deployment.json").write_text("{}")
        draft = {"tag_name": "kotlin-v0.2.0", "draft": True}
        for state in ("PUBLISHED", "VALIDATED"):
            with self.subTest(state=state), patch.object(ci, "github_release", return_value=draft), \
                    patch.object(ci, "restore") as restore, patch.object(ci, "validate_evidence"), \
                    patch.object(release, "load_release", return_value=self.manifest), \
                    patch.object(release, "deployment", return_value="id"), patch.object(release, "status", return_value=state), \
                    patch.object(release, "verify_public") as verify, patch.object(release, "upload") as upload, \
                    patch.object(ci, "gh") as gh:
                result = ci.deliver(self.config, self.metadata, "verify")
                restore.assert_called_once_with(draft)
                self.assertEqual(1 if state == "PUBLISHED" else 0, verify.call_count)
                self.assertNotIn("Unpublished version", result)
                upload.assert_not_called()
                gh.assert_not_called()

    def test_restored_signed_evidence_must_prove_the_same_clean_commit(self):
        self.output.mkdir()
        for source, failures, valid in (("commit", 0, True), ("wrong", 0, False), ("commit", 1, False)):
            with zipfile.ZipFile(self.output / "conformance-evidence.zip", "w") as archive:
                result = {"sourceCommit": source, "dirty": False, "complete": True, "passed": 1, "failed": 0}
                for name in ("original-v1.json", "compatibility-v1.json"):
                    archive.writestr("reports/conformance/" + name, json.dumps(result))
                archive.writestr("test-results/test/TEST-fixture.xml", f'<testsuite tests="1" failures="{failures}" errors="0" skipped="0"/>')
            with self.subTest(source=source, failures=failures), patch.object(release, "verify_signature") as signature:
                if valid:
                    ci.validate_evidence(self.config, self.manifest)
                else:
                    with self.assertRaises(release.ReleaseError):
                        ci.validate_evidence(self.config, self.manifest)
                signature.assert_called_once()

    def test_retry_download_uses_successful_gate_artifact_identity(self):
        workflow = WORKFLOW.read_text()
        self.assertIn("artifact_name: ${{ steps.gate.outputs.artifact_name }}", workflow)
        self.assertIn("name: ${{ needs.gate.outputs.artifact_name }}", workflow)
        self.assertNotIn("name: kotlin-verified-${{ github.run_id }}-${{ github.run_attempt }}", workflow)
        self.assertIn("group: kotlin-publish-${{ needs.gate.outputs.version }}", workflow)

    def test_existing_remote_tag_is_never_signed_or_force_pushed(self):
        with patch.object(release, "git", return_value="existing-tag-object"), patch.object(release, "run") as run:
            ci.ensure_tag(self.config, "kotlin-v0.2.0", "commit")
        self.assertEqual(1, run.call_count)
        self.assertEqual(["git", "fetch", "origin", "refs/tags/kotlin-v0.2.0:refs/tags/kotlin-v0.2.0"], run.call_args.args[0])

    def test_real_noninteractive_signed_tag_in_isolated_git_repository(self):
        # This test uses a new disposable test key and a local bare remote only.
        home = self.config / "gnupg"
        home.mkdir(mode=0o700)
        passfile = self.config / "signing-passphrase"
        passfile.write_text("test-fixture-only\n")
        passfile.chmod(0o600)
        command = ["gpg", "--homedir", str(home), "--batch", "--pinentry-mode", "loopback",
                   "--passphrase-file", str(passfile)]
        subprocess.run(command + ["--quick-generate-key", "FTMS CI disposable test", "ed25519", "sign", "1d"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.addCleanup(lambda: subprocess.run(["gpgconf", "--homedir", str(home), "--kill", "all"],
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        keys = subprocess.check_output(command + ["--with-colons", "--list-secret-keys"], stderr=subprocess.DEVNULL, text=True)
        key = next(line.split(":")[9] for line in keys.splitlines() if line.startswith("fpr:"))
        (self.config / "signing-fingerprint").write_text(key)
        (self.config / "signing-fingerprint").chmod(0o600)
        import shlex
        wrapper = self.config / "git-gpg"
        wrapper.write_text("#!/bin/sh\nexec " + shlex.join(command) + ' "$@"\n')
        wrapper.chmod(0o700)
        bare = self.path / "remote.git"
        def git(*args):
            return subprocess.check_output(["git", *args], cwd=release.ROOT, stderr=subprocess.DEVNULL, text=True).strip()
        git("init", "--initial-branch=main")
        git("config", "user.name", "FTMS test")
        git("config", "user.email", "test@example.invalid")
        git("add", "packages/kotlin/VERSION", "packages/kotlin/CHANGELOG.md")
        git("commit", "-m", "fixture")
        git("init", "--bare", str(bare))
        git("remote", "add", "origin", str(bare))
        commit = git("rev-parse", "HEAD")
        ci.ensure_tag(self.config, "kotlin-v0.2.0", commit)
        self.assertEqual("tag", git("cat-file", "-t", "refs/tags/kotlin-v0.2.0"))
        self.assertEqual(commit, git("rev-parse", "kotlin-v0.2.0^{commit}"))
        result = subprocess.run(["git", "-c", "gpg.program=gpg", "verify-tag", "--raw", "kotlin-v0.2.0"],
                                cwd=release.ROOT, env={**os.environ, "GNUPGHOME": str(home)},
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        self.assertIn("[GNUPG:] VALIDSIG " + key, result.stderr)


if __name__ == "__main__":
    unittest.main()
