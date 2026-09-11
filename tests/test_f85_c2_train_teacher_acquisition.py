"""Contract tests for the F85A harness and large-plan preparation."""

import json
from pathlib import Path
import shutil
import tempfile

import pytest

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
    assert "RETRY_REQUIRES_NEW_AUTHORIZATION" in source
    assert "STALE_PROGRESS_PROVENANCE" in source
    assert "max_concurrent_roots=lanes" in source
    assert "Arena" not in source
    assert "selfplay" not in source.lower()


def test_f85_manifest_binds_exact_train_roots_and_teacher_contract():
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    root_payload = json.loads(ROOT_CORPUS.read_text(encoding="utf-8"))
    assert payload["schema"] == "generic-chess-f85-train-root-precompute-manifest-v1"
    assert payload["status"] == "PRECOMPUTE_COMPLETE_ACQUISITION_NOT_AUTHORIZED"
    assert payload["sandbox_sha"] == f85.F85_PRECOMPUTE_SOURCE_SHA
    assert payload["f83_authority"]["root_set_identity_sha256"] == f85.F83_ROOT_SET_ID
    assert payload["f84_calibration_artifact"]["content_sha256"] == f85.F84_CALIBRATION_SHA
    assert payload["execution_contract"]["train_root_count"] == 36
    assert payload["execution_contract"]["dev_root_count"] == 0
    assert payload["execution_contract"]["resource_root_count"] == 0
    assert payload["execution_contract"]["max_concurrent_roots"] == 2
    assert f85.FROZEN_MANIFEST_MAX_CONCURRENT_ROOTS == 2
    assert f85.MAX_CONCURRENT_ROOTS == 3
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


def _fake_complete(record):
    return {
        "status": "COMPLETE",
        "position_key": record["position_key"],
        "selected_action_count": 0,
        "actual_teacher_calls": 0,
        "actual_search_calls": 4,
        "teacher_rows": [],
        "root_metadata": {},
    }


def _runtime_tmp():
    return Path(tempfile.mkdtemp(prefix="generic-chess-f85-"))


def _plan_file(runtime, *, lanes=3):
    runtime.mkdir(parents=True, exist_ok=True)
    plan = runtime / "plan.json"
    plan.write_text(json.dumps({
        "sandbox_sha": f85._git_sha(),
        "precompute_manifest_sha256": f85._sha(f85.F85_MANIFEST_PATH),
        "resource_envelope": {"intended_cpu_lanes": lanes},
    }), encoding="utf-8")
    return plan


