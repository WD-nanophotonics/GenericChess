from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from types import SimpleNamespace

from results.dev_aux.task2625.freeze_study import initial_vector
from results.dev_aux.task109.adapter import PersistentStop
from results.dev_aux.task2492.learning import AlphaBeta, Receipt
from results.dev_aux.task2511.generic import NonScoringTerminal
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from results.dev_aux.task2636.candidate_training import (
    CandidateTrainingJournal,
    audit_candidate_training_arm_prefix,
    build_candidate_arm_inputs,
    apply_training_search_receipt,
    execute_candidate_training_query,
    finish_candidate_episode,
    initialize_candidate_arm,
    iter_training_episodes,
    read_newline_jsonl_prefix,
    replay_training_root,
    recovered_training_status,
    replay_closed_training_episode,
    run_candidate_training_arm,
    run_candidate_training_episode,
)


def frozen_inputs():
    from results.dev_aux.task2636.partial_evaluation_audit import PLAN_PATH, ROOT

    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    lineage = plan["source_lineage"]
    index = json.loads((ROOT / lineage["candidate_index"]).read_text(encoding="utf-8"))
    pool = json.loads((ROOT / lineage["root_pool"]).read_text(encoding="utf-8"))
    return plan, index, pool


def test_candidate_training_inputs_bind_positional_arms_and_separate_seeds():
    plan, index, pool = frozen_inputs()
    arms = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)

    assert [arm.candidate_index for arm in arms] == list(range(16))
    assert [arm.candidate_seed for arm in arms] == [row["seed"] for row in index["rows"]]
    assert all(len(arm.roots) == 120 for arm in arms)
    assert all(arm.initial_weights == arms[0].initial_weights for arm in arms)
    assert all(arm.initial_weights[0] == 1.0 for arm in arms)
    assert all(root["candidate_seed"] == arm.candidate_seed
               for arm in arms for root in arm.roots)


@pytest.mark.parametrize("mutation", ["seed", "rule_hash", "family", "candidate_index"])
def test_candidate_training_inputs_reject_cross_candidate_root_binding(mutation):
    plan, index, pool = frozen_inputs()
    changed = json.loads(json.dumps(pool))
    root = changed["training_roots"][0]
    if mutation == "seed":
        root["candidate_seed"] += 1
    elif mutation == "rule_hash":
        root["rule_sha256"] = "0" * 64
    elif mutation == "family":
        duplicate = next(row["family"] for row in changed["training_roots"][1:]
                         if row["candidate_index"] == root["candidate_index"])
        root["family"] = duplicate
    else:
        root["candidate_index"] = 16

    with pytest.raises(ValueError):
        build_candidate_arm_inputs(plan, index, changed, initial_vector=initial_vector)


def test_candidate_training_inputs_require_the_frozen_unregistered_pool():
    plan, index, pool = frozen_inputs()
    pool["root_pool_registered"] = True
    with pytest.raises(ValueError, match="unregistered frozen roots"):
        build_candidate_arm_inputs(plan, index, pool, initial_vector=initial_vector)


@pytest.mark.parametrize(
    "mutation", ["channel_order", "feature_nan", "missing_root", "record_hash", "fingerprint"])
def test_candidate_training_inputs_reject_frozen_root_schema_drift(mutation):
    plan, index, pool = frozen_inputs()
    changed = json.loads(json.dumps(pool))
    root = changed["training_roots"][0]
    if mutation == "channel_order":
        root["channels"][0], root["channels"][1] = root["channels"][1], root["channels"][0]
    elif mutation == "feature_nan":
        root["features"][0] = float("nan")
    elif mutation == "record_hash":
        root["record"]["actions"].pop()
    elif mutation == "fingerprint":
        root["ruleset_fingerprint"] = "0" * 64
    else:
        changed["training_roots"].pop()

    with pytest.raises(ValueError):
        build_candidate_arm_inputs(plan, index, changed, initial_vector=initial_vector)


@pytest.mark.parametrize("weights", [[0.0] * 10, [1.0, *([float("inf")] * 9)]])
def test_candidate_training_inputs_reject_nonfrozen_initialization(weights):
    plan, index, pool = frozen_inputs()
    with pytest.raises(ValueError, match="initialization"):
        build_candidate_arm_inputs(
            plan, index, pool, initial_vector=lambda seed, dimension: list(weights))


def test_candidate_training_inputs_require_one_shared_initial_vector():
    plan, index, pool = frozen_inputs()
    calls = 0

    def changing_initial_vector(seed, dimension):
        nonlocal calls
        calls += 1
        return [1.0, *([float(calls)] * (dimension - 1))]

    with pytest.raises(ValueError, match="share the frozen initialization"):
        build_candidate_arm_inputs(
            plan, index, pool, initial_vector=changing_initial_vector)


def test_candidate_runtime_preserves_task2625_model_foe_and_learner_contract():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[7]
    runtime = initialize_candidate_arm(arm)

    assert runtime.identity is arm
    assert runtime.model.weights == list(arm.initial_weights)
    assert runtime.model.fixed == runtime.foe.fixed == 0
    assert runtime.model.scale == runtime.foe.scale == 10.0
    assert runtime.model.weights[0] == 1.0
    assert runtime.foe.weights == [1.0] * 10
    assert runtime.learner.eta == 0.05
    assert runtime.learner.lam == 0.95


