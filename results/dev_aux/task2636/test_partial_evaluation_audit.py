from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from results.dev_aux.task2636.partial_evaluation_audit import (
    PLAN_PATH,
    FrozenSlotReplayContext,
    audit_completed_rows,
    expected_slots,
    replay_frozen_slot,
    replay_slot_history,
    validate_candidate_model_snapshots,
    validate_result_receipt,
    verify_candidate_training_receipt_links,
)


ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def frozen_inputs():
    plan = json.loads(PLAN_PATH.read_text(encoding="utf8"))
    pool_path = ROOT / plan["source_lineage"]["root_pool"]
    pool = json.loads(pool_path.read_text(encoding="utf8"))
    return plan, pool, expected_slots(plan, pool)


def row_for(key, frozen, *, ending, actual=None, reward=None, nodes=0, queries=0):
    candidate, family, color, endpoint = key
    return {
        "slot": {
            "candidate_index": candidate,
            "family": family,
            "learner_color": color,
            "endpoint": endpoint,
        },
        "candidate_seed": frozen[key]["candidate_seed"],
        "node_cap": frozen[key]["node_cap"],
        "ending": ending,
        "actual_outcome": actual,
        "reward": reward,
        "nodes": nodes,
        "queries": queries,
    }


def test_all_absent_slots_stay_in_full_pair_denominator(frozen_inputs):
    plan, pool, _frozen = frozen_inputs
    audit = audit_completed_rows([], plan, pool)
    assert audit["planned_slots"] == 1024
    assert audit["completed_slots"] == 0
    assert audit["slot_states"] == {"ACTUAL_TERMINAL": 0, "UNKNOWN": 0, "MISSING": 1024}
    assert audit["pair_count"] == 512
    assert audit["difference_sum_bounds"] == [-1024, 1024]
    assert audit["difference_mean_bounds"] == [-2.0, 2.0]


def test_unknown_and_actual_are_bounded_without_dropping_pair(frozen_inputs):
    plan, pool, frozen = frozen_inputs
    td_key = next(k for k in frozen if k[2] == 0 and k[3] == "TDLeaf")
    initial_key = (td_key[0], td_key[1], td_key[2], "initial")
    rows = [
        row_for(td_key, frozen, ending="ACTUAL_TERMINAL", actual=1, reward=1,
                nodes=1, queries=1),
        row_for(initial_key, frozen, ending="NODE_CAP_UNKNOWN"),
    ]
    audit = audit_completed_rows(rows, plan, pool)
    pair = next(p for p in audit["pairs"] if p["pair"] == list(td_key[:3]))
    assert pair["difference_bounds"] == [0, 2]
    assert audit["pair_count"] == 512
    assert audit["slot_states"]["UNKNOWN"] == 1
    assert audit["slot_states"]["MISSING"] == 1022


def test_unknown_cannot_carry_draw_or_reward(frozen_inputs):
    plan, pool, frozen = frozen_inputs
    key = next(k for k in frozen if k[3] == "initial")
    row = row_for(key, frozen, ending="HORIZON_UNKNOWN", actual=0, reward=0)
    with pytest.raises(ValueError, match="UNKNOWN cannot carry"):
        audit_completed_rows([row], plan, pool)


def test_missing_and_unrecognized_endings_cannot_masquerade_as_closed_rows(frozen_inputs):
    plan, pool, frozen = frozen_inputs
    key = next(iter(frozen))
    missing = row_for(key, frozen, ending="MISSING")
    with pytest.raises(ValueError, match="non-MISSING ending"):
        audit_completed_rows([missing], plan, pool)
    invalid = row_for(key, frozen, ending="RESOURCE_EXHAUSTED")
    with pytest.raises(ValueError, match="unrecognized completed UNKNOWN"):
        audit_completed_rows([invalid], plan, pool)


