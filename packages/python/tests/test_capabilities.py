from __future__ import annotations

import importlib.util
import json
import shutil
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

from deancochran_ftms import (
    C7Evidence,
    CapabilitySnapshot,
    CharacteristicEvidence,
    DecodeState,
    DiscoveryState,
    Prerequisite,
    Presence,
    RangeFormatOptions,
    ReadReason,
    ReadState,
    ServiceScope,
    TruthValue,
    evaluate_capabilities,
)


def runner() -> ModuleType:
    path = Path(__file__).parents[1] / "scripts/run_capability_conformance.py"
    spec = importlib.util.spec_from_file_location("capability_runner", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_capability_corpus_is_complete() -> None:
    module = runner()
    report = module.run()
    assert report["runnerErrors"] == [] and report["complete"]
    assert report["caseCounts"] == {
        "total": 63,
        "byCategory": {
            "discovery": 12,
            "duplicates": 3,
            "features": 5,
            "forward-compatibility": 2,
            "measurements": 7,
            "operations": 4,
            "properties": 22,
            "ranges": 8,
        },
    }
    assert report["assertionCounts"] == {
        "total": 63,
        "passed": 63,
        "failed": 0,
        "unsupported": 0,
        "skipped": 0,
    }


def test_evidence_is_immutable_and_invalid_input_is_rejected() -> None:
    evidence = CharacteristicEvidence(
        "00002acc00001000800000805f9b34fb", 2, ReadState.SUCCESS, read_bytes=b"\0" * 8
    )
    snapshot = CapabilitySnapshot(DiscoveryState.COMPLETE, ServiceScope.PRESENT, 0, (evidence,))
    report = evaluate_capabilities(snapshot)
    with pytest.raises((AttributeError, TypeError)):
        report.presence[1] = 1  # type: ignore[index]
    with pytest.raises(TypeError):
        CharacteristicEvidence(
            "00002acc00001000800000805f9b34fb",
            2,
            ReadState.SUCCESS,
            read_bytes=cast(bytes, bytearray(8)),
        )
    with pytest.raises(TypeError):
        evaluate_capabilities(object())  # type: ignore[arg-type]
    assert "canExecute" not in report.to_wire()


def resistance_snapshot(payload: bytes) -> CapabilitySnapshot:
    def observation(
        uuid: str, properties: int, payload: bytes | None = None
    ) -> CharacteristicEvidence:
        return CharacteristicEvidence(
            f"0000{uuid}00001000800000805f9b34fb",
            properties,
            ReadState.NOT_ATTEMPTED if payload is None else ReadState.SUCCESS,
            read_bytes=payload or b"",
        )

    return CapabilitySnapshot(
        DiscoveryState.COMPLETE,
        ServiceScope.PRESENT,
        0,
        (
            observation("2acc", 2, bytes.fromhex("0000000004000000")),
            observation("2ad6", 2, payload),
            observation("2ad9", 0x28),
            observation("2ada", 0x10),
            observation("2ad4", 2, bytes.fromhex("000064000100")),
        ),
        C7Evidence(TruthValue.FALSE, TruthValue.UNKNOWN),
    )


def test_resistance_format_is_explicit_and_does_not_affect_other_ranges() -> None:
    snapshot = resistance_snapshot(bytes.fromhex("f6ff64000a00"))
    default = evaluate_capabilities(snapshot)
    assert default.ranges[2][1] == DecodeState.MALFORMED
    assert default.operations[4][4] == Prerequisite.INCONSISTENT
    selected = evaluate_capabilities(snapshot, RangeFormatOptions("signed16Tenths"))
    assert selected.ranges[2] == (Presence.UNIQUE, DecodeState.VALID, 1, (2, -10, 100, 10, 10, 2))
    assert selected.operations[4][4] == Prerequisite.SATISFIED
    assert selected.ranges[0] == default.ranges[0]
    whole = resistance_snapshot(bytes.fromhex("006401"))
    assert evaluate_capabilities(whole).ranges[2][1] == DecodeState.VALID
    assert (
        evaluate_capabilities(whole, RangeFormatOptions("signed16Tenths")).ranges[2][1]
        == DecodeState.MALFORMED
    )
    invalid_options: tuple[object, ...] = (True, {}, "signed16Tenths")
    for invalid in invalid_options:
        with pytest.raises(TypeError):
            evaluate_capabilities(snapshot, cast(Any, invalid))
    with pytest.raises(ValueError):
        evaluate_capabilities(snapshot, RangeFormatOptions(cast(Any, "invalid")))


def test_report_construction_rejects_mutable_aliases_and_wire_view_is_independent() -> None:
    report = evaluate_capabilities(resistance_snapshot(bytes.fromhex("006401")))
    with pytest.raises(TypeError):
        replace(report, presence=cast(Any, [Presence.UNKNOWN]))
    with pytest.raises(TypeError):
        replace(report, ranges=((2, 1, 1, [2, 0, 100, 1, 1, 2]),))
    wire = cast(dict[str, Any], report.to_wire())
    wire["ranges"][2][3][1] = 99
    wire["operations"][4][4] = 99
    assert report.ranges[2][3] == (2, 0, 100, 1, 1, 2)
    assert report.operations[4][4] == Prerequisite.SATISFIED
    assert wire != report.to_wire()


@pytest.mark.parametrize(
    "field,value",
    [
        ("uuid", "00002ACC00001000800000805f9b34fb"),
        ("uuid", "2acc"),
        ("uuid", "０" * 32),
        ("properties", True),
        ("properties", -1),
        ("properties", 65536),
        ("read_state", 1),
        ("read_reason", True),
        ("read_reason", ReadReason.TIMEOUT),
        ("read_bytes", bytearray(8)),
    ],
)
def test_invalid_characteristic_arguments(field: str, value: object) -> None:
    args: dict[str, Any] = dict(
        uuid="00002acc00001000800000805f9b34fb", properties=2, read_state=ReadState.SUCCESS
    )
    args[field] = value
    with pytest.raises((TypeError, ValueError)):
        CharacteristicEvidence(**args)


@pytest.mark.parametrize(
    "field,value",
    [
        ("generation", True),
        ("generation", -1),
        ("generation", 2**32),
        ("discovery", 2),
        ("scope", True),
        ("characteristics", []),
        ("c7", True),
    ],
)
def test_invalid_snapshot_arguments(field: str, value: object) -> None:
    snapshot = resistance_snapshot(bytes.fromhex("006401"))
    with pytest.raises((TypeError, ValueError)):
        replace(snapshot, **{field: cast(Any, value)})


@pytest.mark.parametrize("side", ["input", "expected"])
def test_runner_rejects_invalid_expanded_types_and_accounts_all_cases(
    tmp_path: Path, side: str
) -> None:
    module = runner()
    source = Path(__file__).resolve().parents[3] / "shared/conformance/capabilities"
    destination = tmp_path / "capabilities"
    shutil.copytree(source, destination)
    vectors_path = destination / "v1/vectors.json"
    vectors = json.loads(vectors_path.read_text())
    case = vectors["cases"][0]
    case["input"]["edits"].append({"path": ["generation"], "value": 1})
    case["expected"]["edits"].append({"path": ["generation"], "value": 1})
    case[side]["edits"].append({"path": ["generation"], "value": True})
    vectors_path.write_text(json.dumps(vectors))
    report = module.run(destination / "v1")
    assert not report["complete"]
    assert report["runnerErrors"]
    assert report["caseCounts"]["total"] == 63
    assert report["assertionCounts"] == dict(
        total=63, passed=62, failed=1, unsupported=0, skipped=0
    )


def test_runner_comparison_is_json_type_exact() -> None:
    module = runner()
    assert not module._exact({"x": [1]}, {"x": [True]})
    assert not module._exact([1], [1.0])
    assert not module._exact([1, 2], [2, 1])
    assert not module._exact({"x": 1}, {"x": 1, "y": 2})
    assert module._exact({"x": [None, 1]}, {"x": [None, 1]})


def test_runner_root_replacement_is_deep_copied_and_subsequent_edits_apply() -> None:
    module = runner()
    replacement = {"items": [1, 2]}
    templates = {"base": {"old": 0}}
    actual = module._expand(
        {
            "template": "base",
            "edits": [
                {"path": [], "value": replacement},
                {"path": ["items"], "op": "append", "value": 3},
                {"path": ["items", 0], "op": "remove"},
            ],
        },
        templates,
    )
    assert actual == {"items": [2, 3]}
    assert replacement == {"items": [1, 2]}
    assert templates == {"base": {"old": 0}}
    with pytest.raises(ValueError, match="cannot remove root"):
        module._edit(actual, {"path": [], "op": "remove"})