def test_unknown_episode_resets_td_trace_without_imputing_a_draw():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime = initialize_candidate_arm(arm)
    receipt = Receipt(None, 0.8, (0.0, 1.0, *([0.0] * 8)), False, (),
                      1, True, 0, 0.0, "complete")
    runtime.learner.observe(runtime.model, receipt)
    before_unknown = list(runtime.model.weights)
    finish_candidate_episode(runtime, None)
    assert runtime.model.weights == before_unknown
    assert runtime.learner.rows == []
    assert runtime.learner.snapshot is None

    runtime = initialize_candidate_arm(arm)
    runtime.model.weights = [1.0, 0.5, *([0.0] * 8)]
    runtime.learner.observe(runtime.model, receipt)
    before_draw = list(runtime.model.weights)
    finish_candidate_episode(runtime, 0)
    assert runtime.model.weights != before_draw


@pytest.mark.parametrize("outcome", [True, -0.5, 2, float("nan")])
def test_episode_finish_rejects_nonterminal_or_ambiguous_outcomes(outcome):
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime = initialize_candidate_arm(arm)

    with pytest.raises(ValueError, match="actual terminal W/L/D"):
        finish_candidate_episode(runtime, outcome)


class _FakeSession:
    def __init__(self):
        self.state = ("root", 0)


class _FakeEnv:
    def __init__(self, actor=0):
        self.actor = actor
        self.history = []
        self.session = _FakeSession()
        self.replayed = 0

    def player(self):
        return self.actor

    def record(self):
        return list(self.history)

    def push(self, action):
        self.history.append(action)
        self.actor = 1 - self.actor
        self.session.state = ("after", self.actor)

    def replay(self):
        self.replayed += 1


class _TinySearchEnv(_FakeEnv):
    def features(self):
        return (0.0, float(self.history[-1] if self.history else 0), *([0.0] * 8))

    def terminal(self):
        return None

    def actions(self):
        return list(range(self.branching)) if len(self.history) < self.tree_depth else []

    def in_check(self):
        return False

    def tactical(self, action):
        return False

    def push(self, action):
        self.history.append(action)
        old = self.actor, self.session.state
        self._undo.append(old)
        self.actor = 1 - self.actor
        self.session.state = ("path", tuple(self.history))

    def pop(self):
        self.history.pop()
        self.actor, self.session.state = self._undo.pop()

    def __init__(self, actor=0, *, tree_depth=1, branching=2):
        super().__init__(actor)
        self._undo = []
        self.tree_depth = tree_depth
        self.branching = branching


def test_incomplete_search_receipt_does_not_update_or_advance_candidate_game():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime, env = initialize_candidate_arm(arm), _FakeEnv(actor=0)
    receipt = Receipt(None, None, None, False, (), 4, False, 0, 0.0, "STOPPED_USER")

    step = apply_training_search_receipt(
        runtime, env, learner_color=0, receipt=receipt)

    assert step.complete is False and step.moved is False
    assert env.history == [] and env.replayed == 0
    assert runtime.learner.rows == []


@pytest.mark.parametrize(("actor", "learner_color", "observed"), [(0, 0, 1), (0, 1, 0)])
def test_complete_search_receipt_advances_once_and_updates_only_on_learner_turn(
        actor, learner_color, observed):
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime, env = initialize_candidate_arm(arm), _FakeEnv(actor=actor)
    receipt = Receipt("move", 0.2, (0.0, 1.0, *([0.0] * 8)), False, (),
                      8, True, 0, 0.0, "complete")

    step = apply_training_search_receipt(
        runtime, env, learner_color=learner_color, receipt=receipt)

    assert step.complete and step.moved
    assert env.history == ["move"] and env.replayed == 1
    assert len(runtime.learner.rows) == observed


def test_candidate_query_selects_learner_or_foe_and_applies_one_complete_receipt():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime, env = initialize_candidate_arm(arm), _FakeEnv(actor=0)
    selected = []

    def search(search_env, model, **kwargs):
        selected.append(model)
        return Receipt("move", 0.2, (0.0, 1.0, *([0.0] * 8)), False, (),
                       8, True, 0, 0.0, "complete")

    receipt, step = execute_candidate_training_query(
        runtime, env, learner_color=0, search=search, nodes=32, seconds=1.0,
        seed=17, cancel=lambda: None)

    assert receipt.complete and step.learner_turn and step.moved
    assert selected == [runtime.model]
    assert env.history == ["move"] and len(runtime.learner.rows) == 1


def test_candidate_query_rejects_search_that_mutates_game_history():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime, env = initialize_candidate_arm(arm), _FakeEnv(actor=0)

    def mutating_search(search_env, model, **kwargs):
        search_env.history.append("illegal-search-side-effect")
        return Receipt("move", 0.2, (0.0, 1.0, *([0.0] * 8)), False, (),
                       8, True, 0, 0.0, "complete")

    with pytest.raises(AssertionError, match="mutated the complete game history"):
        execute_candidate_training_query(
            runtime, env, learner_color=0, search=mutating_search, nodes=32,
            seconds=1.0, seed=17, cancel=lambda: None)


def test_actual_alphabeta_cancel_closes_incomplete_receipt_without_advancing():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime, env = initialize_candidate_arm(arm), _TinySearchEnv(actor=0)

    def stopped():
        raise PersistentStop("persistent user stop")

    search = lambda search_env, model, **kwargs: AlphaBeta(1, 0).search(
        search_env, model, **kwargs)
    before = env.record()
    receipt, step = execute_candidate_training_query(
        runtime, env, learner_color=0, search=search, nodes=32, seconds=1.0,
        seed=17, cancel=stopped)

    assert not receipt.complete and receipt.nodes == 0
    assert receipt.reason == "STOPPED_USER"
    assert not step.moved and env.record() == before
    assert runtime.learner.rows == []


