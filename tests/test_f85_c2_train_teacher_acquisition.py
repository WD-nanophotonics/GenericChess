"""Contract tests for the F85A harness and large-plan preparation."""

import json
from pathlib import Path

from scripts import f50_generic_learnable_evaluator as f50
from scripts import f85_c2_train_teacher_acquisition as f85
from scripts import f83_c1_relative_evidence_roots_and_cost_calibration as f83


ROOT = Path(__file__).resolve().parents[1]
ROOT_CORPUS = ROOT / "artifacts/f83_c1_relative_evidence/root_corpus.json"
MANIFEST = ROOT / "artifacts/f85_c2_train_teacher_evidence/train_precompute_manifest.json"


def test_f85_harness_is_precompute_only_until_approved_plan():
    source = (ROOT / "scripts/f85_c2_train_teacher_acquisition.py").read_text(encoding="utf-8")
    assert f85.WORK_ORDER == "GENERICCHESS-F85A-C2-TRAIN-TEACHER-ACQUISITION-HARNESS-AND-LARGE-PLAN"
    assert "--precompute-only" in source
    assert "acquisition is withheld" in source.lower()
    assert "Arena" not in source
    assert "selfplay" not in source.lower()
    assert ".generic_chess_flow" not in source


def test_f85_manifest_binds_exact_train_roots_and_teacher_contract():
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    root_payload = json.loads(ROOT_CORPUS.read_text(encoding="utf-8"))
    assert payload["schema"] == "generic-chess-f85-train-root-precompute-manifest-v1"
    assert payload["status"] == "PRECOMPUTE_COMPLETE_ACQUISITION_NOT_AUTHORIZED"
    assert payload["f83_authority"]["root_set_identity_sha256"] == f85.F83_ROOT_SET_ID
    assert payload["f84_calibration_artifact"]["content_sha256"] == f85.F84_CALIBRATION_SHA
    assert payload["execution_contract"]["train_root_count"] == 36
    assert payload["execution_contract"]["dev_root_count"] == 0
    assert payload["execution_contract"]["resource_root_count"] == 0
    assert payload["execution_contract"]["max_concurrent_roots"] == 2
    assert payload["execution_contract"]["per_root_wall_cap_seconds"] == 720
    assert payload["execution_contract"]["no_auto_retry"] is True
    assert payload["teacher_contract"]["root_budgets"] == [2000, 40000, 80000]
    assert payload["teacher_contract"]["observer_root_budget"] == 2000
    assert payload["teacher_contract"]["teacher_child_budgets"] == {"all_legal": 1000, "selected_high": 20000, "selected_mid": 10000}
    assert len(payload["roots"]) == 36
    assert all(root["role"] == "train" for root in payload["roots"])
    assert {stratum: sum(root["stratum"] == stratum for root in payload["roots"]) for stratum in ("reachable_random", "c1_on_policy", "c1_pv_corridor")} == {"reachable_random": 12, "c1_on_policy": 12, "c1_pv_corridor": 12}
    by_id = {root["root_id"]: root for root in root_payload["roots"]}
    assert [root["root_id"] for root in payload["roots"]] == [root["root_id"] for root in root_payload["roots"] if root["role"] == "train"]
    for root in payload["roots"]:
        assert root["position_key"] == by_id[root["root_id"]]["position_key"]
        assert root["maximum_selected_actions"] == 9
        assert root["maximum_teacher_calls"] == 18
        assert root["declared_node_ceiling"] == f85._root_ceiling(root["legal_action_count"])
        assert root["declared_node_ceiling"] > 0
    assert payload["total_declared_node_ceiling"] == sum(root["declared_node_ceiling"] for root in payload["roots"])
    assert ".generic_chess_flow" not in MANIFEST.read_text(encoding="utf-8")


def test_f85_precompute_replays_all_36_train_roots_and_recomputes_legal_counts():
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    root_payload = json.loads(ROOT_CORPUS.read_text(encoding="utf-8"))
    compiled, _native, _profile = f50._ruleset(f85.LABEL)
    from generic_chess.core.identity import position_identity_key

    source_by_id = {root["root_id"]: root for root in root_payload["roots"]}
    replayed = []
    for record in payload["roots"]:
        source = source_by_id[record["root_id"]]
        session = f83._session(compiled, source["replay_actions"])
        assert session.result.status.value == "ongoing"
        assert position_identity_key(session.state.position, compiled) == record["position_key"]
        assert len(session.legal_actions()) == record["legal_action_count"]
        replayed.append(record["position_key"])
    assert len(replayed) == 36
    assert len(set(replayed)) == 36
