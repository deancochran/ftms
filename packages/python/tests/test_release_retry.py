import importlib.util
import json
import unittest
import urllib.error
from collections.abc import Mapping
from email.message import Message
from pathlib import Path
from typing import Any


def load_retry() -> Any:
    path = Path(__file__).parents[1] / "scripts/release_retry.py"
    spec = importlib.util.spec_from_file_location("release_retry_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


retry = load_retry()


class Tests(unittest.TestCase):
    def test_absent_partial_identical_and_mismatch(self) -> None:
        expected = {"a": "1", "b": "2"}

        def absent(_: str) -> bytes:
            raise urllib.error.HTTPError("url", 404, "missing", Message(), None)

        def metadata(digests: Mapping[str, str | None]) -> bytes:
            return json.dumps(
                {
                    "urls": [
                        {"filename": name, "digests": {"sha256": digest}}
                        for name, digest in digests.items()
                    ]
                }
            ).encode()

        self.assertEqual(retry.plan("1", expected, absent), ["a", "b"])
        self.assertEqual(retry.plan("1", expected, lambda _: metadata({"a": "1"})), ["b"])
        self.assertEqual(retry.plan("1", expected, lambda _: metadata(expected)), [])
        with self.assertRaises(ValueError):
            retry.plan("1", expected, lambda _: metadata({"a": "x"}))
        with self.assertRaises(ValueError):
            retry.plan("1", expected, lambda _: metadata({"a": None}))

    def test_registry_errors_are_not_absence(self) -> None:
        error = urllib.error.HTTPError("url", 403, "forbidden", Message(), None)
        self.addCleanup(error.close)

        def forbidden(_: str) -> bytes:
            raise error

        with self.assertRaises(urllib.error.HTTPError):
            retry.plan("1", {"a": "1"}, forbidden)

        def unavailable(_: str) -> bytes:
            raise urllib.error.URLError("offline")

        with self.assertRaises(urllib.error.URLError):
            retry.plan("1", {"a": "1"}, unavailable)