def test_persistent_stop_during_alphabeta_unwinds_search_without_next_query():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime = initialize_candidate_arm(arm)
    env = _TinySearchEnv(actor=0, tree_depth=2, branching=16)
    polls = 0

    def stopped_on_inner_poll():
        nonlocal polls
        polls += 1
        if polls == 4:
            raise PersistentStop("persistent user stop")

    search = lambda search_env, model, **kwargs: AlphaBeta(2, 0).search(
        search_env, model, **kwargs)
    before = env.record()
    episode = run_candidate_training_episode(
        runtime, next(iter_training_episodes(arm, max_episodes=1)), env,
        horizon=8, nodes_per_query=4096, seconds_per_query=1.0,
        remaining_nodes=4096, query_seed_base=17, search=search,
        cancel=stopped_on_inner_poll)

    assert polls == 4
    assert episode.ending == "STOPPED_USER" and episode.nodes == 128
    assert episode.queries == 1 and episode.outcome is None
    assert env.record() == before
    assert env.replayed == 0 and runtime.learner.rows == []
    row = episode.query_rows[0]
    assert row["complete"] is False and row["search_reason"] == "STOPPED_USER"
    assert row["record_before"] == row["record_after"] == episode.start_record


def test_bounded_episode_preserves_horizon_as_unknown_after_real_search():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime, env = initialize_candidate_arm(arm), _TinySearchEnv(actor=0)
    search = lambda search_env, model, **kwargs: AlphaBeta(1, 0).search(
        search_env, model, **kwargs)

    result = run_candidate_training_episode(
        runtime, next(iter_training_episodes(arm, max_episodes=1)), env,
        horizon=1, nodes_per_query=32, seconds_per_query=1.0,
        remaining_nodes=64, query_seed_base=17, search=search, cancel=lambda: None)

    assert result.ending == "HORIZON_UNKNOWN" and result.outcome is None
    assert result.queries == 1 and result.nodes > 0
    assert result.stats["censored"] is True
    row = result.query_rows[0]
    assert row["candidate_index"] == 0 and row["candidate_seed"] == arm.candidate_seed
    assert row["root_family"] == result.root_family
    assert row["root_record_sha256"] == arm.roots[0]["record_sha256"]
    assert row["record_before"] == result.start_record
    assert row["record_after"] == result.final_record
    assert row["complete"] is True and row["value"] is not None
    assert row["requested_nodes"] == 32 and row["search_seed"] == 17


def test_episode_rejects_runtime_mismatch_before_search_or_mutation():
    plan, index, pool = frozen_inputs()
    arms = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)
    runtime = initialize_candidate_arm(arms[0])
    wrong_episode = next(iter_training_episodes(arms[1], max_episodes=1))
    env = _TinySearchEnv(actor=0)
    before = env.record()

    with pytest.raises(ValueError, match="does not belong"):
        run_candidate_training_episode(
            runtime, wrong_episode, env, horizon=128, nodes_per_query=32,
            seconds_per_query=1.0, remaining_nodes=64, query_seed_base=17,
            search=lambda *args, **kwargs: pytest.fail("mismatched arm must not search"),
            cancel=lambda: None)
    assert env.record() == before


def test_episode_rechecks_mutable_root_hash_before_search():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    episode = next(iter_training_episodes(arm, max_episodes=1))
    episode.root["record"]["actions"].pop()
    runtime, env = initialize_candidate_arm(arm), _TinySearchEnv(actor=0)

    with pytest.raises(ValueError, match="hash/fingerprint mismatch"):
        run_candidate_training_episode(
            runtime, episode, env, horizon=8, nodes_per_query=32,
            seconds_per_query=1.0, remaining_nodes=64, query_seed_base=17,
            search=lambda *args, **kwargs: pytest.fail("mutated root must not search"),
            cancel=lambda: None)
    assert env.history == []


def test_episode_closure_stops_before_search_and_keeps_unknown():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime, env = initialize_candidate_arm(arm), _TinySearchEnv(actor=0)
    invoked = []

    def search(*args, **kwargs):
        invoked.append(True)
        raise AssertionError("stopped episode must not query search")

    def stopped():
        raise PersistentStop("persistent user stop")

    result = run_candidate_training_episode(
        runtime, next(iter_training_episodes(arm, max_episodes=1)), env,
        horizon=128, nodes_per_query=32, seconds_per_query=1.0,
        remaining_nodes=64, query_seed_base=17, search=search, cancel=stopped)

    assert result.ending == "STOPPED_USER" and result.outcome is None
    assert result.queries == 0 and invoked == []
    assert result.stats["censored"] is True


def test_episode_node_cap_stays_unknown_without_querying_search():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime, env = initialize_candidate_arm(arm), _TinySearchEnv(actor=0)

    result = run_candidate_training_episode(
        runtime, next(iter_training_episodes(arm, max_episodes=1)), env,
        horizon=128, nodes_per_query=32, seconds_per_query=1.0,
        remaining_nodes=0, query_seed_base=17,
        search=lambda *args, **kwargs: pytest.fail("zero budget must not search"),
        cancel=lambda: None)

    assert result.ending == "NODE_CAP_UNKNOWN" and result.outcome is None
    assert result.queries == 0 and result.stats["censored"] is True


