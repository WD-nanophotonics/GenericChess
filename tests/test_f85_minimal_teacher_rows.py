"""Equivalence and resumability contracts for the minimal F85 teacher path."""

import json
from pathlib import Path
import hashlib

from scripts import f50_generic_learnable_evaluator as f50
from scripts import f59_action_spectrum_diagnosis as f59
from scripts import f79_parent_anchored_full_residual_arena4 as f79
from scripts import f85_c2_train_teacher_acquisition as f85
from scripts import f82_c2_parent_anchored_repeatability as c2


ROOT = Path(__file__).resolve().parents[1]


def _record():
    payload = json.loads((ROOT / "artifacts/f83_c1_relative_evidence/root_corpus.json").read_text(encoding="utf-8"))
    return next(root for root in payload["roots"] if root["role"] == "train")


def test_minimal_smoke_is_exactly_equivalent_to_f59_selected_rows():
    compiled, native, _profile = f50._ruleset(f85.LABEL)
    _parent, champion, _descriptor = f79._load_frozen_candidate(compiled)
    record = _record()
    full_rows, full_meta = f59._spectrum_for_root(compiled, native, champion, champion, record, smoke=True)
    minimal = f85._minimal_teacher_unit(compiled, native, champion, record, smoke=True)
    assert [row["action_key"] for row in minimal["teacher_rows"]] == [row.action_key for row in full_rows]
    assert [row["q_1k"] for row in minimal["teacher_rows"]] == [row.q_1k for row in full_rows]
    assert [row["q_20k"] for row in minimal["teacher_rows"]] == [row.q_20k for row in full_rows]
    for minimal_row, full_row in zip(minimal["teacher_rows"], full_rows):
        assert minimal_row["features"] == full_row.features.tolist()
        assert minimal_row["base_q"] == full_row.base_q
    assert minimal["root_metadata"]["root_2k"]["action_key"] == full_meta["root_2k"]["action_key"]
    assert minimal["root_metadata"]["root_80k"]["action_key"] == full_meta["root_80k"]["action_key"]


def test_minimal_manifest_uses_reduced_node_formula():
    payload = json.loads((ROOT / "artifacts/f85_c2_train_teacher_evidence/minimal_train_manifest.json").read_text(encoding="utf-8"))
    assert payload["schema"] == "generic-chess-f85-minimal-teacher-rows-manifest-v1"
    assert payload["teacher_contract"]["diagnostic_calls_omitted"] == ["root_40k", "observer_2k", "selected_q10k"]
    assert payload["total_declared_node_ceiling"] == sum(root["declared_node_ceiling"] for root in payload["roots"])
    for root in payload["roots"]:
        expected = 2_000 + 80_000 + 1_000 * root["legal_action_count"] + 20_000 * root["maximum_selected_actions"]
        assert root["declared_node_ceiling"] == expected


def test_phase_resume_reuses_complete_root2k(tmp_path, monkeypatch):
    compiled, native, _profile = f50._ruleset(f85.LABEL)
    _parent, champion, _descriptor = f79._load_frozen_candidate(compiled)
    record = _record()
    runtime = tmp_path / "progress"
    first = f85._run_minimal_root(record, plan_sha="a" * 64, manifest_sha="b" * 64, runtime_dir=runtime, compiled=compiled, native=native, parent=champion, stop_after="root2k")
    assert first["status"] == "PAUSED"
    original = f59._root_search
    monkeypatch.setattr(f59, "_root_search", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("root2k was recomputed")))
    second = f85._run_minimal_root(record, plan_sha="a" * 64, manifest_sha="b" * 64, runtime_dir=runtime, compiled=compiled, native=native, parent=champion, stop_after="root2k")
    assert second["status"] == "PAUSED"
    monkeypatch.setattr(f59, "_root_search", original)


def test_phase_provenance_is_runtime_independent_and_sealed_roots_reuse(tmp_path, monkeypatch):
    record = _record()
    enriched = {**record, "action_history": [{"synthetic": "history"}], "replay_actions": [{"synthetic": "replay"}]}
    assert f85._phase_provenance(record, plan_sha="a" * 64, manifest_sha="b" * 64) == f85._phase_provenance(enriched, plan_sha="a" * 64, manifest_sha="b" * 64)

    runtime = tmp_path / "progress"
    provenance = f85._phase_provenance(enriched, plan_sha="a" * 64, manifest_sha="b" * 64)
    root_dir = runtime / record["root_id"]
    root_dir.mkdir(parents=True)
    sealed = {"root_id": record["root_id"], "position_key": record["position_key"], "role": record["role"], "stratum": record["stratum"], "selected_action_count": 0, "actual_teacher_calls": 0, "actual_search_calls": 2, "teacher_rows": [], "root_metadata": {}}
    for phase, value in {
        "root2k": {"action": None},
        "root80k": {"action": None},
        "all_legal_q1k": {"actions": [], "q1k": []},
        "selected_q20": {"rows": []},
        "assembled": sealed,
    }.items():
        (root_dir / f"{phase}.json").write_text(json.dumps({"status": "COMPLETE", "provenance": provenance, "value": value}), encoding="utf-8")

    compiled, native, _profile = f50._ruleset(f85.LABEL)
    _parent, champion, _descriptor = f79._load_frozen_candidate(compiled)
    monkeypatch.setattr(f59, "_root_search", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("sealed root was recomputed")))
    resumed = f85._run_minimal_root(record, plan_sha="a" * 64, manifest_sha="b" * 64, runtime_dir=runtime, compiled=compiled, native=native, parent=champion)
    assert resumed["status"] == "COMPLETE"
    assert resumed["teacher_rows"] == []


def test_bounded_worker_cap_returns_time_cap_without_claiming_complete(tmp_path):
    record = _record()
    result = f85._run_minimal_root_bounded(record, plan_sha="c" * 64, manifest_sha="d" * 64, runtime_dir=tmp_path / "progress", wall_seconds=0)
    assert result["status"] == "TIME_CAP"
    assert result["termination_reason"] == "per_root_wall_cap"


def test_canonical_training_evidence_shape_is_consumable(monkeypatch, tmp_path):
    evidence_path = tmp_path / "training_evidence.json"
    evidence_path.write_text(json.dumps({
        "c1_checkpoint_id": c2.PARENT_CHECKPOINT_ID,
        "c1_model_sha256": c2.PARENT_MODEL_SHA,
        "roots": [{"root_id": "synthetic", "teacher_rows": [
            {"features": [0.0, 1.0], "base_q": 0.0, "q_20k": 1.0, "action_key": "a"},
            {"features": [1.0, 0.0], "base_q": 0.0, "q_20k": 0.0, "action_key": "b"},
        ]}],
    }), encoding="utf-8")
    monkeypatch.setattr(c2, "TEACHER_EVIDENCE", evidence_path)
    rows = c2._training_data()
    assert len(rows) == 1
    assert rows[0]["target"] == 0
