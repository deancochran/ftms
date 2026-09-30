from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


def _module() -> ModuleType:
    path = Path(__file__).parents[1] / "scripts" / "verify_public.py"
    spec = importlib.util.spec_from_file_location("verify_public", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VERIFY_PUBLIC = _module()


def _metadata(wheel_sha256: str = "a" * 64, sdist_sha256: str = "b" * 64) -> dict[str, Any]:
    version = "0.1.0a1"
    return {
        "info": {"name": "deancochran-ftms", "version": version},
        "urls": [
            {
                "filename": f"deancochran_ftms-{version}-py3-none-any.whl",
                "url": "https://files.pythonhosted.org/packages/example.whl",
                "yanked": False,
                "digests": {"sha256": wheel_sha256},
            },
            {
                "filename": f"deancochran_ftms-{version}.tar.gz",
                "url": "https://files.pythonhosted.org/packages/example.tar.gz",
                "yanked": False,
                "digests": {"sha256": sdist_sha256},
            },
        ],
    }


def test_selects_exact_public_artifact_pair() -> None:
    selected = VERIFY_PUBLIC._select_artifacts(_metadata(), "0.1.0a1")
    assert set(selected) == {"wheel", "sdist"}
    assert selected["wheel"]["digests"]["sha256"] == "a" * 64


@pytest.mark.parametrize("mutation", ["extra", "yanked", "host", "identity"])
def test_rejects_ambiguous_or_untrusted_registry_metadata(mutation: str) -> None:
    metadata = _metadata()
    if mutation == "extra":
        metadata["urls"].append(dict(metadata["urls"][0]))
    elif mutation == "yanked":
        metadata["urls"][0]["yanked"] = True
    elif mutation == "host":
        metadata["urls"][0]["url"] = "https://example.invalid/package.whl"
    else:
        metadata["info"]["version"] = "9.9.9"
    with pytest.raises(ValueError):
        VERIFY_PUBLIC._select_artifacts(metadata, "0.1.0a1")


def test_verifies_downloaded_bytes_and_both_consumers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    wheel = b"public wheel bytes"
    sdist = b"public sdist bytes"
    wheel_digest = hashlib.sha256(wheel).hexdigest()
    sdist_digest = hashlib.sha256(sdist).hexdigest()
    metadata = _metadata(wheel_digest, sdist_digest)
    fetched = {
        "metadata": json.dumps(metadata).encode(),
        metadata["urls"][0]["url"]: wheel,
        metadata["urls"][1]["url"]: sdist,
    }
    consumed: list[tuple[str, bytes]] = []
    fetches: list[tuple[str, dict[str, int]]] = []

    def fetch(url: str, **options: int) -> bytes:
        fetches.append((url, options))
        return fetched[url]

    monkeypatch.setattr(VERIFY_PUBLIC, "_fetch", fetch)

    def consume(artifact: Path, _root: Path, report: dict[str, Any], kind: str) -> None:
        consumed.append((kind, artifact.read_bytes()))
        report.setdefault("consumers", {})[kind] = {
            "outcome": "passed",
            "interpreter": "test-python",
        }

    monkeypatch.setattr(VERIFY_PUBLIC, "_run_consumer", consume)
    output = tmp_path / "report.json"

    assert VERIFY_PUBLIC.verify_public_release(
        "0.1.0a1", wheel_digest, sdist_digest, output, "metadata"
    )
    assert consumed == [("wheel", wheel), ("sdist", sdist)]
    assert fetches == [
        ("metadata", {}),
        (metadata["urls"][0]["url"], {"attempts": 3}),
        (metadata["urls"][1]["url"], {"attempts": 3}),
    ]
    report = json.loads(output.read_text())
    assert report["complete"] is True
    assert report["errors"] == []
    assert set(report["consumers"]) == {"wheel", "sdist"}


@pytest.mark.parametrize("failure", ["registry-digest", "download-digest", "consumer"])
def test_verification_failures_are_reported(
    failure: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    wheel = b"public wheel bytes"
    sdist = b"public sdist bytes"
    wheel_digest = hashlib.sha256(wheel).hexdigest()
    sdist_digest = hashlib.sha256(sdist).hexdigest()
    metadata = _metadata(wheel_digest, sdist_digest)
    expected_wheel_digest = wheel_digest
    downloaded_wheel = wheel
    if failure == "registry-digest":
        expected_wheel_digest = "f" * 64
    elif failure == "download-digest":
        downloaded_wheel = b"tampered wheel bytes"

    fetched = {
        "metadata": json.dumps(metadata).encode(),
        metadata["urls"][0]["url"]: downloaded_wheel,
        metadata["urls"][1]["url"]: sdist,
    }
    monkeypatch.setattr(VERIFY_PUBLIC, "_fetch", lambda url, **_options: fetched[url])

    def consume(_artifact: Path, _root: Path, report: dict[str, Any], kind: str) -> None:
        if failure == "consumer":
            raise RuntimeError("consumer failed")
        report.setdefault("consumers", {})[kind] = {"outcome": "passed"}

    monkeypatch.setattr(VERIFY_PUBLIC, "_run_consumer", consume)
    output = tmp_path / "report.json"

    assert not VERIFY_PUBLIC.verify_public_release(
        "0.1.0a1", expected_wheel_digest, sdist_digest, output, "metadata"
    )
    report = json.loads(output.read_text())
    assert report["complete"] is False
    assert len(report["errors"]) == 1
    if failure == "registry-digest":
        assert "registry SHA-256" in report["errors"][0]["reason"]
    elif failure == "download-digest":
        assert "downloaded wheel SHA-256" in report["errors"][0]["reason"]
    else:
        assert "consumer failed" in report["errors"][0]["reason"]


def test_report_write_failure_returns_false(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    wheel = b"wheel"
    sdist = b"sdist"
    wheel_digest = hashlib.sha256(wheel).hexdigest()
    sdist_digest = hashlib.sha256(sdist).hexdigest()
    metadata = _metadata(wheel_digest, sdist_digest)
    fetched = {
        "metadata": json.dumps(metadata).encode(),
        metadata["urls"][0]["url"]: wheel,
        metadata["urls"][1]["url"]: sdist,
    }
    monkeypatch.setattr(VERIFY_PUBLIC, "_fetch", lambda url, **_options: fetched[url])

    def consume(_artifact: Path, _root: Path, report: dict[str, Any], kind: str) -> None:
        report.setdefault("consumers", {})[kind] = {"outcome": "passed"}

    monkeypatch.setattr(VERIFY_PUBLIC, "_run_consumer", consume)
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("blocker")

    assert not VERIFY_PUBLIC.verify_public_release(
        "0.1.0a1", wheel_digest, sdist_digest, blocker / "report.json", "metadata"
    )
    diagnostic = json.loads(capsys.readouterr().err)
    assert diagnostic["publicPackageVerification"] is False
    assert "reportWriteError" in diagnostic


def test_fetch_retries_transient_registry_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0
    sleeps: list[int] = []

    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
            return None

        def read(self) -> bytes:
            return b"registry response"

    def open_response(_request: object, timeout: int) -> Response:
        nonlocal attempts
        assert timeout == 30
        attempts += 1
        if attempts == 1:
            raise VERIFY_PUBLIC.urllib.error.URLError("not propagated yet")
        return Response()

    monkeypatch.setattr(VERIFY_PUBLIC.urllib.request, "urlopen", open_response)
    monkeypatch.setattr(VERIFY_PUBLIC.time, "sleep", sleeps.append)

    assert VERIFY_PUBLIC._fetch("https://pypi.org/example", attempts=2, delay_seconds=7) == (
        b"registry response"
    )
    assert attempts == 2
    assert sleeps == [7]


def test_fetch_reports_exhausted_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_request: object, timeout: int) -> None:
        assert timeout == 30
        raise VERIFY_PUBLIC.urllib.error.URLError("offline")

    monkeypatch.setattr(VERIFY_PUBLIC.urllib.request, "urlopen", fail)
    monkeypatch.setattr(VERIFY_PUBLIC.time, "sleep", lambda _delay: None)

    with pytest.raises(RuntimeError, match="failed to fetch"):
        VERIFY_PUBLIC._fetch("https://pypi.org/example", attempts=2, delay_seconds=0)


@pytest.mark.parametrize(("complete", "exit_code"), [(True, 0), (False, 1)])
def test_cli_exit_code_reflects_verification(
    complete: bool, exit_code: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        VERIFY_PUBLIC.sys,
        "argv",
        [
            "verify_public.py",
            "--version",
            "0.1.0a1",
            "--wheel-sha256",
            "a" * 64,
            "--sdist-sha256",
            "b" * 64,
        ],
    )
    monkeypatch.setattr(VERIFY_PUBLIC, "verify_public_release", lambda *_args: complete)

    assert VERIFY_PUBLIC.main() == exit_code
