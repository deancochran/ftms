import importlib.util
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest


def load_runner() -> Any:
    path = Path(__file__).parents[1] / "scripts/run_measurement_status_conformance.py"
    spec = importlib.util.spec_from_file_location("status_report_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_status_corruption_fails_report_and_encoding_is_independent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = load_runner()
    decode = runner.decode_machine_status_raw
    encode = runner.encode_machine_status_raw
    inputs = []

    def corrupt(data: bytes) -> Any:
        return replace(decode(data), trailing_bytes=1)

    def track(raw: Any) -> bytes:
        inputs.append(raw)
        # Corrupt decoded evidence must never become the encoder oracle.
        assert raw.trailing_bytes == 0
        result = encode(raw)
        assert isinstance(result, bytes)
        return result

    monkeypatch.setattr(runner, "P", tmp_path)
    monkeypatch.setattr(runner, "decode_machine_status_raw", corrupt)
    monkeypatch.setattr(runner, "encode_machine_status_raw", track)
    assert runner.main() == 1
    report = json.loads(
        (tmp_path / "build/measurement-status-verification-report.json").read_text()
    )
    assert not report["complete"] and not report["runnerErrors"]
    assert inputs
    assert any(
        x["direction"] == "decode" and x["outcome"] == "failed"
        for x in report["corpora"]["statuses"]["outcomes"]
    )


def test_expected_error_cannot_pass_successful_measurement_decode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = load_runner()
    decode = runner.decode_measurement_raw
    fallback = decode(bytes.fromhex("00000100"), 5)

    def corrupt(data: bytes, kind: int) -> Any:
        try:
            return decode(data, kind)
        except runner.RawCodecError:
            return fallback

    monkeypatch.setattr(runner, "P", tmp_path)
    monkeypatch.setattr(runner, "decode_measurement_raw", corrupt)
    assert runner.main() == 1
    report = json.loads(
        (tmp_path / "build/measurement-status-verification-report.json").read_text()
    )
    assert not report["runnerErrors"]
    assert any(x["outcome"] == "failed" for x in report["corpora"]["measurements"]["outcomes"])