def test_duplicate_or_invalid_slot_is_rejected(frozen_inputs):
    plan, pool, frozen = frozen_inputs
    key = next(iter(frozen))
    row = row_for(key, frozen, ending="HORIZON_UNKNOWN")
    with pytest.raises(ValueError, match="duplicate evaluation slot"):
        audit_completed_rows([row, row], plan, pool)
    row["slot"]["candidate_index"] = 999
    with pytest.raises(ValueError, match="unexpected evaluation slot"):
        audit_completed_rows([row], plan, pool)


def test_slot_cap_and_terminal_perspective_are_enforced(frozen_inputs):
    plan, pool, frozen = frozen_inputs
    key = next(k for k in frozen if k[2] == 1 and k[3] == "TDLeaf")
    wrong_reward = row_for(key, frozen, ending="ACTUAL_TERMINAL", actual=1, reward=1,
                           nodes=1, queries=1)
    with pytest.raises(ValueError, match="learner perspective"):
        audit_completed_rows([wrong_reward], plan, pool)
    over_cap = row_for(key, frozen, ending="HORIZON_UNKNOWN",
                       nodes=frozen[key]["node_cap"] + 1, queries=1)
    with pytest.raises(ValueError, match="exceeded its combined"):
        audit_completed_rows([over_cap], plan, pool)


def test_final_partial_receipt_binds_slot_query_totals_and_missing_complement(frozen_inputs):
    plan, pool, frozen = frozen_inputs
    td_key = next(k for k in frozen if k[2] == 0 and k[3] == "TDLeaf")
    initial_key = (td_key[0], td_key[1], 0, "initial")
    rows = [
        row_for(td_key, frozen, ending="ACTUAL_TERMINAL", actual=1, reward=1,
                nodes=1, queries=1),
        row_for(initial_key, frozen, ending="NODE_CAP_UNKNOWN"),
    ]
    query_rows = [{"slot": rows[0]["slot"], "ply": 0, "nodes": 1,
                   "requested_nodes": 2048, "complete": True}]
    audit = audit_completed_rows(rows, plan, pool)
    receipt = {
        "status": "TIME_CAP", "plan_sha256": "0" * 64,
        "registration_sha256": "1" * 64, "training_result_sha256": "2" * 64,
        "root_pool_sha256": "3" * 64, "expected_slots": 1024,
        "completed_slots": 2, "missing_slots": audit["missing_slots"],
        "missing": 1022, "actual_terminal": 1, "UNKNOWN": 1,
        "nodes": 1, "queries": 1,
    }
    validate_result_receipt(receipt, rows, query_rows, audit)

    wrong_missing = dict(receipt, missing=1021)
    with pytest.raises(ValueError, match="missing count"):
        validate_result_receipt(wrong_missing, rows, query_rows, audit)
    bool_count = dict(receipt, actual_terminal=True)
    with pytest.raises(ValueError, match="nonnegative integer"):
        validate_result_receipt(bool_count, rows, query_rows, audit)
    duplicate_rows = [dict(row) for row in rows]
    duplicate_rows[0]["queries"] = 2
    duplicate_audit = audit_completed_rows(duplicate_rows, plan, pool)
    duplicate_query_receipt = dict(
        receipt, queries=2, completed_slots=len(duplicate_rows),
        missing_slots=duplicate_audit["missing_slots"])
    with pytest.raises(ValueError, match="contiguous per-slot prefix"):
        validate_result_receipt(duplicate_query_receipt, duplicate_rows,
                                query_rows + [dict(query_rows[0])], duplicate_audit)
    with pytest.raises(ValueError, match="lacks a durable closed slot"):
        validate_result_receipt(receipt, rows, query_rows + [{
            "slot": {"candidate_index": 15, "family": 9999999,
                     "learner_color": 0, "endpoint": "TDLeaf"},
            "ply": 0, "nodes": 1, "requested_nodes": 2048, "complete": True,
        }], audit)
    with pytest.raises(ValueError, match="not a final result receipt"):
        validate_result_receipt(dict(receipt, status="NO_FINAL_RECEIPT"), rows, query_rows, audit)