def test_incomplete_resource_receipt_is_logged_without_game_advance():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime, env = initialize_candidate_arm(arm), _TinySearchEnv(actor=0)
    partial = Receipt(None, None, None, False, (), 7, False, 0, 0.01, "resource limit")

    result = run_candidate_training_episode(
        runtime, next(iter_training_episodes(arm, max_episodes=1)), env,
        horizon=128, nodes_per_query=32, seconds_per_query=1.0,
        remaining_nodes=64, query_seed_base=17,
        search=lambda *args, **kwargs: partial, cancel=lambda: None)

    assert result.ending == "SEARCH_RESOURCE_UNKNOWN" and result.outcome is None
    assert result.queries == 1 and result.nodes == 7
    row = result.query_rows[0]
    assert row["complete"] is False and row["search_reason"] == "resource limit"
    assert row["record_before"] == row["record_after"] == result.start_record
    assert result.stats["censored"] is True


def test_non_scoring_terminal_closes_episode_as_unknown():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime, env = initialize_candidate_arm(arm), _TinySearchEnv(actor=0)
    result = SimpleNamespace(
        status=SimpleNamespace(value="NO_CONTEST"), declaration_outcome=None)
    env.terminal = lambda: (_ for _ in ()).throw(NonScoringTerminal(result))

    episode = run_candidate_training_episode(
        runtime, next(iter_training_episodes(arm, max_episodes=1)), env,
        horizon=128, nodes_per_query=32, seconds_per_query=1.0,
        remaining_nodes=64, query_seed_base=17,
        search=lambda *args, **kwargs: pytest.fail("terminal state must not search"),
        cancel=lambda: None)

    assert episode.ending == "NON_SCORING_UNKNOWN" and episode.outcome is None
    assert episode.queries == 0 and episode.stats["censored"] is True


def test_actual_terminal_draw_stays_distinct_from_unknown_closure():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime, env = initialize_candidate_arm(arm), _TinySearchEnv(actor=0)
    env.terminal = lambda: 0

    result = run_candidate_training_episode(
        runtime, next(iter_training_episodes(arm, max_episodes=1)), env,
        horizon=128, nodes_per_query=32, seconds_per_query=1.0,
        remaining_nodes=64, query_seed_base=17,
        search=lambda *args, **kwargs: pytest.fail("terminal state must not search"),
        cancel=lambda: None)

    assert result.ending == "ACTUAL_TERMINAL" and result.outcome == 0
    assert result.stats["censored"] is False


def test_training_journal_fsyncs_episode_prefix_and_marks_missing_final_receipt(tmp_path):
    started, queries = tmp_path / "started.json", tmp_path / "queries.jsonl"
    episodes, result = tmp_path / "episodes.jsonl", tmp_path / "training-result.json"
    with CandidateTrainingJournal(started, queries, episodes, result,
                                  {"status": "STARTED", "plan_sha256": "a" * 64}) as journal:
        journal.append_query({"candidate_index": 0, "complete": False,
                              "reason": "STOPPED_USER"})
        journal.close_episode({"candidate_index": 0, "ending": "STOPPED_USER",
                              "outcome": None})

    query_rows, query_tail = read_newline_jsonl_prefix(queries)
    episode_rows, episode_tail = read_newline_jsonl_prefix(episodes)
    assert len(query_rows) == len(episode_rows) == 1
    assert not query_tail and not episode_tail
    assert recovered_training_status(started, result) == "NO_FINAL_RECEIPT"
    with pytest.raises(FileExistsError):
        CandidateTrainingJournal(started, queries, episodes, result, {"status": "STARTED"})


def test_training_journal_preserves_and_excludes_truncated_jsonl_tail(tmp_path):
    started, queries = tmp_path / "started.json", tmp_path / "queries.jsonl"
    episodes, result = tmp_path / "episodes.jsonl", tmp_path / "training-result.json"
    journal = CandidateTrainingJournal(started, queries, episodes, result,
                                      {"status": "STARTED"})
    journal.append_query({"query": 0, "complete": True})
    journal.close()
    with queries.open("ab") as stream:
        stream.write(b'{"query":1,"complete":')
    before = queries.read_bytes()

    rows, tail = read_newline_jsonl_prefix(queries)

    assert rows == ({"complete": True, "query": 0},)
    assert tail == b'{"query":1,"complete":'
    assert queries.read_bytes() == before
    assert recovered_training_status(started, result) == "NO_FINAL_RECEIPT"


def test_training_journal_final_receipt_is_write_once_and_recoverable(tmp_path):
    started, queries = tmp_path / "started.json", tmp_path / "queries.jsonl"
    episodes, result = tmp_path / "episodes.jsonl", tmp_path / "training-result.json"
    journal = CandidateTrainingJournal(started, queries, episodes, result,
                                      {"status": "STARTED"})
    journal.finish({"status": "STOPPED_USER", "episodes": 1})
    assert recovered_training_status(started, result) == "STOPPED_USER"
    with pytest.raises(RuntimeError, match="cannot be finished twice"):
        journal.finish({"status": "COMPLETE"})
    journal.close()


def test_training_journal_closes_start_handle_if_later_exclusive_open_fails(tmp_path):
    started, queries = tmp_path / "started.json", tmp_path / "queries.jsonl"
    episodes, result = tmp_path / "episodes.jsonl", tmp_path / "training-result.json"
    queries.write_text("preexisting\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        CandidateTrainingJournal(started, queries, episodes, result,
                                 {"status": "STARTED"})

    with started.open("a", encoding="utf-8") as stream:
        stream.write("recovery-marker")
    assert recovered_training_status(started, result) == "NO_FINAL_RECEIPT"


