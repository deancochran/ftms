"""Offline release safety regressions. No credentials, remote calls or real keys."""

import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import zipfile

import publish as release


class PublishingTest(unittest.TestCase):
    def setUp(self):
        preferred = "/tmp/opencode" if os.access("/tmp/opencode", os.W_OK | os.X_OK) else None
        self.temp = tempfile.TemporaryDirectory(prefix="ftms-publisher-", dir=preferred)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.config = self.path / "config"
        self.config.mkdir(mode=0o700)
        self.output = self.path / "release"
        self.output.mkdir()
        self.release_patch = patch.object(release, "RELEASE", self.output)
        self.release_patch.start()
        self.addCleanup(self.release_patch.stop)

    def secret(self, name, value):
        path = self.config / name
        path.write_text(value)
        path.chmod(0o600)
        return path

    def bundle(self, names=None):
        names = names or ["io/github/deancochran/ftms/0.1.0/ftms-0.1.0.jar"]
        bundle = self.output / "central-bundle.zip"
        with zipfile.ZipFile(bundle, "w") as archive:
            for name in names:
                archive.writestr(name, b"artifact")
        return {"version": "0.1.0", "bundleSha256": release.sha256(bundle.read_bytes()),
                "files": {name: release.sha256(b"artifact") for name in names}}, bundle

    def test_owner_only_credentials(self):
        path = self.secret("central-token", "not-a-real-token")
        self.assertEqual(path, release.private_file(self.config, "central-token"))
        path.chmod(0o644)
        with self.assertRaises(release.ReleaseError):
            release.private_file(self.config, "central-token")

    def test_symlinks_and_repository_secrets_rejected(self):
        path = self.secret("real", "not-a-secret")
        (self.config / "central-token").symlink_to(path)
        with self.assertRaises(release.ReleaseError):
            release.private_file(self.config, "central-token")
        with patch.object(release, "ROOT", self.path), self.assertRaises(release.ReleaseError):
            release.private_file(self.config, "real")

    def test_token_only_in_fixed_origin_authorization_header(self):
        self.secret("central-token", "dXNlcjpwYXNz")
        with patch.object(release, "request", return_value=b"ok") as request:
            self.assertEqual(b"ok", release.central(self.config, "/status?id=example"))
            self.assertEqual(release.CENTRAL + "/status?id=example", request.call_args.args[0])
            self.assertEqual("Bearer dXNlcjpwYXNz", request.call_args.kwargs["headers"]["Authorization"])

    def test_redirect_and_error_body_not_disclosed(self):
        with self.assertRaises(release.ReleaseError):
            release.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.invalid")
        error = urllib.error.HTTPError("https://central.sonatype.com", 401, "secret-value", {}, io.BytesIO(b"secret-value"))
        with patch.object(release.HTTP, "open", side_effect=error), self.assertRaises(release.ReleaseError) as caught:
            release.request(release.CENTRAL)
        self.assertNotIn("secret-value", str(caught.exception))

    def test_bundle_exact_hashes_and_tampering(self):
        manifest, bundle = self.bundle()
        release.validate_bundle(manifest, bundle)
        manifest["files"][next(iter(manifest["files"]))] = "0" * 64
        with self.assertRaises(release.ReleaseError):
            release.validate_bundle(manifest, bundle)
        manifest, bundle = self.bundle()
        bundle.write_bytes(bundle.read_bytes() + b"tampered")
        with self.assertRaises(release.ReleaseError):
            release.validate_bundle(manifest, bundle)

    def test_bundle_path_traversal_rejected(self):
        manifest, bundle = self.bundle(["io/github/deancochran/ftms/0.1.0/../../secret"])
        with self.assertRaises(release.ReleaseError):
            release.validate_bundle(manifest, bundle)

    def test_dirty_checkout_rejected(self):
        with patch.object(release, "git", return_value=" M source.kt"), self.assertRaises(release.ReleaseError):
            release.clean_commit()

    def test_existing_evidence_never_cleaned(self):
        with patch.object(release, "logged") as logged, self.assertRaises(release.ReleaseError):
            release.prepare(self.config)
        logged.assert_not_called()

    def test_wrong_deployment_bundle_rejected(self):
        release.write_json(self.output / "deployment.json", {"bundleSha256": "wrong"})
        with self.assertRaises(release.ReleaseError):
            release.deployment({"bundleSha256": "right", "sourceCommit": "source", "tagObject": "tag"})

    def test_wrong_deployment_commit_or_tag_rejected(self):
        manifest = {"bundleSha256": "right", "sourceCommit": "source", "tagObject": "tag"}
        for field in ("sourceCommit", "tagObject"):
            release.write_json(self.output / "deployment.json", {**manifest, field: "wrong"})
            with self.subTest(field=field), self.assertRaises(release.ReleaseError):
                release.deployment(manifest)

    def test_publish_only_validated_or_already_publishing(self):
        for state in ("PENDING", "VALIDATING", "FAILED", "UNKNOWN"):
            with self.subTest(state=state), patch.object(release, "deployment", return_value="id"), \
                    patch.object(release, "status", return_value=state), patch.object(release, "central") as central:
                with self.assertRaises(release.ReleaseError):
                    release.publish(self.config, {}, 1)
                central.assert_not_called()
        for state, writes in (("VALIDATED", 1), ("PUBLISHING", 0), ("PUBLISHED", 0)):
            with self.subTest(state=state), patch.object(release, "deployment", return_value="id"), \
                    patch.object(release, "status", return_value=state), patch.object(release, "central") as central, \
                    patch.object(release, "wait_for"), patch.object(release, "verify_staged") as staged:
                release.publish(self.config, {}, 1)
                self.assertEqual(writes, central.call_count)
                self.assertEqual(writes, staged.call_count)

    def test_staged_bytes_must_match_signed_manifest(self):
        manifest, _ = self.bundle()
        manifest["sourceCommit"] = "commit"
        with patch.object(release, "central", return_value=b"artifact"):
            release.verify_staged(self.config, manifest, "id")
        with patch.object(release, "central", return_value=b"different"), self.assertRaises(release.ReleaseError):
            release.verify_staged(self.config, manifest, "id")

    def test_staged_mismatch_never_publishes(self):
        with patch.object(release, "deployment", return_value="id"), \
                patch.object(release, "status", return_value="VALIDATED"), \
                patch.object(release, "verify_staged", side_effect=release.ReleaseError("mismatch")), \
                patch.object(release, "central") as central, self.assertRaises(release.ReleaseError):
            release.publish(self.config, {}, 1)
        central.assert_not_called()

    def test_resume_upload_never_uploads_twice(self):
        release.write_json(self.output / "deployment.json", {})
        with patch.object(release, "deployment", return_value="id"), patch.object(release, "wait_for") as wait, \
                patch.object(release, "central") as central:
            release.upload(self.config, {}, 1)
        central.assert_not_called()
        wait.assert_called_once()

    def test_central_discovery_paginates_exact_bundle_names(self):
        manifest = {"tag": "kotlin-v0.2.0", "deploymentName": "kotlin-v0.2.0-hash"}
        matched = {"deploymentName": manifest["deploymentName"], "deploymentId": "00000000-0000-0000-0000-000000000001", "deploymentState": "VALIDATED"}
        pages = [{"pageCount": 2, "deployments": [{**matched, "deploymentName": "prefix-" + manifest["deploymentName"]}]},
                 {"pageCount": 2, "deployments": [matched]}]
        with patch.object(release, "central", side_effect=[json.dumps(p).encode() for p in pages]) as central:
            self.assertEqual(matched["deploymentId"], release.find_deployment(self.config, manifest))
            self.assertIn("page=1", central.call_args.args[1])
        for matches in ([matched, matched], [{**matched, "deploymentState": "FAILED"}]):
            with patch.object(release, "central", return_value=json.dumps({"pageCount": 1, "deployments": matches}).encode()), \
                    self.assertRaises(release.ReleaseError):
                release.find_deployment(self.config, manifest)

    def test_accepted_upload_can_be_recovered_without_another_post(self):
        manifest = {"tag": "kotlin-v0.2.0", "deploymentName": "kotlin-v0.2.0-hash", "bundleSha256": "hash", "sourceCommit": "commit", "tagObject": "tag"}
        item = {"deploymentName": manifest["deploymentName"], "deploymentId": "00000000-0000-0000-0000-000000000001", "deploymentState": "VALIDATED"}
        with patch.object(release, "central", return_value=json.dumps({"pageCount": 1, "deployments": [item]}).encode()) as central, \
                patch.object(release, "wait_for"):
            release.upload(self.config, manifest, 1)
        self.assertEqual(1, central.call_count)
        self.assertEqual("GET", central.call_args.kwargs["method"])
        self.assertEqual(item["deploymentId"], release.deployment(manifest))

    def test_public_propagation_retry_and_deadline(self):
        manifest, _ = self.bundle()
        manifest.update({"sourceCommit": "commit", "coordinates": "io.github.deancochran:ftms:0.1.0"})
        with patch.object(release, "deployment", return_value="id"), patch.object(release, "status", return_value="PUBLISHED"), \
                patch.object(release, "request", side_effect=[release.HttpFailure(404), b"artifact"]) as request, \
                patch.object(release, "logged"), patch.object(release.time, "sleep"), patch.object(release.time, "monotonic", return_value=0):
            release.verify_public(self.config, manifest, timeout=10)
            self.assertEqual(2, request.call_count)
        with patch.object(release, "deployment", return_value="id"), patch.object(release, "status", return_value="PUBLISHED"), \
                patch.object(release, "request", side_effect=release.HttpFailure(404)), \
                patch.object(release.time, "monotonic", side_effect=[0, 11]), self.assertRaises(release.HttpFailure):
            release.verify_public(self.config, manifest, timeout=10)

    def test_status_identity_and_failure(self):
        with patch.object(release, "central", return_value=json.dumps({"deploymentId": "wrong"}).encode()), \
                self.assertRaises(release.ReleaseError):
            release.status(self.config, "expected", {"version": "0.1.0"})
        with patch.object(release, "status", return_value="FAILED"), self.assertRaises(release.ReleaseError):
            release.wait_for(self.config, "id", {}, {"PUBLISHED"}, 1)

    def test_wrong_or_extra_central_coordinates_rejected(self):
        expected = "pkg:maven/io.github.deancochran/ftms@0.1.0"
        for state in ("VALIDATED", "PUBLISHING", "PUBLISHED"):
            for purls in (["pkg:maven/other/project@0.1.0"], [expected, expected]):
                response = {"deploymentId": "id", "deploymentState": state, "purls": purls}
                with self.subTest(state=state, purls=purls), \
                        patch.object(release, "central", return_value=json.dumps(response).encode()), \
                        self.assertRaises(release.ReleaseError):
                    release.status(self.config, "id", {"version": "0.1.0"})
        response = {"deploymentId": "id", "deploymentState": "VALIDATED", "purls": [expected]}
        with patch.object(release, "central", return_value=json.dumps(response).encode()):
            self.assertEqual("VALIDATED", release.status(self.config, "id", {"version": "0.1.0"}))

    def test_empty_coordinates_only_allowed_after_publish_transition(self):
        for state in ("VALIDATED", "PUBLISHING", "PUBLISHED"):
            for purls in (None, []):
                response = {"deploymentId": "id", "deploymentState": state, "purls": purls}
                with self.subTest(state=state, purls=purls), \
                        patch.object(release, "central", return_value=json.dumps(response).encode()):
                    if state == "VALIDATED":
                        with self.assertRaises(release.ReleaseError):
                            release.status(self.config, "id", {"version": "0.1.0"})
                    else:
                        self.assertEqual(state, release.status(self.config, "id", {"version": "0.1.0"}))

    def test_signed_tag_object_must_match_remote(self):
        key = "A" * 40
        manifest = {"sourceCommit": "commit", "signingFingerprint": key, "tag": "kotlin-v0.1.0"}
        release.write_json(self.output / "manifest.json", manifest)
        for kind, signing_key, remote_object, checkout, strict, valid in (
            ("tag", key, "tag-object", "commit", True, True),
            ("commit", key, "tag-object", "commit", True, False),
            ("tag", "B" * 40, "tag-object", "commit", True, False),
            ("tag", key, "changed-tag-object", "commit", True, False),
            ("tag", key, "tag-object", "new-tooling-commit", True, False),
            ("tag", key, "tag-object", "new-tooling-commit", False, True)
        ):
            def git(*args):
                if args[0] == "cat-file":
                    return kind
                if args[0] == "ls-remote":
                    return f"{remote_object}\trefs/tags/kotlin-v0.1.0\ncommit\trefs/tags/kotlin-v0.1.0^{{}}"
                return "commit" if args[1].endswith("^{commit}") else "tag-object"

            verification = subprocess.CompletedProcess([], 0, "", "[GNUPG:] VALIDSIG " + signing_key + " details")
            with self.subTest(kind=kind, signing_key=signing_key, remote_object=remote_object), \
                    patch.object(release, "verify_signature"), patch.object(release, "validate_bundle"), \
                    patch.object(release, "fingerprint", return_value=key), \
                    patch.object(release, "clean_commit", return_value=checkout), \
                    patch.object(release, "git", side_effect=git), patch.object(release, "run", return_value=verification):
                if valid:
                    self.assertEqual("tag-object", release.load_release(self.config, require_prepared_checkout=strict)["tagObject"])
                else:
                    with self.assertRaises(release.ReleaseError):
                        release.load_release(self.config, require_prepared_checkout=strict)


if __name__ == "__main__":
    unittest.main()
