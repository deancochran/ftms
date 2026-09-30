"""Credential-free registry decision tests; no publication or network access."""
import json
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

import release
from release import public_version_exists


class ReleaseRetryTests(unittest.TestCase):
    def test_existing_version_runs_public_verifier_and_never_uploads(self):
        with (patch("sys.argv", ["release.py", "publish", "--execute", "--tag", "dart-v0.1.0"]),
              patch.dict("os.environ", {"GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/tags/dart-v0.1.0",
                                        "GITHUB_REPOSITORY": "deancochran/ftms"}),
              patch.object(release, "validate_tag"),
              patch.object(release, "validated_evidence", return_value={"archiveSha256": "digest"}),
              patch.object(release, "sha256", return_value="digest"),
              patch.object(release, "public_version_exists", return_value=True),
              patch.object(release, "run") as run):
            release.main()
            run.assert_called_once_with(release.sys.executable, "tool/verify_public.py")
            run.reset_mock()
            run.side_effect = ValueError("public contents differ")
            with self.assertRaises(ValueError):
                release.main()
            run.assert_called_once_with(release.sys.executable, "tool/verify_public.py")

    def test_existing_version_requires_verification_not_another_upload(self):
        self.assertTrue(public_version_exists("0.1.0", lambda *_: json.dumps({"version": "0.1.0"}).encode()))

    def test_wrong_identity_fails(self):
        with self.assertRaises(ValueError):
            public_version_exists("0.1.0", lambda *_: b'{"version":"0.2.0"}')

    def test_only_404_permits_upload(self):
        for code in (404, 401, 403, 500):
            def fail(*_, code=code):
                raise HTTPError("https://pub.dev/", code, "test", {}, None)
            if code == 404:
                self.assertFalse(public_version_exists("0.1.0", fail))
            else:
                with self.assertRaises(HTTPError):
                    public_version_exists("0.1.0", fail)

    def test_network_errors_fail_closed(self):
        def fail(*_):
            raise TimeoutError("offline")
        with self.assertRaises(TimeoutError):
            public_version_exists("0.1.0", fail)