def test_episode_query_and_closure_sinks_integrate_with_journal(tmp_path):
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime, env = initialize_candidate_arm(arm), _TinySearchEnv(actor=0)
    started, queries = tmp_path / "started.json", tmp_path / "queries.jsonl"
    episodes, final = tmp_path / "episodes.jsonl", tmp_path / "training-result.json"
    search = lambda search_env, model, **kwargs: AlphaBeta(1, 0).search(
        search_env, model, **kwargs)

    with CandidateTrainingJournal(started, queries, episodes, final,
                                  {"status": "STARTED"}) as journal:
        result = run_candidate_training_episode(
            runtime, next(iter_training_episodes(arm, max_episodes=1)), env,
            horizon=1, nodes_per_query=32, seconds_per_query=1.0,
            remaining_nodes=64, query_seed_base=17, search=search,
            cancel=lambda: None, query_sink=journal.append_query,
            episode_sink=journal.close_episode)

    query_rows, query_tail = read_newline_jsonl_prefix(queries)
    episode_rows, episode_tail = read_newline_jsonl_prefix(episodes)
    assert len(query_rows) == len(episode_rows) == 1
    assert not query_tail and not episode_tail
    assert episode_rows[0] == result.summary_record()
    assert episode_rows[0]["ending"] == "HORIZON_UNKNOWN"
    assert episode_rows[0]["actual_outcome"] is None
    assert recovered_training_status(started, final) == "NO_FINAL_RECEIPT"


