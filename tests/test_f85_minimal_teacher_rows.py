"""Equivalence and resumability contracts for the minimal F85 teacher path."""

import json
from pathlib import Path

from scripts import f50_generic_learnable_evaluator as f50
from scripts import f59_action_spectrum_diagnosis as f59
from scripts import f79_parent_anchored_full_residual_arena4 as f79
from scripts import f85_c2_train_teacher_acquisition as f85


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