def test_f85_fake_complete_seals_only_after_all_36_units(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    evidence = tmp_path / "training_evidence.json"
    calls = []
    runtime = _runtime_tmp()
    plan = _plan_file(runtime)

    def runner(record):
        calls.append(record["root_id"])
        return _fake_complete(record)

    try:
        result = f85._run_approved_acquisition(manifest, plan, runtime_dir=runtime, evidence_path=evidence, runner=runner)
        assert result["status"] == "COMPLETE_TRAIN_TEACHER_EVIDENCE_SEALED"
        assert len(calls) == 36
        assert json.loads(evidence.read_text(encoding="utf-8"))["root_count"] == 36
    finally:
        shutil.rmtree(runtime, ignore_errors=True)


def test_f85_terminal_first_batch_stops_before_submitting_later_batches(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    calls = []
    runtime = _runtime_tmp()
    plan = _plan_file(runtime)

    def runner(record):
        calls.append(record["root_id"])
        return {"status": "TIME_CAP", "termination_reason": "per_root_wall_cap"} if len(calls) == 1 else _fake_complete(record)

    try:
        result = f85._run_approved_acquisition(manifest, plan, runtime_dir=runtime, runner=runner)
        assert result["status"] == "INCOMPLETE"
        assert len(calls) == 3
        assert result["completed_count"] == 2
        assert len(list(runtime.rglob("*.json"))) == 4
    finally:
        shutil.rmtree(runtime, ignore_errors=True)


def test_f85_same_plan_terminal_progress_never_retries_teacher(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    calls = []
    runtime = _runtime_tmp()
    plan = _plan_file(runtime)

    def failing_runner(record):
        calls.append(record["root_id"])
        return {"status": "HARNESS_MISMATCH", "error": "fake"}

    try:
        first = f85._run_approved_acquisition(manifest, plan, runtime_dir=runtime, runner=failing_runner)
        assert first["status"] == "INCOMPLETE"
        first_calls = len(calls)

        def forbidden_runner(record):
            raise AssertionError("same-plan terminal progress was retried")

        second = f85._run_approved_acquisition(manifest, plan, runtime_dir=runtime, runner=forbidden_runner)
        assert second["reason"] == "RETRY_REQUIRES_NEW_AUTHORIZATION"
        assert len(calls) == first_calls
    finally:
        shutil.rmtree(runtime, ignore_errors=True)


def test_f85_stale_complete_progress_is_not_reused(tmp_path):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    runtime = _runtime_tmp()
    plan = _plan_file(runtime)
    try:
        f85._run_approved_acquisition(manifest, plan, runtime_dir=runtime, runner=_fake_complete)
        progress = next(path for path in runtime.rglob("*.json") if path.name != "plan.json")
        prior = json.loads(progress.read_text(encoding="utf-8"))
        prior["provenance"]["manifest_content_sha256"] = "0" * 64
        progress.write_text(json.dumps(prior), encoding="utf-8")
        result = f85._run_approved_acquisition(manifest, plan, runtime_dir=runtime, runner=lambda _record: pytest.fail("stale unit reused"))
        assert result["status"] == "HARNESS_MISMATCH"
        assert result["reason"] == "STALE_PROGRESS_PROVENANCE"
    finally:
        shutil.rmtree(runtime, ignore_errors=True)


def test_f85_authorized_plan_is_exactly_three_lanes_and_two_or_four_are_rejected():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    runtime = _runtime_tmp()
    try:
        three_lane_plan = _plan_file(runtime / "three", lanes=3)
        validated, _plan_sha = f85._validate_execution_plan(three_lane_plan, manifest)
        assert validated["resource_envelope"]["intended_cpu_lanes"] == 3

        for lanes in (2, 4):
            rejected_plan = _plan_file(runtime / str(lanes), lanes=lanes)
            with pytest.raises(RuntimeError, match="authorized three-lane"):
                f85._validate_execution_plan(rejected_plan, manifest)
    finally:
        shutil.rmtree(runtime, ignore_errors=True)


@pytest.mark.parametrize("field", [
    "compute_plan_sha256",
    "manifest_content_sha256",
    "root_record_sha256",
    "c1_checkpoint_id",
    "c1_model_sha256",
    "f59_script_sha256",
    "f62_script_sha256",
])
def test_f85_every_provenance_binding_rejects_stale_complete_progress(field):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    runtime = _runtime_tmp()
    plan = _plan_file(runtime)
    try:
        f85._run_approved_acquisition(manifest, plan, runtime_dir=runtime, runner=_fake_complete)
        progress = next(path for path in runtime.rglob("*.json") if path.name != "plan.json")
        prior = json.loads(progress.read_text(encoding="utf-8"))
        prior["provenance"][field] = "0" * 64
        progress.write_text(json.dumps(prior), encoding="utf-8")
        result = f85._run_approved_acquisition(
            manifest,
            plan,
            runtime_dir=runtime,
            runner=lambda _record: pytest.fail("stale unit reused"),
        )
        assert result == {
            "status": "HARNESS_MISMATCH",
            "reason": "STALE_PROGRESS_PROVENANCE",
            "root_id": prior["root_id"],
        }
    finally:
        shutil.rmtree(runtime, ignore_errors=True)


def test_f85_harness_mismatch_first_batch_stops_before_later_batches():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    calls = []
    runtime = _runtime_tmp()
    plan = _plan_file(runtime)

    def runner(record):
        calls.append(record["root_id"])
        return {"status": "HARNESS_MISMATCH", "error": "fake"} if len(calls) == 1 else _fake_complete(record)

    try:
        result = f85._run_approved_acquisition(manifest, plan, runtime_dir=runtime, runner=runner)
        assert result["status"] == "INCOMPLETE"
        assert len(calls) == 3
        assert result["completed_count"] == 2
        assert len(list(runtime.rglob("*.json"))) == 4
    finally:
        shutil.rmtree(runtime, ignore_errors=True)