def test_arm_prefix_audit_replays_closed_episodes_and_preserves_open_query_suffix(tmp_path):
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    started, queries = tmp_path / "started.json", tmp_path / "queries.jsonl"
    episodes, final = tmp_path / "episodes.jsonl", tmp_path / "training-result.json"
    started.write_text(json.dumps({
        "status": "STARTED", "candidate_index": arm.candidate_index,
        "candidate_seed": arm.candidate_seed,
        "candidate_ruleset_sha256": arm.candidate_ruleset_sha256,
    }) + "\n", encoding="utf-8")
    runtime = initialize_candidate_arm(arm)
    search = lambda search_env, model, **kwargs: AlphaBeta(1, 0).search(
        search_env, model, **kwargs)
    closed_query_rows = []
    closed_episode_rows = []
    first = next(iter_training_episodes(arm, max_episodes=2))
    run_candidate_training_episode(
        runtime, first, _TinySearchEnv(actor=0), horizon=1,
        nodes_per_query=32, seconds_per_query=1.0, remaining_nodes=64,
        query_seed_base=17, search=search, cancel=lambda: None,
        query_sink=closed_query_rows.append,
        episode_sink=closed_episode_rows.append)
    second = tuple(iter_training_episodes(arm, max_episodes=2))[1]
    partial_query_rows = []
    run_candidate_training_episode(
        runtime, second, _TinySearchEnv(actor=0), horizon=1,
        nodes_per_query=32, seconds_per_query=1.0, remaining_nodes=64,
        query_seed_base=27, search=search, cancel=lambda: None,
        query_sink=partial_query_rows.append)
    queries.write_text("".join(json.dumps(row) + "\n"
                               for row in closed_query_rows + partial_query_rows),
                        encoding="utf-8")
    episodes.write_text("".join(json.dumps(row) + "\n" for row in closed_episode_rows),
                         encoding="utf-8")
    before = (queries.read_bytes(), episodes.read_bytes(), started.read_bytes())

    audited = audit_candidate_training_arm_prefix(
        arm, started_path=started, query_path=queries, episode_path=episodes,
        result_path=final,
        environment_for_episode=lambda _: _TinySearchEnv(actor=0),
        max_episodes=2, decode_action=lambda action: action,
        verify_root_history=False)

    assert {key: audited[key] for key in (
        "status", "closed_episodes", "replayed_episodes", "trailing_query_rows",
        "query_tail_bytes", "episode_tail_bytes", "replayed_nodes",
        "actual_terminals", "unknown_episodes", "final_receipt", "final_tail_bytes",
        "replayed_open_queries", "open_query_nodes", "query_file_present",
        "episode_file_present")} == {
        "status": "NO_FINAL_RECEIPT_OPEN_EPISODE",
        "closed_episodes": 1, "replayed_episodes": 1,
        "trailing_query_rows": 1, "query_tail_bytes": 0,
        "episode_tail_bytes": 0, "replayed_nodes": closed_episode_rows[0]["nodes"],
        "actual_terminals": 0, "unknown_episodes": 1,
        "final_receipt": "MISSING", "final_tail_bytes": 0,
        "replayed_open_queries": 1,
        "open_query_nodes": partial_query_rows[0]["nodes"],
        "query_file_present": True, "episode_file_present": True,
    }
    assert audited["start_sha256"] == hashlib.sha256(before[2]).hexdigest()
    assert audited["query_sha256"] == hashlib.sha256(before[0]).hexdigest()
    assert audited["episode_sha256"] == hashlib.sha256(before[1]).hexdigest()
    assert audited["final_sha256"] is None
    assert (queries.read_bytes(), episodes.read_bytes(), started.read_bytes()) == before
    assert not final.exists()

    forged = copy.deepcopy(closed_query_rows + partial_query_rows)
    forged[-1]["weights_before_search"][0] += 0.25
    queries.write_text("".join(json.dumps(row) + "\n" for row in forged),
                        encoding="utf-8")
    with pytest.raises(ValueError, match="model snapshot does not follow"):
        audit_candidate_training_arm_prefix(
            arm, started_path=started, query_path=queries, episode_path=episodes,
            result_path=final,
            environment_for_episode=lambda _: _TinySearchEnv(actor=0),
            max_episodes=2, decode_action=lambda action: action,
            verify_root_history=False)
    queries.write_bytes(before[0])

    queries.write_text('{"candidate_index":0,"candidate_index":0}\n',
                        encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate object keys"):
        audit_candidate_training_arm_prefix(
            arm, started_path=started, query_path=queries, episode_path=episodes,
            result_path=final,
            environment_for_episode=lambda _: _TinySearchEnv(actor=0),
            max_episodes=2, decode_action=lambda action: action,
            verify_root_history=False)
    queries.write_bytes(before[0])


def test_arm_prefix_audit_distinguishes_torn_final_receipt_from_missing(tmp_path):
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    started, queries = tmp_path / "started.json", tmp_path / "queries.jsonl"
    episodes, final = tmp_path / "episodes.jsonl", tmp_path / "training-result.json"
    started.write_text(json.dumps({
        "status": "STARTED", "candidate_index": arm.candidate_index,
        "candidate_seed": arm.candidate_seed,
        "candidate_ruleset_sha256": arm.candidate_ruleset_sha256,
    }) + "\n", encoding="utf-8")
    queries.write_bytes(b"")
    episodes.write_bytes(b"")
    final.write_bytes(b'{"status":"STOPPED_USER"')
    before = final.read_bytes()

    audited = audit_candidate_training_arm_prefix(
        arm, started_path=started, query_path=queries, episode_path=episodes,
        result_path=final,
        environment_for_episode=lambda _: pytest.fail("no episode to replay"),
        max_episodes=2)

    assert audited["status"] == "NO_FINAL_RECEIPT"
    assert audited["final_receipt"] == "TORN_OR_INVALID"
    assert audited["final_tail_bytes"] > 0
    assert audited["final_sha256"] == hashlib.sha256(before).hexdigest()
    assert final.read_bytes() == before


def test_arm_prefix_audit_reports_started_without_any_journal_files(tmp_path):
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    started = tmp_path / "started.json"
    queries, episodes = tmp_path / "queries.jsonl", tmp_path / "episodes.jsonl"
    final = tmp_path / "training-result.json"
    started.write_text(json.dumps({
        "status": "STARTED", "candidate_index": arm.candidate_index,
        "candidate_seed": arm.candidate_seed,
        "candidate_ruleset_sha256": arm.candidate_ruleset_sha256,
    }) + "\n", encoding="utf-8")

    audited = audit_candidate_training_arm_prefix(
        arm, started_path=started, query_path=queries, episode_path=episodes,
        result_path=final,
        environment_for_episode=lambda _: pytest.fail("no episode to replay"),
        max_episodes=2)

    assert audited["status"] == "NO_FINAL_RECEIPT"
    assert audited["closed_episodes"] == audited["trailing_query_rows"] == 0
    assert audited["final_receipt"] == "MISSING"
    assert not audited["query_file_present"] and not audited["episode_file_present"]
    assert not queries.exists() and not episodes.exists() and not final.exists()


def test_arm_prefix_audit_accepts_bound_zero_episode_stop_receipt(tmp_path):
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    started, queries = tmp_path / "started.json", tmp_path / "queries.jsonl"
    episodes, final = tmp_path / "episodes.jsonl", tmp_path / "training-result.json"
    with CandidateTrainingJournal(started, queries, episodes, final, {
            "status": "STARTED", "candidate_index": arm.candidate_index,
            "candidate_seed": arm.candidate_seed,
            "candidate_ruleset_sha256": arm.candidate_ruleset_sha256}) as journal:
        journal.finish({
            "status": "STOPPED_USER", "candidate_index": arm.candidate_index,
            "candidate_seed": arm.candidate_seed,
            "candidate_ruleset_sha256": arm.candidate_ruleset_sha256,
            "episodes": 0, "actual_terminals": 0, "unknown_episodes": 0,
            "combined_candidate_and_foe_nodes": 0,
            "final_weights": list(arm.initial_weights),
        })

    audited = audit_candidate_training_arm_prefix(
        arm, started_path=started, query_path=queries, episode_path=episodes,
        result_path=final,
        environment_for_episode=lambda _: pytest.fail("stop receipt has no episode"),
        max_episodes=2)
    assert audited["status"] == audited["final_receipt"] == "STOPPED_USER"
    assert audited["closed_episodes"] == audited["trailing_query_rows"] == 0

    forged = json.loads(final.read_text(encoding="utf-8"))
    forged["candidate_index"] = False  # bool compares equal to candidate index 0 in Python.
    final.write_text(json.dumps(forged) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="final receipt does not match"):
        audit_candidate_training_arm_prefix(
            arm, started_path=started, query_path=queries, episode_path=episodes,
            result_path=final,
            environment_for_episode=lambda _: pytest.fail("stop receipt has no episode"),
            max_episodes=2)


def test_closed_training_episode_replay_reconstructs_td_updates_from_receipts():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    episode = next(iter_training_episodes(arm, max_episodes=1))
    trained_runtime = initialize_candidate_arm(arm)
    trained_env = _TinySearchEnv(actor=0, tree_depth=4, branching=8)
    search = lambda search_env, model, **kwargs: AlphaBeta(1, 0).search(
        search_env, model, **kwargs)

    result = run_candidate_training_episode(
        trained_runtime, episode, trained_env, horizon=3,
        nodes_per_query=32, seconds_per_query=1.0, remaining_nodes=96,
        query_seed_base=17, search=search, cancel=lambda: None)

    assert result.queries == 3 and result.outcome is None
    replay_runtime = initialize_candidate_arm(arm)
    replay_env = _TinySearchEnv(actor=0, tree_depth=4, branching=8)
    with pytest.raises(ValueError, match="not at its bound frozen root"):
        replay_closed_training_episode(
            initialize_candidate_arm(arm), episode, result.summary_record(),
            result.query_rows, replay_env, decode_action=lambda action: action)
    forged_rows = copy.deepcopy(result.query_rows)
    forged_rows[0]["record_after"].clear()
    with pytest.raises(ValueError, match="complete query did not append exactly one action"):
        replay_closed_training_episode(
            initialize_candidate_arm(arm), episode, result.summary_record(),
            forged_rows, _TinySearchEnv(actor=0, tree_depth=4, branching=8),
            decode_action=lambda action: action, verify_root_history=False)
    forged_weights = copy.deepcopy(result.query_rows)
    forged_weights[0]["weights_before_search"][1] += 0.25
    with pytest.raises(ValueError, match="model snapshot does not follow"):
        replay_closed_training_episode(
            initialize_candidate_arm(arm), episode, result.summary_record(),
            forged_weights, _TinySearchEnv(actor=0, tree_depth=4, branching=8),
            decode_action=lambda action: action, verify_root_history=False)
    forged_draw = result.summary_record()
    forged_draw["actual_outcome"] = 0
    with pytest.raises(ValueError, match="UNKNOWN episode carries a terminal reward"):
        replay_closed_training_episode(
            initialize_candidate_arm(arm), episode, forged_draw,
            result.query_rows, _TinySearchEnv(actor=0, tree_depth=4, branching=8),
            decode_action=lambda action: action, verify_root_history=False)
    replayed = replay_closed_training_episode(
        replay_runtime, episode, result.summary_record(), result.query_rows,
        replay_env, decode_action=lambda action: action,
        verify_root_history=False)

    assert replayed["ending"] == result.ending == "HORIZON_UNKNOWN"
    assert replayed["actual_outcome"] is None
    assert replayed["nodes"] == result.nodes
    assert replayed["final_weights"] == result.final_weights
    assert replayed["stats"] == result.stats
    assert replay_env.record() == result.final_record


def test_zero_query_stopped_episode_replays_as_unknown_without_search():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    episode = next(iter_training_episodes(arm, max_episodes=1))
    runtime = initialize_candidate_arm(arm)
    env = _TinySearchEnv(actor=0)

    def stopped():
        raise PersistentStop("persistent user stop")

    result = run_candidate_training_episode(
        runtime, episode, env, horizon=8, nodes_per_query=32,
        seconds_per_query=1.0, remaining_nodes=64, query_seed_base=17,
        search=lambda *args, **kwargs: pytest.fail("stop must precede search"),
        cancel=stopped)
    replayed = replay_closed_training_episode(
        initialize_candidate_arm(arm), episode, result.summary_record(), (),
        _TinySearchEnv(actor=0), decode_action=lambda action: action,
        verify_root_history=False)

    assert result.ending == replayed["ending"] == "STOPPED_USER"
    assert result.outcome is replayed["actual_outcome"] is None
    assert result.queries == replayed["queries"] == 0
    assert replayed["final_weights"] == result.final_weights


def test_persistent_stop_closes_real_alphabeta_episode_as_durable_unknown(tmp_path):
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime = initialize_candidate_arm(arm)
    env = _TinySearchEnv(actor=0, tree_depth=2, branching=16)
    started, queries = tmp_path / "started.json", tmp_path / "queries.jsonl"
    episodes, final = tmp_path / "episodes.jsonl", tmp_path / "training-result.json"
    polls = 0
    search = lambda search_env, model, **kwargs: AlphaBeta(2, 0).search(
        search_env, model, **kwargs)

    def stop_on_inner_poll():
        nonlocal polls
        polls += 1
        if polls == 5:
            raise PersistentStop("persistent user stop")

    constructed_episodes = []
    training_episodes = []

    def make_environment(episode):
        constructed_episodes.append(episode.episode_index)
        training_episodes.append(episode)
        return env

    with CandidateTrainingJournal(started, queries, episodes, final,
                                  {"status": "STARTED"}) as journal:
        arm_result = run_candidate_training_arm(
            runtime, environment_for_episode=make_environment,
            horizon=8, nodes_per_query=4096, seconds_per_query=1.0,
            node_cap=4096, max_episodes=3, query_seed_base=17, search=search,
            cancel=stop_on_inner_poll, query_sink=journal.append_query,
            episode_sink=journal.close_episode)
        journal.finish({"status": arm_result.ending,
                        "episodes": arm_result.episodes,
                        "unknown_episodes": arm_result.unknown_episodes})

    query_rows, query_tail = read_newline_jsonl_prefix(queries)
    episode_rows, episode_tail = read_newline_jsonl_prefix(episodes)
    assert polls == 5 and arm_result.ending == "STOPPED_USER"
    assert constructed_episodes == [0]
    assert arm_result.episodes == arm_result.unknown_episodes == 1
    assert arm_result.actual_terminals == 0 and arm_result.combined_nodes == 128
    assert env.record() == episode_rows[0]["start_record"] and env.replayed == 0
    assert runtime.learner.rows == []
    assert not query_tail and not episode_tail
    assert len(query_rows) == len(episode_rows) == 1
    assert query_rows[0]["complete"] is False
    assert query_rows[0]["search_reason"] == "STOPPED_USER"
    assert episode_rows[0]["ending"] == arm_result.ending
    assert episode_rows[0]["nodes"] == arm_result.combined_nodes
    assert episode_rows[0]["actual_outcome"] is None
    assert episode_rows[0]["ending"] == "STOPPED_USER"
    assert recovered_training_status(started, final) == "STOPPED_USER"
    replayed = replay_closed_training_episode(
        initialize_candidate_arm(arm), training_episodes[0], episode_rows[0],
        query_rows, _TinySearchEnv(actor=0, tree_depth=2, branching=16),
        decode_action=lambda action: action, verify_root_history=False)
    assert replayed["ending"] == "STOPPED_USER"
    assert replayed["actual_outcome"] is None and replayed["nodes"] == 128


def test_candidate_training_arm_closes_at_combined_candidate_foe_node_cap():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime = initialize_candidate_arm(arm)
    env = _TinySearchEnv(actor=0, tree_depth=2, branching=16)
    made = []

    def make_environment(episode):
        made.append(episode.episode_index)
        return env

    result = run_candidate_training_arm(
        runtime, environment_for_episode=make_environment,
        horizon=8, nodes_per_query=32, seconds_per_query=1.0,
        node_cap=1, max_episodes=3, query_seed_base=17,
        search=lambda search_env, model, **kwargs: AlphaBeta(2, 0).search(
            search_env, model, **kwargs), cancel=lambda: None)

    assert made == [0]
    assert result.ending == "NODE_CAP"
    assert result.episodes == result.unknown_episodes == 1
    assert result.actual_terminals == 0 and result.combined_nodes == 1


def test_candidate_training_arm_stop_before_episode_constructs_no_environment():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime = initialize_candidate_arm(arm)

    def stopped():
        raise PersistentStop("persistent user stop")

    result = run_candidate_training_arm(
        runtime, environment_for_episode=lambda _: pytest.fail(
            "a stop before the episode must not construct its environment"),
        horizon=8, nodes_per_query=32, seconds_per_query=1.0,
        node_cap=100, max_episodes=3, query_seed_base=17,
        search=lambda *args, **kwargs: pytest.fail("must not search"),
        cancel=stopped)

    assert result.ending == "STOPPED_USER"
    assert result.episodes == result.actual_terminals == result.unknown_episodes == 0
    assert result.combined_nodes == 0


def test_torn_final_receipt_is_reported_as_missing_not_repaired(tmp_path):
    started, result = tmp_path / "started.json", tmp_path / "training-result.json"
    started.write_text('{"status":"STARTED"}\n', encoding="utf-8")
    result.write_bytes(b'{"status":"COMPLETE"')
    before = result.read_bytes()

    assert recovered_training_status(started, result) == "NO_FINAL_RECEIPT"
    assert result.read_bytes() == before


def test_actual_alphabeta_complete_query_is_nonmutating_until_receipt_apply():
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]
    runtime, env = initialize_candidate_arm(arm), _TinySearchEnv(actor=0)
    search = lambda search_env, model, **kwargs: AlphaBeta(1, 0).search(
        search_env, model, **kwargs)
    before = env.record()

    receipt, step = execute_candidate_training_query(
        runtime, env, learner_color=0, search=search, nodes=32, seconds=1.0,
        seed=17, cancel=lambda: None)

    assert receipt.complete and receipt.nodes > 0
    assert step.moved and env.record() != before
    assert env.history == [receipt.action]
    assert len(runtime.learner.rows) == 1