def test_complete_search_receipt_cannot_use_zero_node_replay_scaffolding(frozen_inputs):
    plan, pool, frozen = frozen_inputs
    key = next(k for k in frozen if k[2] == 0 and k[3] == "TDLeaf")
    row = row_for(key, frozen, ending="ACTUAL_TERMINAL", actual=1, reward=1,
                  nodes=0, queries=1)
    query = {"slot": row["slot"], "ply": 0, "nodes": 0,
             "requested_nodes": 2048, "complete": True}
    audit = audit_completed_rows([row], plan, pool)
    receipt = {
        "status": "TIME_CAP", "plan_sha256": "0" * 64,
        "registration_sha256": "1" * 64, "training_result_sha256": "2" * 64,
        "root_pool_sha256": "3" * 64, "expected_slots": 1024,
        "completed_slots": 1, "missing_slots": audit["missing_slots"],
        "missing": 1023, "actual_terminal": 1, "UNKNOWN": 0,
        "nodes": 0, "queries": 1,
    }
    with pytest.raises(ValueError, match="completed search query must visit at least one node"):
        validate_result_receipt(receipt, [row], [query], audit)


def test_incomplete_zero_node_query_remains_unknown(frozen_inputs):
    plan, pool, frozen = frozen_inputs
    key = next(k for k in frozen if k[2] == 0 and k[3] == "TDLeaf")
    row = row_for(key, frozen, ending="SEARCH_RESOURCE_UNKNOWN", nodes=0, queries=1)
    query = {"slot": row["slot"], "ply": 0, "nodes": 0,
             "requested_nodes": 2048, "complete": False}
    audit = audit_completed_rows([row], plan, pool)
    receipt = {
        "status": "TIME_CAP", "plan_sha256": "0" * 64,
        "registration_sha256": "1" * 64, "training_result_sha256": "2" * 64,
        "root_pool_sha256": "3" * 64, "expected_slots": 1024,
        "completed_slots": 1, "missing_slots": audit["missing_slots"],
        "missing": 1023, "actual_terminal": 0, "UNKNOWN": 1,
        "nodes": 0, "queries": 1,
    }
    validate_result_receipt(receipt, [row], [query], audit)
    assert audit["slot_states"]["UNKNOWN"] == 1
    assert audit["slot_states"]["MISSING"] == 1023


def test_candidate_model_snapshots_bind_all_frozen_indices_and_weights():
    from results.dev_aux.task2625.freeze_study import initial_vector

    initial = initial_vector(1977, 10)
    candidate_path = ROOT / "results/dev_aux/task2633/generated/candidate-index.json"
    candidate_index = json.loads(candidate_path.read_text(encoding="utf-8"))
    rows = [
        {"candidate_index": index, "candidate_seed": candidate["seed"],
         "candidate_ruleset_sha256": candidate["ruleset_sha256"],
         "initial_weights": list(initial), "final_weights": [*initial]}
        for index, candidate in enumerate(candidate_index["rows"])
    ]
    models = validate_candidate_model_snapshots(rows)
    assert set(models) == set(range(16))
    assert models[3] == initial
    assert validate_candidate_model_snapshots(rows[::-1]) == models

    with pytest.raises(ValueError, match="duplicated"):
        validate_candidate_model_snapshots(rows + [rows[0]])
    with pytest.raises(ValueError, match="cover all sixteen"):
        validate_candidate_model_snapshots(rows[:-1])


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("candidate_seed", 1, "seed differs"),
        ("candidate_ruleset_sha256", "0" * 64, "rule hash differs"),
        ("initial_weights", [1.0] * 10, "initialization differs"),
        ("final_weights", [1.0] * 9 + [float("nan")], "ten finite numeric weights"),
        ("final_weights", [1.0] * 9 + [10 ** 400], "ten finite numeric weights"),
    ],
)
def test_candidate_model_snapshots_reject_cross_binding_and_bad_vectors(field, value, message):
    from results.dev_aux.task2625.freeze_study import initial_vector

    initial = initial_vector(1977, 10)
    candidate_path = ROOT / "results/dev_aux/task2633/generated/candidate-index.json"
    candidate_index = json.loads(candidate_path.read_text(encoding="utf-8"))
    rows = [
        {"candidate_index": index, "candidate_seed": candidate["seed"],
         "candidate_ruleset_sha256": candidate["ruleset_sha256"],
         "initial_weights": list(initial), "final_weights": [*initial]}
        for index, candidate in enumerate(candidate_index["rows"])
    ]
    rows[5][field] = value
    with pytest.raises(ValueError, match=message):
        validate_candidate_model_snapshots(rows)


