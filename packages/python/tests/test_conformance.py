from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def test_partial_canonical_conformance_report() -> None:
    script = Path(__file__).parents[1] / "scripts" / "run_features_conformance.py"
    spec = importlib.util.spec_from_file_location("runner", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.run()
    assert report["runnerErrors"] == []
    assert report["runnerComplete"]
    assert report["conformanceComplete"]
    assert report["v1"]["caseCounts"]["total"] == 97
    assert report["v1"]["caseCounts"]["byCategory"]["features"] == 35
    assert report["v1"]["assertionCounts"] == {
        "total": 97,
        "passed": 97,
        "failed": 0,
        "unsupported": 0,
        "skipped": 0,
    }
    assert report["valuesV1"]["caseCounts"] == {
        "total": 8,
        "byCategory": {"features": 3, "ranges": 5},
    }
    assert report["valuesV1"]["assertionCounts"] == {
        "total": 16,
        "passed": 16,
        "failed": 0,
        "unsupported": 0,
        "skipped": 0,
    }
    assert report["controlsV1"]["caseCounts"] == {
        "total": 41,
        "byCategory": {"requests": 27, "responses": 6, "invalid": 8},
    }
    assert report["controlsV1"]["assertionCounts"] == {
        "total": 72,
        "passed": 72,
        "failed": 0,
        "unsupported": 0,
        "skipped": 0,
    }
    assert report["inspectionV1"]["caseCounts"] == {"total": 9}
    assert report["inspectionV1"]["assertionCounts"] == {
        "total": 9,
        "passed": 9,
        "failed": 0,
        "unsupported": 0,
        "skipped": 0,
    }
    assert report["compatibilityV1"]["caseCounts"] == {
        "total": 9,
        "byCategory": {"ranges": 3, "measurements": 6},
    }
    assert report["compatibilityV1"]["assertionCounts"] == {
        "total": 18,
        "passed": 18,
        "failed": 0,
        "unsupported": 0,
        "skipped": 0,
    }


def test_duplicate_ids_are_rejected_within_a_synthetic_corpus() -> None:
    script = Path(__file__).parents[1] / "scripts" / "run_features_conformance.py"
    spec = importlib.util.spec_from_file_location("runner_duplicates", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(ValueError, match="duplicate fixture IDs: repeated"):
        module._ensure_unique_ids(
            {"features": [{"id": "repeated"}], "ranges": [{"id": "repeated"}]}
        )


def test_runner_error_is_recorded_for_unreadable_synthetic_corpus(tmp_path: Path) -> None:
    script = Path(__file__).parents[1] / "scripts" / "run_features_conformance.py"
    spec = importlib.util.spec_from_file_location("runner_errors", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.run(tmp_path, tmp_path)
    assert not report["runnerComplete"]
    assert report["runnerErrors"]
    assert "FileNotFoundError" in report["runnerErrors"][0]["reason"]


def test_missing_duplicate_and_unexpected_outcomes_are_incomplete() -> None:
    script = Path(__file__).parents[1] / "scripts" / "run_features_conformance.py"
    spec = importlib.util.spec_from_file_location("runner_accounting", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    expected = {("a", "encode"), ("a", "decode")}
    outcomes = [{"id": "a", "direction": direction} for direction in ("encode", "decode")]
    assert module._complete(outcomes, expected)
    assert not module._complete(outcomes[:1], expected)
    assert not module._complete(outcomes + outcomes[:1], expected)
    assert not module._complete(outcomes + [{"id": "b", "direction": "encode"}], expected)
    assert not module._complete([], set())