def test_candidate_episode_schedule_cycles_roots_and_alternates_learner_color():
    plan, index, pool = frozen_inputs()
    arms = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)
    episodes = list(iter_training_episodes(arms[3], max_episodes=123))

    assert [row.candidate_index for row in episodes] == [3] * 123
    assert [row.candidate_seed for row in episodes] == [index["rows"][3]["seed"]] * 123
    assert [row.episode_index for row in episodes] == list(range(123))
    assert [row.root for row in episodes[:120]] == list(arms[3].roots)
    assert episodes[120].root == arms[3].roots[0]
    assert [row.learner_color for row in episodes[:4]] == [0, 1, 0, 1]


def test_candidate_training_root_replays_only_against_its_pinned_rule():
    plan, index, pool = frozen_inputs()
    arms = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)
    episode = next(iter_training_episodes(arms[0], max_episodes=1))

    def compile_candidate(candidate_index):
        candidate_path = Path(index["rows"][candidate_index]["source_file"])
        return compile_ruleset_for_execution(
            ruleset_from_dict(json.loads(candidate_path.read_text(encoding="utf-8"))))

    env = replay_training_root(episode, compile_candidate(0))
    assert env.record() == episode.root["record"]
    with pytest.raises(ValueError, match="exact complete-history replay"):
        replay_training_root(episode, compile_candidate(1))


@pytest.mark.parametrize("max_episodes", [0, -1, True, 1.5])
def test_candidate_episode_schedule_rejects_invalid_episode_limit(max_episodes):
    plan, index, pool = frozen_inputs()
    arm = build_candidate_arm_inputs(
        plan, index, pool, initial_vector=initial_vector)[0]

    with pytest.raises(ValueError, match="episode count"):
        list(iter_training_episodes(arm, max_episodes=max_episodes))