def test_training_receipt_links_bind_exact_registration_result_and_audit_bytes():
    from results.dev_aux.task2625.freeze_study import initial_vector

    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    lineage = plan["source_lineage"]
    index = json.loads((ROOT / lineage["candidate_index"]).read_text(encoding="utf-8"))
    initial = initial_vector(1977, 10)
    models = [
        {"candidate_index": i, "candidate_seed": row["seed"],
         "candidate_ruleset_sha256": row["ruleset_sha256"],
         "initial_weights": list(initial), "final_weights": [*initial]}
        for i, row in enumerate(index["rows"])
    ]
    registration = {
        "plan_sha256": hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest(),
        "root_pool_sha256": lineage["root_pool_sha256"],
        "candidate_index_sha256": lineage["candidate_index_sha256"],
    }
    registration_raw = json.dumps(registration, sort_keys=True).encode("utf-8")
    result = {
        **registration,
        "registration_sha256": hashlib.sha256(registration_raw).hexdigest(),
        "candidate_models": models,
    }
    result_raw = json.dumps(result, sort_keys=True).encode("utf-8")
    audit = {
        **registration,
        "registration_sha256": hashlib.sha256(registration_raw).hexdigest(),
        "training_result_sha256": hashlib.sha256(result_raw).hexdigest(),
    }
    audit_raw = json.dumps(audit, sort_keys=True).encode("utf-8")

    linked = verify_candidate_training_receipt_links(
        registration_raw, result_raw, audit_raw)
    assert linked["training_result_sha256"] == hashlib.sha256(result_raw).hexdigest()
    assert set(linked["candidate_models"]) == set(range(16))

    with pytest.raises(ValueError, match="exact registration/result bytes"):
        verify_candidate_training_receipt_links(
            registration_raw, result_raw + b" ", audit_raw)
    with pytest.raises(ValueError, match="exact registration bytes"):
        verify_candidate_training_receipt_links(
            registration_raw + b" ", result_raw, audit_raw)


