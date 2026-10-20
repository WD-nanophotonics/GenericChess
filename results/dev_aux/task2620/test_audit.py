"""Actual-search audit acceptance and adversarial receipt regressions."""
import copy
import datetime
import json
from pathlib import Path

import chess
import pytest

from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2620 import audit as auditor, evaluate as evaluator


def dump(path, value):
    raw = (json.dumps(value, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    return auditor.sha(raw)


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def write_rows(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


@pytest.fixture
def actual_run(tmp_path, monkeypatch, request):
    run = tmp_path / "run"
    run.mkdir()
    (tmp_path / ".local_agent").mkdir()
    for module in (evaluator, auditor):
        monkeypatch.setattr(module, "ROOT", tmp_path)
        monkeypatch.setattr(module, "RUN", run)
        monkeypatch.setattr(module, "require_identity", lambda: None)
    monkeypatch.setattr(evaluator, "SharedDeleteStopReader", lambda root: lambda: None)
    dump(tmp_path / ".local_agent/session.json", dict(state="active", id="same-segment"))
    original = dict(seeds=[7], methods=["TreeStrap", "TDLeaf", "WDL"],
                    nodes_per_seed_method_arm=100)
    original_sha = dump(tmp_path / "original-plan.json", original)
    arms = [dict(seed=7, seed_index=0, method=method, status="NODE_BUDGET_REACHED",
                 nodes_total=100, initial_weights=[1.] * 5, final_weights=[1.] * 5,
                 training_loss_mean=0., training_loss_terms=1, tree_samples=0,
                 tree_active_samples=0, td_observations=0, update_steps=0,
                 actual_terminal_games=0, unknown_games=0, missing_slots=0,
                 weights_are_strength_evidence=False) for method in original["methods"]]
    training_sha = dump(run / "training-result.json", dict(
        status="COMPLETE_TRAINING", eligible_for_evaluation=True,
        plan_sha256=original_sha, arms=arms))
    board = chess.Board(getattr(request, "param", chess.STARTING_FEN))
    roots_sha = dump(run / "evaluation-root-manifest.json", dict(
        roots=[dict(family=1, record=ChessEnv(board).record())]))
    stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    slots = [[0, 7, 1, color, endpoint] for color in (0, 1)
             for endpoint in ("initial", "TreeStrap", "TDLeaf", "WDL")]
    plan = dict(task="audit-unit", source_sha256={}, python_chess_version=chess.__version__,
                registered_at=stamp, preparation_started_at=stamp, session_id="same-segment",
                seeds=[7], training_plan_path="original-plan.json",
                training_plan_sha256=original_sha, training_result_sha256=training_sha,
                evaluation_root_manifest_sha256=roots_sha, all_in_hard_cap_seconds=60,
                fixed_foe_weights=[1.] * 5,
                evaluation=dict(root_count=1, expected_slots=8, ordered_slots=slots,
                                caps_by_family={"1": 4096}, cap_values_nodes_both_sides=[4096],
                                hard_cap_seconds=30, max_plies_per_game=2, nodes_per_search=2048,
                                seconds_per_search=5, ordering_seed_base=123, depth=1, q_limit=1))
    plan_sha = dump(run / "plan.json", plan)
    dump(run / "registration.json", dict(status="REGISTERED_PRE_EVALUATION",
        plan_sha256=plan_sha, training_result_sha256=training_sha, source_sha256={}))
    command = ["unit-python", "actual-search-test"]
    dump(run / "launch-claim.json", dict(command=command, utc=stamp))
    dump(run / "launch-started.json", dict(command=command, pid=123, utc=stamp))
    result = evaluator.evaluate()
    ended = datetime.datetime.now(datetime.timezone.utc)
    wall = (ended - datetime.datetime.fromisoformat(stamp)).total_seconds()
    dump(run / "launch-exit.json", dict(return_code=0, wall_seconds=wall, utc=ended.isoformat()))
    assert result["actual_slots"] == 8
    return run


def test_actual_search_full_audit_and_write_once(actual_run):
    result = auditor.audit()
    assert result["status"] == "PASS"
    assert result["game_receipts"] == 8 and result["query_receipts"] == 16
    assert result["unknown"] == 8 and result["actual_terminal"] == 0
    assert result["missing_slots"] == []
    assert len(result["finite_panel_contrasts"]) == 6
    assert all(row["difference_bounds"] == [-2., 2.]
               for row in result["finite_panel_contrasts"])
    with pytest.raises(FileExistsError, match="write-once"):
        auditor.audit()


@pytest.mark.parametrize("field,value,error", [
    ("action", "a1a8", "illegal Chess move"),
    ("weights", [1., 2., 3., 4., 5.], "wrong actor weights"),
    ("total_slot_nodes_both_sides", 99999, "cumulative both-side nodes"),
    ("nodes", 99999, "node receipt exceeds"),
    ("ordering_seed", -1, "ordering seed mismatch"),
    ("actor", 1, "actor/color mismatch"),
])
def test_query_corruption_is_rejected(actual_run, field, value, error):
    path = actual_run / "evaluation-queries.jsonl"
    rows = read_rows(path)
    rows[0][field] = value
    write_rows(path, rows)
    with pytest.raises(ValueError, match=error):
        auditor.audit()
    assert not (actual_run / "independent-audit.json").exists()


@pytest.mark.parametrize("field,value,error", [
    ("outcome_white_relative", 0, "actual terminal Chess result"),
    ("unknown_is_draw", True, "converted UNKNOWN to draw"),
    ("nodes", 99999, "node/query totals"),
    ("ending", "ACTUAL_TERMINAL", "claims terminal"),
    ("ending", "SEARCH_RESOURCE_UNKNOWN", "incomplete search receipt"),
])
def test_game_corruption_is_rejected(actual_run, field, value, error):
    path = actual_run / "evaluation-games.jsonl"
    rows = read_rows(path)
    rows[0][field] = value
    write_rows(path, rows)
    with pytest.raises(ValueError, match=error):
        auditor.audit()


def test_incomplete_query_cannot_resume_same_slot(actual_run):
    path = actual_run / "evaluation-queries.jsonl"
    rows = read_rows(path)
    rows[0].update(complete=False, action=None, value=None,
                   record_after=copy.deepcopy(rows[0]["record_before"]))
    write_rows(path, rows)
    with pytest.raises(ValueError, match="continued after an incomplete"):
        auditor.audit()


def test_missing_final_receipt_does_not_invent_closure(actual_run):
    (actual_run / "launch-exit.json").unlink()
    with pytest.raises(FileNotFoundError, match="run is not closed"):
        auditor.audit()
    assert not (actual_run / "independent-audit.json").exists()


def test_missing_slots_stay_in_full_contrast_denominator(actual_run):
    games = read_rows(actual_run / "evaluation-games.jsonl")
    queries = read_rows(actual_run / "evaluation-queries.jsonl")
    write_rows(actual_run / "evaluation-games.jsonl", games[:4])
    write_rows(actual_run / "evaluation-queries.jsonl", [q for q in queries if q["slot_index"] < 4])
    path = actual_run / "evaluation-result.json"
    result = json.loads(path.read_text())
    result.update(status="PARTIAL_GLOBAL_CAP", actual_slots=4, missing_slots=[4, 5, 6, 7],
                  unknown=4, nodes=sum(g["nodes"] for g in games[:4]),
                  queries=sum(g["searches"] for g in games[:4]))
    dump(path, result)
    audited = auditor.audit()
    assert audited["missing_slots"] == [4, 5, 6, 7]
    assert all(c["matched_slots_planned"] == 2 and c["observed_pair_slots"] == 1
               and c["difference_bounds"] == [-2., 2.]
               for c in audited["finite_panel_contrasts"])


@pytest.mark.parametrize("actual_run", ["7k/8/5KQ1/8/8/8/8/8 w - - 0 1"], indirect=True)
def test_actual_checkmate_replay_and_learner_color_sign(actual_run):
    result = auditor.audit()
    assert result["actual_terminal"] == 8 and result["unknown"] == 0
    assert result["query_receipts"] == 8
    rows = read_rows(actual_run / "evaluation-games.jsonl")
    assert all(row["outcome_white_relative"] == 1 for row in rows)
    assert all(row["learner_reward"] == (1 if row["learner_color"] == 0 else -1)
               for row in rows)
    assert all(c["difference_bounds"] == [0., 0.] for c in result["finite_panel_contrasts"])


def test_abnormal_launcher_exit_cannot_claim_audit_pass(actual_run):
    path = actual_run / "launch-exit.json"
    row = json.loads(path.read_text())
    row["return_code"] = 1
    dump(path, row)
    with pytest.raises(ValueError, match="did not exit successfully"):
        auditor.audit()


def test_frozen_source_digest_is_checked_before_replay(actual_run):
    path = actual_run / "plan.json"
    plan = json.loads(path.read_text())
    plan["source_sha256"] = {"source.py": "0" * 64}
    (auditor.ROOT / "source.py").write_text("actual bytes")
    plan_sha = dump(path, plan)
    path = actual_run / "registration.json"
    registration = json.loads(path.read_text())
    registration.update(plan_sha256=plan_sha, source_sha256=plan["source_sha256"])
    dump(path, registration)
    with pytest.raises(ValueError, match="pinned source changed"):
        auditor.audit()
