"""Crash-resume assembly checks for the corrected F61 strength runner."""

import json
from types import SimpleNamespace

from scripts import f61_r2_fresh_strength as runner


def test_f61_worker_budget_uses_available_cpu_across_candidate_lanes(monkeypatch):
    monkeypatch.setattr(runner.os, "cpu_count", lambda: 20)
    assert runner._workers(8, concurrent_lanes=3) == 6
    assert runner._workers(32) == 20


def test_f61_runner_uses_the_receipt_bound_corrective_identity():
    assert runner.CORRECTED_TRAINING_CONFIG == "f61-corrected-perspective"
    data = json.loads(
        (runner.ROOT / "docs" / "architecture" / "GENERICCHESS_F61_MODEL_PARAMS.json")
        .read_text(encoding="utf-8")
    )
    parent = runner.f59._parent(runner.f59.LABELS[1])
    actual = {}
    for candidate in data["corrected_candidates"]:
        checkpoint = runner._candidate_checkpoint(parent, candidate)
        actual[candidate["candidate_id"]] = checkpoint.checkpoint_id
    assert actual == runner.EXPECTED_CORRECTED_IDS


def test_f61_reuses_only_complete_identity_matching_validation(tmp_path):
    candidate = {"candidate_id": "candidate-a", "checkpoint_id": "old-a"}
    child = SimpleNamespace(checkpoint_id="corrected-a")
    openings = SimpleNamespace(openings=tuple(
        SimpleNamespace(final_position_key=f"opening-{index}") for index in range(2)
    ))
    validation_rows = [
        {
            "opening_id": f"opening-{index}",
            "parent_nodes": runner.NODES_PER_MOVE,
            "child_nodes": runner.NODES_PER_MOVE,
            "decision_changed": bool(index),
        }
        for index in range(2)
    ]
    row = {
        "candidate_id": "candidate-a",
        "old_checkpoint_id": "old-a",
        "corrected_checkpoint_id": "corrected-a",
        "search_validation": {
            "opening_count": 2,
            "decision_changes": 1,
            "rows": validation_rows,
        },
    }
    partial = tmp_path / "partial.json"
    partial.write_text(json.dumps({"candidates": [row]}), encoding="utf-8")

    reused = runner._load_reusable_validations(
        partial, [candidate], {"candidate-a": child}, {"candidate-a": openings}
    )
    assert reused == {"candidate-a": row["search_validation"]}

    unit = tmp_path / "candidate-a" / "validation.json"
    runner._write_validation_unit(
        unit, candidate, child, openings, row["search_validation"]
    )
    assert runner._load_validation_unit(
        unit, candidate, child, openings
    ) == row["search_validation"]

    row["search_validation"]["rows"] = validation_rows[:1]
    partial.write_text(json.dumps({"candidates": [row]}), encoding="utf-8")
    assert runner._load_reusable_validations(
        partial, [candidate], {"candidate-a": child}, {"candidate-a": openings}
    ) == {}