@pytest.mark.parametrize("duplicate_artifact", [
    "registration", "training result", "training audit", "nested candidate model",
    "non-standard JSON constant",
])
def test_training_receipt_links_reject_duplicate_json_keys(duplicate_artifact):
    from results.dev_aux.task2625.freeze_study import initial_vector

    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    lineage = plan["source_lineage"]
    index = json.loads((ROOT / lineage["candidate_index"]).read_text(encoding="utf-8"))
    initial = initial_vector(1977, 10)
    models = [
        {"candidate_index": i, "candidate_seed": row["seed"],
         "candidate_ruleset_sha256": row["ruleset_sha256"],
         "initial_weights": list(initial), "final_weights": list(initial)}
        for i, row in enumerate(index["rows"])
    ]
    registration = {
        "plan_sha256": hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest(),
        "root_pool_sha256": lineage["root_pool_sha256"],
        "candidate_index_sha256": lineage["candidate_index_sha256"],
    }
    registration_raw = json.dumps(registration, sort_keys=True).encode("utf-8")
    if duplicate_artifact == "registration":
        registration_raw = registration_raw[:-1] + (
            b',"plan_sha256":"' + b"0" * 64 + b'"}')
    registration_sha = hashlib.sha256(registration_raw).hexdigest()
    result = {
        **registration,
        "registration_sha256": registration_sha,
        "candidate_models": models,
    }
    result_raw = json.dumps(result, sort_keys=True).encode("utf-8")
    if duplicate_artifact == "training result":
        result_raw = result_raw[:-1] + (
            b',"registration_sha256":"' + b"0" * 64 + b'"}')
    elif duplicate_artifact == "nested candidate model":
        result_raw = result_raw.replace(
            b'"candidate_index": 0',
            b'"candidate_index": 0,"candidate_index":0', 1)
    result_sha = hashlib.sha256(result_raw).hexdigest()
    audit = {
        **registration,
        "registration_sha256": registration_sha,
        "training_result_sha256": result_sha,
    }
    audit_raw = json.dumps(audit, sort_keys=True).encode("utf-8")
    if duplicate_artifact == "training audit":
        audit_raw = audit_raw[:-1] + (
            b',"training_result_sha256":"' + b"0" * 64 + b'"}')
    elif duplicate_artifact == "non-standard JSON constant":
        audit_raw = audit_raw[:-1] + b',"extension":NaN}'

    expected_error = ("non-standard JSON constant" if
                      duplicate_artifact == "non-standard JSON constant" else
                      "duplicate JSON object keys")
    with pytest.raises(ValueError, match=expected_error):
        verify_candidate_training_receipt_links(
            registration_raw, result_raw, audit_raw)


@pytest.mark.parametrize("artifact_name", [
    "registration", "training result", "training audit",
])
@pytest.mark.parametrize("pin_name", [
    "plan_sha256", "root_pool_sha256", "candidate_index_sha256",
])
def test_training_receipt_links_reject_each_cross_artifact_frozen_pin(
        artifact_name, pin_name):
    from results.dev_aux.task2625.freeze_study import initial_vector

    plan_raw = PLAN_PATH.read_bytes()
    plan = json.loads(plan_raw)
    lineage = plan["source_lineage"]
    index = json.loads((ROOT / lineage["candidate_index"]).read_text(encoding="utf-8"))
    initial = initial_vector(1977, 10)
    models = [
        {"candidate_index": i, "candidate_seed": row["seed"],
         "candidate_ruleset_sha256": row["ruleset_sha256"],
         "initial_weights": list(initial), "final_weights": list(initial)}
        for i, row in enumerate(index["rows"])
    ]
    pins = {
        "plan_sha256": hashlib.sha256(plan_raw).hexdigest(),
        "root_pool_sha256": lineage["root_pool_sha256"],
        "candidate_index_sha256": lineage["candidate_index_sha256"],
    }
    registration = dict(pins)
    result = {**pins, "candidate_models": models}
    audit = dict(pins)
    if artifact_name == "registration":
        registration[pin_name] = "f" * 64
    registration_raw = json.dumps(registration, sort_keys=True).encode("utf-8")
    result["registration_sha256"] = hashlib.sha256(registration_raw).hexdigest()
    if artifact_name == "training result":
        result[pin_name] = "f" * 64
    result_raw = json.dumps(result, sort_keys=True).encode("utf-8")
    audit["registration_sha256"] = hashlib.sha256(registration_raw).hexdigest()
    audit["training_result_sha256"] = hashlib.sha256(result_raw).hexdigest()
    if artifact_name == "training audit":
        audit[pin_name] = "f" * 64
    audit_raw = json.dumps(audit, sort_keys=True).encode("utf-8")

    with pytest.raises(ValueError, match="differs from frozen task2636 inputs"):
        verify_candidate_training_receipt_links(
            registration_raw, result_raw, audit_raw)


def test_query_replayer_checks_one_legal_history_append_without_running_search():
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.session.serialization import deserialize_game_record
    from generic_chess.session.session import GameSession
    from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv

    plan = json.loads(PLAN_PATH.read_text(encoding="utf8"))
    index_path = ROOT / plan["source_lineage"]["candidate_index"]
    index = json.loads(index_path.read_text(encoding="utf8"))
    candidate = index["rows"][0]
    rule_path = ROOT / candidate["source_file"]
    assert hashlib.sha256(rule_path.read_bytes()).hexdigest() == candidate["ruleset_sha256"]
    compiled = compile_ruleset_for_execution(
        ruleset_from_dict(json.loads(rule_path.read_text(encoding="utf8"))))
    pool_path = ROOT / plan["source_lineage"]["root_pool"]
    pool = json.loads(pool_path.read_text(encoding="utf8"))
    root = next(r for r in pool["evaluation_roots"] if r["candidate_index"] == 0)
    env = FixedScaleSessionEnv(GameSession.replay(
        compiled, deserialize_game_record(json.dumps(root["record"]))))
    actor = env.player()
    cap = expected_slots(plan, pool)[(0, root["family"], actor, "TDLeaf")]["node_cap"]
    learner_color = actor
    slot = {"candidate_index": 0, "family": root["family"],
            "learner_color": learner_color, "endpoint": "TDLeaf"}
    weights = [1.0] + [0.0] * 9
    foe = [1.0] * 10
    before = env.record()
    action = env.actions()[0]
    # FixedScaleSessionEnv.actions() already returns typed SessionChoice rows.
    env.push(action)
    after = env.record()
    slot_record = {"slot": slot, "candidate_seed": root["candidate_seed"],
                   "node_cap": cap, "initial_record": before,
                   "final_record": after, "nodes": 1, "queries": 1,
                   "ending": "STOPPED_USER_UNKNOWN", "actual_outcome": None,
                   "reward": None}
    query = {"slot": slot, "ply": 0, "actor": actor, "weights": weights,
             "record_before": before, "record_after": after, "complete": True,
             "nodes": 1, "requested_nodes": 2048}
    receipt = replay_slot_history(before, slot_record, [query], compiled,
                                  weights, foe, cap, 2048)
    assert receipt["queries"] == 1 and receipt["nodes"] == 1
    replay_context = FrozenSlotReplayContext()
    bound = replay_context.replay(slot_record, [query], weights, foe)
    bound_again = replay_context.replay(slot_record, [query], weights, foe)
    assert bound_again["final_record"] == bound["final_record"]
    assert len(replay_context.compiled) == 1
    assert bound["candidate_index"] == 0
    assert bound["candidate_ruleset_sha256"] == candidate["ruleset_sha256"]
    assert bound["root_pool_sha256"] == plan["source_lineage"]["root_pool_sha256"]
    assert len(bound["replay_runtime_source_hashes"]) == 14
    from results.dev_aux.task2625.freeze_study import initial_vector
    initial_weights = initial_vector(1977, dimension=10)
    initial_slot = dict(slot_record, slot={**slot, "endpoint": "initial"})
    initial_query = dict(query, slot=initial_slot["slot"], weights=initial_weights)
    initial_replay = replay_context.replay(initial_slot, [initial_query],
                                           initial_weights, foe)
    assert initial_replay["candidate_ruleset_sha256"] == candidate["ruleset_sha256"]
    with pytest.raises(ValueError, match="seed-1977 vector"):
        replay_context.replay(initial_slot, [initial_query], [0.0] * 10, foe)
    with pytest.raises(ValueError, match="all-ones model"):
        replay_context.replay(slot_record, [query], weights, [0.0] * 10)
    wrong_seed_row = dict(slot_record, candidate_seed=root["candidate_seed"] + 1)
    with pytest.raises(ValueError, match="candidate seed"):
        replay_context.replay(wrong_seed_row, [query], weights, foe)
    query["weights"] = foe
    with pytest.raises(ValueError, match="model weights"):
        replay_slot_history(before, slot_record, [query], compiled,
                             weights, foe, cap, 2048)
    query["weights"] = weights
    query["actor"] = bool(actor)
    with pytest.raises(ValueError, match="query ply/actor"):
        replay_slot_history(before, slot_record, [query], compiled,
                             weights, foe, cap, 2048)
    query["actor"] = actor
    query["ply"] = False
    with pytest.raises(ValueError, match="query ply/actor"):
        replay_slot_history(before, slot_record, [query], compiled,
                             weights, foe, cap, 2048)
    query["ply"] = 0
    query["weights"] = [True] + [False] * 9
    with pytest.raises(ValueError, match="model weights"):
        replay_slot_history(before, slot_record, [query], compiled,
                             weights, foe, cap, 2048)
    query["weights"] = weights
    query["record_before"] = after
    with pytest.raises(ValueError, match="pre-state"):
        replay_slot_history(before, slot_record, [query], compiled,
                             weights, foe, cap, 2048)
    query["record_before"] = before
    query["record_after"] = before
    with pytest.raises(ValueError, match="append exactly one legal action"):
        replay_slot_history(before, slot_record, [query], compiled,
                             weights, foe, cap, 2048)
    query["record_after"] = after
    slot_record["final_record"] = before
    with pytest.raises(ValueError, match="final history"):
        replay_slot_history(before, slot_record, [query], compiled,
                             weights, foe, cap, 2048)

    # A stopped, incomplete query is a closed UNKNOWN slot with no move.
    query.update(complete=False, nodes=0, record_after=before)
    slot_record.update(final_record=before, nodes=0)
    stopped = replay_slot_history(before, slot_record, [query], compiled,
                                  weights, foe, cap, 2048)
    assert stopped["ending"] == "STOPPED_USER_UNKNOWN"
    assert stopped["actual_outcome"] is None and stopped["nodes"] == 0

    # A caller cannot turn that same nonterminal closure into an actual draw.
    slot_record.update(ending="ACTUAL_TERMINAL", actual_outcome=0, reward=0)
    with pytest.raises(ValueError, match="nonterminal/non-scoring slot"):
        replay_slot_history(before, slot_record, [query], compiled,
                             weights, foe, cap, 2048)


def test_frozen_replayer_fails_closed_on_study_plan_drift(monkeypatch):
    from results.dev_aux.task2636 import partial_evaluation_audit as audit_module

    monkeypatch.setattr(audit_module, "FROZEN_PLAN_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="audited frozen plan"):
        replay_frozen_slot({}, [], [], [])


def test_frozen_replay_rejects_a_fabricated_non_pool_terminal_record(frozen_inputs):
    """A fabricated terminal label cannot make a non-pool record admissible."""
    _plan, _pool, frozen = frozen_inputs
    context = FrozenSlotReplayContext()
    key = next(k for k in frozen if k[0] == 0 and k[3] == "TDLeaf")
    root = context.roots[(key[0], key[1])]
    row = row_for(key, frozen, ending="ACTUAL_TERMINAL", actual=1, reward=1,
                  nodes=0, queries=0)
    row.update(initial_record={"ruleset_fingerprint": "constructed-mate", "actions": []},
               final_record={"ruleset_fingerprint": "constructed-mate", "actions": []},
               candidate_seed=root["candidate_seed"])

    with pytest.raises(ValueError, match="slot initial history differs from the frozen root"):
        context.replay(row, [], [0.0] * 10, [1.0] * 10)


def test_frozen_candidate_actual_terminal_fixture_replays_to_rule_outcome():
    """Replay an actual candidate-bound terminal path; fixture queries are scaffolding only."""
    from generic_chess.rules.compiler import compile_ruleset_for_execution
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.session.serialization import deserialize_game_record
    from generic_chess.session.session import GameSession
    from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv
    from scripts.generic_session_win_proof import SessionChoice

    fixture_path = ROOT / "results/dev_aux/task2636/two-ply-terminal-fixture-screen-incremental.json"
    fixture_raw = fixture_path.read_bytes()
    assert hashlib.sha256(fixture_raw).hexdigest() == (
        "77114c7caec9570f2080c931fb7c249074da5874e4e5cd47ffd616f0e19d17c5")
    screen = json.loads(fixture_raw)
    assert screen["source_script_sha256"] == (
        "34535198cd0eeba756ac11375137802d66798b90edfcfd727ab6322f398d6359")
    assert screen["status"] == "FOUND_FROZEN_CANDIDATE_TERMINAL_FIXTURE"
    fixture = screen["fixture"]
    assert fixture["ending"] == "ACTUAL_TERMINAL"

    context = FrozenSlotReplayContext()
    key = (fixture["candidate_index"], fixture["family"], 0, "TDLeaf")
    frozen = context.frozen[key]
    root = context.roots[(fixture["candidate_index"], fixture["family"])]
    candidate = context.candidate_index["rows"][fixture["candidate_index"]]
    rule_raw = (ROOT / candidate["source_file"]).read_bytes()
    compiled = compile_ruleset_for_execution(
        ruleset_from_dict(json.loads(rule_raw.decode("utf-8"))))
    root_record = root["record"]
    final_actions = deserialize_game_record(json.dumps(fixture["final_record"])).actions
    root_actions = deserialize_game_record(json.dumps(root_record)).actions
    assert final_actions[:len(root_actions)] == root_actions
    added_actions = final_actions[len(root_actions):]
    assert len(added_actions) == fixture["plies"] == 2

    env = FixedScaleSessionEnv(GameSession.replay(
        compiled, deserialize_game_record(json.dumps(root_record))))
    weights, foe = [0.0] * 10, [1.0] * 10
    queries = []
    for ply, action in enumerate(added_actions):
        actor = env.player()
        before = env.record()
        env.push(SessionChoice("ACTION", action=action))
        after = env.record()
        # These zero-node rows are replay-test scaffolding, not search receipts.
        queries.append({"slot": {"candidate_index": key[0], "family": key[1],
                                  "learner_color": key[2], "endpoint": key[3]},
                        "ply": ply, "actor": actor,
                        "weights": weights if actor == 0 else foe,
                        "record_before": before, "record_after": after,
                        "complete": True, "nodes": 0, "requested_nodes": 2048})

    actual = env.terminal()
    assert actual == fixture["actual_outcome"]
    row = {"slot": {"candidate_index": key[0], "family": key[1],
                     "learner_color": key[2], "endpoint": key[3]},
           "candidate_seed": frozen["candidate_seed"], "node_cap": frozen["node_cap"],
           "initial_record": root_record, "final_record": env.record(),
           "ending": "ACTUAL_TERMINAL", "actual_outcome": actual,
           "reward": actual, "nodes": 0, "queries": len(queries)}
    replayed = context.replay(row, queries, weights, foe)
    assert replayed["actual_outcome"] == actual
    assert replayed["ending"] == "ACTUAL_TERMINAL"

    # The replay-only fixture is not a search receipt: composing it with the
    # structural receipt validator must reject its complete zero-node queries.
    audit = audit_completed_rows([row], context.plan, context.pool)
    receipt = {
        "status": "TIME_CAP", "plan_sha256": "0" * 64,
        "registration_sha256": "1" * 64, "training_result_sha256": "2" * 64,
        "root_pool_sha256": "3" * 64, "expected_slots": 1024,
        "completed_slots": 1, "missing_slots": audit["missing_slots"],
        "missing": 1023, "actual_terminal": 1, "UNKNOWN": 0,
        "nodes": 0, "queries": len(queries),
    }
    with pytest.raises(ValueError, match="completed search query must visit at least one node"):
        validate_result_receipt(receipt, [row], queries, audit)


def test_frozen_replayer_fails_closed_on_runtime_source_drift(monkeypatch):
    from results.dev_aux.task2636 import partial_evaluation_audit as audit_module

    monkeypatch.setitem(audit_module.REPLAY_RUNTIME_PINS,
                        "generic_chess/core/transition.py", "0" * 64)
    with pytest.raises(ValueError, match="replay runtime source hash mismatch"):
        replay_frozen_slot({}, [], [], [])
