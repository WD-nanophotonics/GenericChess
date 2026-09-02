"""Synthetic-only tests for the H49B-R1 executable runner freeze."""

from __future__ import annotations

import copy
import json
import statistics
from dataclasses import fields
from types import SimpleNamespace

import pytest

from scripts import audit_f49_learning_signal_architecture as runner


def _cell(rate=0.0):
    return {"status": "VALID", "failed_searches": 0, "mean_flip_rate": rate}


def _teacher(stable=True):
    return {"status": "VALID", "failed_searches": 0, "exact_best_move_agreement": 0.9 if stable else 0.4}


def _observations(teacher_stable=True, control_l0=0.0, control_l1=0.0, structural=0.0, nonmaterial=None):
    def corpus(l0, l1):
        return {"teacher_40_80": _teacher(teacher_stable), "L49_0_2000": _cell(l0), "L49_1_2000": _cell(l1), "non_material_control": {"status": "VALID" if nonmaterial is not None else "UNMEASURABLE_IN_SELECTED_SEARCH_PATH", "non_material_signal": nonmaterial}}

    rows = {name: {"F48_CONTROL": corpus(control_l0, control_l1), "S49-M": corpus(0.0, structural), "S49-E": corpus(0.0, structural)} for name in ("a", "b", "c")}
    # Keep one positive control witness only so the frozen precedence leaves
    # the final synthetic case on MIXED_OR_UNRESOLVED.
    if nonmaterial is None and control_l1:
        rows["b"]["F48_CONTROL"] = corpus(control_l0, 0.0)
        rows["c"]["F48_CONTROL"] = corpus(control_l0, 0.0)
    return rows


def test_h49b_r1_manifest_requires_real_measurement_entry_point_but_no_observation():
    manifest = runner.load_h49b_r1_manifest()
    assert manifest["kind"] == "H49B-R1_F49_DIAGNOSTIC_RUNNER_FREEZE"
    assert manifest["parent_h49b_sha"] == runner.H49B_SHA
    assert manifest["measurement_entry_point"].endswith("run_measurements")
    assert manifest["preflight_entry_point"].endswith("run_preflight")
    assert manifest["observed_results_present"] is False
    assert manifest["measurements_invoked"] is False
    assert manifest["learning_invoked"] is False
    assert manifest["F50_status"] == "NOT_STARTED"
    assert set(manifest["measurement_families"]) == set(runner.MEASUREMENT_FAMILIES)
    assert set(manifest["concrete_partition_routes"]) == runner.PARTITION_ROUTES


def test_h49b_r1_partition_identity_is_concrete_and_atomic(tmp_path):
    exact_fingerprint = runner.f49_protocol.RULESET_FINGERPRINTS["A_CANONICAL_WESTERN_CHESS"]
    partition = runner.partition_identity(corpus_id="synthetic-corpus", checkpoint_or_config_hash="synthetic-config", search_route="AUDIT_SELECTOR", node_budget=None, measurement_family="SELECTOR", ruleset_fingerprint=exact_fingerprint)
    assert partition["input_identity"]["ruleset_fingerprint"] == exact_fingerprint
    assert "PLANNED_ONLY_NO_EXECUTION" not in str(partition)
    store = runner.AtomicPartitionStore(tmp_path)
    store.write(partition, {"synthetic": True})
    assert store.load(partition) == {"synthetic": True}
    stale = copy.deepcopy(partition)
    stale["input_identity"]["corpus_id"] = "other-corpus"
    with pytest.raises(RuntimeError, match="stale or mismatched"):
        store.load(stale)
    with pytest.raises(ValueError, match="concrete"):
        runner.partition_identity(corpus_id="<pending>", checkpoint_or_config_hash="x", search_route="AUDIT_SELECTOR", node_budget=None, measurement_family="SELECTOR", ruleset_fingerprint="synthetic-ruleset")


def test_structural_ledger_is_derived_without_selection_feedback():
    corpus = {"status": "VALID", "records": [
        {"position_identity_key": "a", "target_ply": 8, "legal_action_count": 2, "event_flags": {"remove_or_capture_effect": True, "type_or_promotion_transformation": False, "hand_or_inventory_count_change": True}},
        {"position_identity_key": "a", "target_ply": 9, "legal_action_count": 4, "event_flags": {"remove_or_capture_effect": False, "type_or_promotion_transformation": False, "hand_or_inventory_count_change": False}},
        {"position_identity_key": "b", "target_ply": 9, "legal_action_count": 6, "event_flags": {"remove_or_capture_effect": False, "type_or_promotion_transformation": True, "hand_or_inventory_count_change": False}},
    ]}
    ledger = runner.structural_ledger(corpus)
    assert ledger["total_positions"] == 3
    assert ledger["unique_identities"] == 2
    assert ledger["multiplicity_histogram"] == {"1": 1, "2": 1}
    assert ledger["effective_unique_fraction"] == pytest.approx(2 / 3)
    assert ledger["legal_action_count"] == {"min": 2, "median": 4.0, "mean": 4.0, "p90": 6.0, "max": 6}
    assert ledger["any_inventory_changing_history_event_frequency"] == pytest.approx(2 / 3)


@pytest.mark.parametrize("kwargs,expected", [
    ({"control_l0": 0.0, "control_l1": 0.1, "structural": 0.0, "nonmaterial": False}, "LEARNER_ALIGNED_SIGNAL_SUPPORTED"),
    ({"control_l0": 0.0, "control_l1": 0.0, "structural": 0.1, "nonmaterial": False}, "STRUCTURAL_CORPUS_ARCHITECTURE_LIMITING"),
    ({"teacher_stable": False}, "NATIVE_SEARCH_TEACHER_STABILITY_LIMITING"),
    ({"control_l0": 0.0, "control_l1": 0.0, "structural": 0.0, "nonmaterial": True}, "MATERIAL_ONLY_REPRESENTATION_LIMITING"),
    ({"control_l0": 0.0, "control_l1": 0.0, "structural": 0.0, "nonmaterial": False}, "EVALUATION_SIGNAL_BROADLY_WEAK"),
    ({"control_l0": 0.0, "control_l1": 0.1, "structural": 0.0, "nonmaterial": None}, "MIXED_OR_UNRESOLVED"),
])
def test_independent_selector_reaches_all_six_terminal_paths(kwargs, expected):
    observations = _observations(**kwargs)
    assert runner._independent_selector(observations)[0] == expected
    assert runner._independent_selector(observations) == runner.f49_protocol.select_f49_classification(observations)


def test_preflight_does_not_invoke_measurement_primitives(monkeypatch):
    class Forbidden:
        def __init__(self, *args, **kwargs):
            raise AssertionError("measurement primitive invoked during preflight")

    monkeypatch.setattr(runner, "NativeSearchEngine", Forbidden)
    monkeypatch.setattr(runner, "AlphaBetaPlayer", Forbidden)
    monkeypatch.setattr(runner, "run_measurements", lambda **kwargs: (_ for _ in ()).throw(AssertionError("measurement boundary invoked")), raising=False)
    manifest = runner.run_preflight()
    assert manifest["observed_results_present"] is False
    assert manifest["measurements_invoked"] is False


def test_measurement_boundary_is_explicit_in_source():
    source = runner.SOURCE_PATH.read_text(encoding="utf-8")
    assert "def run_preflight(" in source
    assert "def run_measurements(" in source
    assert "--measure" in source
    assert "def partition_identity(" in source


class _FakeAction:
    def __init__(self, name):
        self.name = name

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, _FakeAction) and self.name == other.name


class _FakeSession:
    def __init__(self, compiled):
        self.compiled = compiled
        self._history = []
        self.state = SimpleNamespace(position=SimpleNamespace(marker=0))
        self.result = SimpleNamespace(status=SimpleNamespace(value="ongoing"))

    def submit(self, action):
        self._history.append(action)
        self.state.position = SimpleNamespace(marker=len(self._history))

    def legal_actions(self):
        return [_FakeAction("a"), _FakeAction("b")]


def _checkpoint():
    return runner.LearnableMaterialCheckpoint(
        ruleset_fingerprint="synthetic-ruleset",
        board_weights={"P": 2.0, "Q": 4.0},
        hand_weights={"P": 1.0, "Q": 2.0},
        reference_median=3.0,
        value_scale=12.0,
        w_max=100.0,
    )


def test_structural_generation_is_deterministic_and_event_stratum_fails_closed(monkeypatch):
    compiled = SimpleNamespace(ruleset_fingerprint="synthetic-ruleset")
    openings = SimpleNamespace(openings=[SimpleNamespace(actions=[])])
    monkeypatch.setattr(runner, "generate_arena_openings", lambda *args, **kwargs: openings)
    monkeypatch.setattr(runner, "GameSession", _FakeSession)
    monkeypatch.setattr(runner, "action_to_dict", lambda action: {"name": action.name})
    monkeypatch.setattr(runner.f49_protocol, "canonical_action_order_key", lambda action: action.name)
    monkeypatch.setattr(runner, "position_identity_key", lambda position, compiled: f"position-{position.marker}")
    monkeypatch.setattr(runner, "_event_between", lambda before, after: {"remove_or_capture_effect": False, "type_or_promotion_transformation": False, "hand_or_inventory_count_change": False})
    first = runner.generate_structural_corpus(compiled, stratum_id="S49-M", seed=17, target_plies=(1, 1), minimum_legal_actions=1, count=1, attempt_cap=3)
    second = runner.generate_structural_corpus(compiled, stratum_id="S49-M", seed=17, target_plies=(1, 1), minimum_legal_actions=1, count=1, attempt_cap=3)
    assert first == second
    assert first["records"][0]["candidate_rng_seed"] == runner.f49_protocol.derive_stratum_candidate_seed("S49-M", 17, 0, first["records"][0]["selected_attempt"])
    assert first["records"][0]["action_history"] == [{"name": first["records"][0]["action_history"][0]["name"]}]
    unavailable = runner.generate_structural_corpus(compiled, stratum_id="S49-E", seed=17, target_plies=(1, 1), minimum_legal_actions=1, count=1, attempt_cap=2)
    assert unavailable["status"] == "STRUCTURAL_STRATUM_UNAVAILABLE"
    monkeypatch.setattr(runner, "_event_between", lambda before, after: {"remove_or_capture_effect": False, "type_or_promotion_transformation": True, "hand_or_inventory_count_change": False})
    eventful = runner.generate_structural_corpus(compiled, stratum_id="S49-E", seed=17, target_plies=(1, 1), minimum_legal_actions=1, count=1, attempt_cap=3)
    assert eventful["status"] == "VALID"
    assert eventful["records"][0]["event_flags"]["type_or_promotion_transformation"] is True


def test_p48_reconstruction_rejects_exact_checkpoint_or_config_drift(monkeypatch, tmp_path):
    path = tmp_path / "results.json"
    path.write_text(json.dumps({"rulesets": [{"ruleset_id": "A_CANONICAL_WESTERN_CHESS", "priors": {"P48-0": {}}}]}), encoding="utf-8")
    monkeypatch.setattr(runner, "F48_RESULTS_PATH", path)
    wrong = SimpleNamespace(checkpoint_id="wrong-checkpoint", config_hash="wrong-config", validate_ruleset=lambda compiled: None)
    monkeypatch.setattr(runner.LearnableMaterialCheckpoint, "from_dict", classmethod(lambda cls, payload: wrong))
    with pytest.raises(RuntimeError, match="P48-0 checkpoint drift"):
        runner.reconstruct_p48_0("A_CANONICAL_WESTERN_CHESS", SimpleNamespace())


def test_native_matrix_uses_exact_cache_keys_fresh_engines_and_failure_reasons(monkeypatch):
    class FakeEngine:
        instances = []
        results = []

        def __init__(self, *args, **kwargs):
            assert kwargs["tt_megabytes"] == 8
            self.instance_id = len(self.instances)
            self.instances.append(self)

        def search(self, session, limits):
            assert limits.max_depth == 12
            assert limits.quiescence_max_depth == 0
            assert limits.quiescence_max_nodes == 0
            return self.results.pop(0)

    def result(reason, action):
        return SimpleNamespace(action=action, score=7, nodes=3, qnodes=1, elapsed_seconds=0.01, completed_depth=2, termination_reason=reason)

    FakeEngine.results = [result("completed", _FakeAction("a"))] * 4
    compiled = SimpleNamespace(ruleset_fingerprint="synthetic-ruleset")
    checkpoint = SimpleNamespace(checkpoint_id="synthetic-checkpoint")
    corpus = {"corpus_id": "synthetic-corpus", "records": [{"output_index": 0, "position_identity_key": "p1", "action_history": []}, {"output_index": 1, "position_identity_key": "p2", "action_history": []}]}
    metrics = runner._measurement_metrics()
    cache = {}
    contexts = {}
    monkeypatch.setattr(runner, "NativeSearchEngine", FakeEngine)
    monkeypatch.setattr(runner, "_replay", lambda *args: SimpleNamespace(result=SimpleNamespace(status=SimpleNamespace(value="ongoing"))))
    monkeypatch.setattr(runner, "compile_native_rules", lambda compiled: "rules")
    monkeypatch.setattr(runner, "compile_native_evaluation", lambda *args, **kwargs: "evaluation")
    monkeypatch.setattr(runner, "_native_profile", lambda *args: "profile")
    monkeypatch.setattr(runner.f49_protocol, "canonical_action_order_key", lambda action: action.name)
    runner._native_search_matrix(compiled, checkpoint, corpus, [500, 2000], "NATIVE_SEARCH_ENGINE_MATERIAL", "L49-0", metrics, cache, contexts)
    runner._native_search_matrix(compiled, checkpoint, corpus, [500, 2000], "NATIVE_SEARCH_ENGINE_MATERIAL", "L49-0", metrics, cache, contexts)
    assert metrics["native_current_process"]["ruleset_compile_count"] == 1
    assert metrics["native_current_process"]["evaluation_table_compile_count"] == 1
    assert metrics["native_current_process"]["search_count"] == 4
    assert len(FakeEngine.instances) == 4
    FakeEngine.results = [result("fallback", _FakeAction("a")), result("node_limit", None), result("depth_limit", _FakeAction("a"))]
    failures = [runner._native_search_once(compiled, "rules", "evaluation", corpus["records"][0], 500, metrics) for _ in range(3)]
    assert [row["failed_search"] for row in failures] == [True, True, False]
    assert failures[-1]["action_key"] == "a"
    assert failures[-1]["score"] == 7
    assert failures[-1]["nodes"] == 3
    assert failures[-1]["qnodes"] == 1


def test_l49_surfaces_update_board_and_hand_and_deduplicate_aliases(monkeypatch):
    compiled = SimpleNamespace(ruleset_fingerprint="synthetic-ruleset")
    monkeypatch.setattr(runner, "non_anchor_type_ids", lambda compiled: ("P", "Q"))
    start = _checkpoint()
    for surface, factors in (("L49-0", (0.75, 1.25)), ("L49-2", (0.50, 1.50))):
        candidates = runner._l49_checkpoints(compiled, start, surface)
        assert len(candidates) == 4
        for name, candidate in candidates:
            type_id, factor_text = name.split(":")
            factor = float(factor_text)
            assert candidate.board_weights[type_id] == pytest.approx(start.board_weights[type_id] * factor)
            assert candidate.hand_weights[type_id] == pytest.approx(start.hand_weights[type_id] * factor)
    directions = runner._l49_checkpoints(compiled, start, "L49-1")
    assert directions
    for _, candidate in directions:
        assert all(value > 0 for value in candidate.board_weights.values())
        assert all(value > 0 for value in candidate.hand_weights.values())
        assert statistics.median(candidate.board_weights.values()) == pytest.approx(start.reference_median)
    monkeypatch.setattr(runner, "_native_search_matrix", lambda compiled, checkpoint, corpus, budgets, route, family, metrics, cache, context_cache: {str(budget): [] for budget in budgets})
    monkeypatch.setattr(runner, "_l49_checkpoints", lambda compiled, start, surface: [("first", start), ("alias", start)])
    surface = runner.native_material_surface(compiled, {"corpus_id": "synthetic", "records": []}, start, "L49-2", metrics=runner._measurement_metrics(), cache={}, context_cache={})
    assert surface["candidate_count"] == 2
    assert surface["deduplicated_checkpoint_count"] == 1
    assert surface["aliases"][start.checkpoint_id] == ["alias"]


def test_teacher_surface_derives_all_adjacent_pairs(monkeypatch):
    def fake_matrix(compiled, checkpoint, corpus, budgets, route, family, metrics, cache, context_cache):
        actions = {10000: ["a", "b"], 20000: ["a", "c"], 40000: ["a", "c"], 80000: ["a", "c"]}
        return {str(budget): [{"action_key": action, "score": 1, "failed_search": 0} for action in actions[budget]] for budget in budgets}

    monkeypatch.setattr(runner, "_native_search_matrix", fake_matrix)
    teacher = runner.teacher_surface(SimpleNamespace(ruleset_fingerprint="synthetic"), {"records": [{}, {}]}, _checkpoint(), metrics=runner._measurement_metrics(), cache={}, context_cache={})
    assert list(teacher["adjacent"]) == ["10000_20000", "20000_40000", "40000_80000"]
    assert teacher["adjacent"]["40000_80000"]["exact_best_move_agreement"] == 1.0
    assert teacher["teacher_40_80"]["stable"] is True
    assert teacher["teacher_convergence"]["agreement_10_20"] == 0.5
    assert teacher["teacher_convergence"]["agreement_20_40"] == 1.0
    assert teacher["teacher_convergence"]["agreement_vector"] == [0.5, 1.0, 1.0]
    assert teacher["teacher_convergence"]["adjacent_deltas"] == [0.5, 0.0]


def test_python_nonmaterial_control_gates_and_fails_closed(monkeypatch):
    corpus = {"corpus_id": "synthetic-corpus", "records": [{"output_index": 0, "position_identity_key": "p0", "action_history": []}]}
    not_run = runner.python_nonmaterial_control(SimpleNamespace(), corpus, teacher_stable=False)
    assert not_run == {"status": "NOT_RUN_NO_STABLE_TEACHER", "non_material_signal": None, "families": []}
    valid = {"action_key": "a", "score": 1, "nodes": 1, "qnodes": 0, "termination_reason": "node_limit", "valid": True, "exception": None}
    monkeypatch.setattr(runner, "_python_decision", lambda *args, **kwargs: dict(valid))
    measured = runner.python_nonmaterial_control(SimpleNamespace(ruleset_fingerprint="synthetic"), corpus, teacher_stable=True)
    assert measured["status"] == "VALID"
    assert len(measured["families"]) == 3
    assert all(len(family["factors"]) == 2 for family in measured["families"])
    monkeypatch.setattr(runner, "_python_decision", lambda *args, **kwargs: {**valid, "valid": False, "action_key": None, "exception": "synthetic failure"})
    failed = runner.python_nonmaterial_control(SimpleNamespace(ruleset_fingerprint="synthetic"), corpus, teacher_stable=True)
    assert failed["status"] == "CELL_INVALID_SEARCH_FAILURE"
    assert failed["non_material_signal"] is None


def test_run_measurements_order_efficiency_and_selector_evidence(monkeypatch, tmp_path):
    events = []
    compiled = SimpleNamespace(ruleset_fingerprint="synthetic-ruleset")
    entry = {"semantic_execution": compiled, "legacy_transport": compiled}
    checkpoint = _checkpoint()
    monkeypatch.setattr(runner, "validate_r3_measurement_freeze", lambda: events.append("freeze"))
    monkeypatch.setattr(runner, "run_preflight", lambda: events.append("preflight") or {"observed_results_present": False})
    monkeypatch.setattr(runner.f49_protocol, "build_h49r3a_primary_execution", lambda: events.append("execution") or {"synthetic": entry})
    monkeypatch.setattr(runner, "generate_arena_openings", lambda *args, **kwargs: events.append("openings") or SimpleNamespace())
    monkeypatch.setattr(runner, "generate_diagnostic_corpus", lambda *args, **kwargs: events.append("F48_CONTROL") or SimpleNamespace(corpus_id="control", positions=[]))

    def structural(*args, **kwargs):
        events.append(kwargs["stratum_id"])
        return {"status": "VALID", "corpus_id": kwargs["stratum_id"], "records": [], "stratum_id": kwargs["stratum_id"]}

    monkeypatch.setattr(runner, "generate_structural_corpus", structural)
    monkeypatch.setattr(runner, "reconstruct_p48_0", lambda *args: events.append("P48-0") or checkpoint)
    monkeypatch.setattr(runner, "_write_partition", lambda *args, **kwargs: events.append("partition"))
    monkeypatch.setattr(runner, "structural_ledger", lambda corpus: {"total_positions": len(corpus.get("records", []))})

    def teacher(*args, **kwargs):
        events.append("TEACHER")
        kwargs["metrics"]["native_current_process"]["search_count"] += 1
        kwargs["metrics"]["native_current_process"]["requested_nodes"] += 80000
        return {"results": {}, "adjacent": {}, "teacher_40_80": {"status": "VALID", "failed_searches": 0, "exact_best_move_agreement": 0.9, "stable": True}}

    monkeypatch.setattr(runner, "teacher_surface", teacher)

    def material(*args, **kwargs):
        events.append(args[3])
        kwargs["metrics"]["native_current_process"]["search_count"] += 1
        kwargs["metrics"]["native_current_process"]["requested_nodes"] += 2000
        return {"surface": args[3], "cells": {}}

    monkeypatch.setattr(runner, "native_material_surface", material)
    monkeypatch.setattr(runner, "python_nonmaterial_control", lambda *args, **kwargs: events.append("PYTHON_NONMATERIAL") or {"status": "VALID", "non_material_signal": False, "families": []})
    result = runner.run_measurements(partition_root=tmp_path)
    assert events[:8] == ["freeze", "preflight", "execution", "openings", "F48_CONTROL", "S49-M", "S49-E", "P48-0"]
    assert events.count("TEACHER") == 3
    assert events.count("PYTHON_NONMATERIAL") == 3
    assert result["observed_results_present"] is True
    assert result["learning_invoked"] is False
    assert result["direct_selector_agreement"] is True
    assert result["efficiency"]["synthetic"]["native_current_process"]["search_count"] == 12
    assert result["efficiency"]["synthetic"]["native_current_process"]["requested_nodes"] == 3 * (80000 + 3 * 2000)
    assert events.index("L49-0") < events.index("TEACHER") < events.index("PYTHON_NONMATERIAL")
    assert {"profile_construction_count", "evaluator_construction_count", "search_wall_seconds"} <= result["efficiency"]["synthetic"]["python_current_process"].keys()
    assert result["efficiency"]["synthetic"]["CURRENT_PROCESS_EXECUTION_COST"]["native"]["search_count"] == 12
    evidence_path = runner.write_evidence_bundle(result, tmp_path / "evidence")
    assert json.loads(evidence_path.read_text(encoding="utf-8"))["direct_selector_agreement"] is True
    assert (tmp_path / "f49_evidence_bundle.json").is_file()


def test_r2_manifest_binds_resumability_order_and_transport_provenance():
    manifest = runner.load_h49b_r2_manifest()
    assert manifest["kind"] == runner.H49B_R2_KIND
    assert manifest["parent_h49b_r1_sha"] == runner.H49B_R1_SHA
    assert manifest["partition_runner"].endswith("run_partition")
    assert manifest["orchestration_phases"].index("Native material leverage surfaces") < manifest["orchestration_phases"].index("Native teacher surfaces") < manifest["orchestration_phases"].index("Python non-material controls only where authorized")
    assert set(manifest["native_transport_provenance"]) == set(runner.RULESET_IDS)
    assert all("original_max_ply" in row and "native_transport_max_ply" in row and row["ruleset_fingerprint"] for row in manifest["native_transport_provenance"].values())


def test_r2_control_events_are_replayed_not_fabricated(monkeypatch):
    action = _FakeAction("a")
    position = SimpleNamespace(index=4, ply=1, action_history=[action], position_key="accepted-position")
    control = SimpleNamespace(corpus_id="accepted-control", positions=[position])
    flags = {"remove_or_capture_effect": True, "type_or_promotion_transformation": False, "hand_or_inventory_count_change": True}
    monkeypatch.setattr(runner, "_replay_with_events", lambda compiled, history: (SimpleNamespace(legal_actions=lambda: [action, _FakeAction("b")]), flags))
    monkeypatch.setattr(runner, "action_to_dict", lambda value: {"name": value.name})
    rows = runner._control_records(SimpleNamespace(), control)
    assert rows == [{"output_index": 4, "target_ply": 1, "selected_attempt": None, "candidate_rng_seed": None, "action_history": [{"name": "a"}], "position_identity_key": "accepted-position", "legal_action_count": 2, "event_flags": flags}]


def test_r2_unavailable_stratum_gets_concrete_deterministic_partition_identity(tmp_path):
    corpus = {"status": "STRUCTURAL_STRATUM_UNAVAILABLE", "stratum_id": "S49-E", "generation_config": {"seed": 1, "attempt_cap": 2}, "failed_output_index": 7, "attempt_cap": 2, "corpus_id": None}
    first = runner._concrete_corpus_id(corpus)
    assert first == runner._concrete_corpus_id(corpus)
    assert first.startswith("UNAVAILABLE.")
    partition = runner.partition_identity(corpus_id=first, checkpoint_or_config_hash="NONE", search_route="EVALUATOR_NEUTRAL_CORE_CORPUS", node_budget=None, measurement_family="S49-E", ruleset_fingerprint="synthetic")
    runner.AtomicPartitionStore(tmp_path).write(partition, corpus)


def test_r2_run_partition_exact_hit_avoids_reexecution(tmp_path):
    partition = runner.partition_identity(corpus_id="synthetic", checkpoint_or_config_hash="checkpoint", search_route="AUDIT_SELECTOR", node_budget=None, measurement_family="SELECTOR", ruleset_fingerprint="synthetic")
    store = runner.AtomicPartitionStore(tmp_path)
    calls = []
    producer = lambda: calls.append("executed") or {"value": 1}
    assert runner.run_partition(store, partition, producer) == {"value": 1}
    assert runner.run_partition(store, partition, producer) == {"value": 1}
    assert calls == ["executed"]


def test_r2_native_raw_partitions_bind_one_budget_each(monkeypatch, tmp_path):
    compiled = SimpleNamespace(ruleset_fingerprint="synthetic")
    checkpoint = SimpleNamespace(checkpoint_id="checkpoint")
    corpus = {"corpus_id": "corpus", "records": [{"output_index": 0, "position_identity_key": "p", "action_history": []}]}
    monkeypatch.setattr(runner, "compile_native_rules", lambda value: "rules")
    monkeypatch.setattr(runner, "compile_native_evaluation", lambda *args, **kwargs: "eval")
    monkeypatch.setattr(runner, "_native_profile", lambda *args: "profile")
    monkeypatch.setattr(runner, "_native_search_once", lambda *args: {"action_key": "a", "score": 1, "nodes": 1, "qnodes": 0, "elapsed_seconds": 0.0, "completed_depth": 1, "termination_reason": "node_limit", "failed_search": False})
    store = runner.AtomicPartitionStore(tmp_path)
    runner._native_search_matrix(compiled, checkpoint, corpus, [500, 2000], "NATIVE_SEARCH_ENGINE_MATERIAL", "L49-0", runner._measurement_metrics(), {}, {}, store)
    identities = [json.loads(path.read_text(encoding="utf-8"))["input_identity"] for path in tmp_path.glob("*.json")]
    assert {row["node_budget"] for row in identities} == {500, 2000}
    assert all(row["checkpoint_or_config_hash"] == "checkpoint" for row in identities)


def test_r2_python_partitions_bind_real_evaluation_config_hash(monkeypatch, tmp_path):
    semantic = SimpleNamespace(ruleset_fingerprint="synthetic")
    corpus = {"corpus_id": "corpus", "records": [{"output_index": 0, "position_identity_key": "p0", "action_history": []}]}
    valid = {"action_key": "a", "score": 1, "nodes": 1, "qnodes": 0, "termination_reason": "node_limit", "valid": True, "exception": None}
    monkeypatch.setattr(runner, "_python_decision", lambda *args, **kwargs: dict(valid))
    store = runner.AtomicPartitionStore(tmp_path)
    runner.python_nonmaterial_control(semantic, corpus, teacher_stable=True, partition_store=store)
    identities = [json.loads(path.read_text(encoding="utf-8"))["input_identity"] for path in tmp_path.glob("*.json")]
    assert len(identities) == 7
    assert runner.config_hash(runner.EvaluationConfig()) in {row["checkpoint_or_config_hash"] for row in identities}
    assert all(row["checkpoint_or_config_hash"] != "EvaluationConfig" for row in identities)


def test_r2_freeze_drift_blocks_before_observation(monkeypatch):
    monkeypatch.setattr(runner, "load_h49b_r3_manifest", lambda: {"runner_raw_sha256": "wrong", "protocol_raw_sha256": "wrong", "h49r4a_manifest_sha256": runner.H49R4A_MANIFEST_SHA, "h49r3a_source_tree_aggregate_sha256": runner.H49R3A_SOURCE_TREE_SHA, "native_binary_sha256": runner.H49R3A_NATIVE_SHA})
    monkeypatch.setattr(runner, "run_preflight", lambda: (_ for _ in ()).throw(AssertionError("preflight ran after freeze drift")))
    with pytest.raises(RuntimeError, match="STOP_ON_H49_RUNNER_FREEZE_DRIFT"):
        runner.run_measurements(partition_root=SimpleNamespace())


def test_r2_l49_construction_failure_is_durable_and_excluded(monkeypatch):
    monkeypatch.setattr(runner, "_l49_candidate_vectors", lambda *args: [("bad", []), ("also_bad", [])])
    monkeypatch.setattr(runner, "_checkpoint_from_vector", lambda *args: (_ for _ in ()).throw(ValueError("limit")))
    rows = runner._l49_checkpoint_rows(SimpleNamespace(), _checkpoint(), "L49-1")
    assert [row["construction_failed"] for row in rows] == [True, True]
    assert all(row["checkpoint"] is None and row["reason"] for row in rows)
    assert runner._flip_surface([{"action_key": "a", "score": 1, "failed_search": 1}], [{"action_key": "a", "score": 1, "failed_search": 0}])["status"] == "CELL_INVALID_SEARCH_FAILURE"


def test_r2_l49_identical_weight_vectors_deduplicate_by_actual_checkpoint_id(monkeypatch):
    compiled = SimpleNamespace(ruleset_fingerprint="synthetic")
    start = _checkpoint()
    monkeypatch.setattr(runner, "non_anchor_type_ids", lambda compiled: ("P", "Q"))
    monkeypatch.setattr(runner, "_l49_candidate_vectors", lambda *args: [("first", [2.0, 4.0, 1.0, 2.0]), ("alias", [2.0, 4.0, 1.0, 2.0])])
    candidates = runner._l49_checkpoints(compiled, start, "L49-1")
    assert candidates[0][1].checkpoint_id == candidates[1][1].checkpoint_id


def test_r2_nonmaterial_liveness_failure_is_unmeasurable(monkeypatch):
    monkeypatch.setattr(runner, "_python_liveness_precheck", lambda execution: (False, "synthetic liveness failure"))
    result = runner.python_nonmaterial_control(SimpleNamespace(ruleset_fingerprint="synthetic"), {"records": []}, teacher_stable=True)
    assert result["status"] == "UNMEASURABLE_IN_SELECTED_SEARCH_PATH"
    assert result["non_material_signal"] is None


def test_r3_native_vector_partition_preserves_two_positions_and_resume_cost(monkeypatch, tmp_path):
    compiled = SimpleNamespace(ruleset_fingerprint="synthetic")
    checkpoint = SimpleNamespace(checkpoint_id="checkpoint")
    corpus = {"corpus_id": "corpus", "records": [{"output_index": 0, "position_identity_key": "p1", "action_history": []}, {"output_index": 1, "position_identity_key": "p2", "action_history": []}]}
    calls = []
    monkeypatch.setattr(runner, "compile_native_rules", lambda value: "rules")
    monkeypatch.setattr(runner, "compile_native_evaluation", lambda *args, **kwargs: "eval")
    monkeypatch.setattr(runner, "_native_profile", lambda *args: "profile")
    def search(*args):
        record = args[3]
        args[5]["native_current_process"]["search_count"] += 1
        args[5]["native_current_process"]["requested_nodes"] += args[4]
        calls.append(record["position_identity_key"])
        return {"action_key": record["position_identity_key"], "score": 1, "nodes": 1, "qnodes": 0, "elapsed_seconds": 0.0, "completed_depth": 1, "termination_reason": "node_limit", "failed_search": False}
    monkeypatch.setattr(runner, "_native_search_once", search)
    store = runner.AtomicPartitionStore(tmp_path)
    first_metrics = runner._measurement_metrics()
    first = runner._native_search_matrix(compiled, checkpoint, corpus, [500], "NATIVE_SEARCH_ENGINE_MATERIAL", "L49-0", first_metrics, {}, {}, store)["500"]
    second_metrics = runner._measurement_metrics()
    second = runner._native_search_matrix(compiled, checkpoint, corpus, [500], "NATIVE_SEARCH_ENGINE_MATERIAL", "L49-0", second_metrics, {}, {}, store)["500"]
    assert [row["action_key"] for row in first] == ["p1", "p2"]
    assert [row["action_key"] for row in second] == ["p1", "p2"]
    assert calls == ["p1", "p2"]
    assert first_metrics["native_authoritative"]["search_count"] == second_metrics["native_authoritative"]["search_count"] == 2
    assert second_metrics["native_current_process"]["search_count"] == 0
    with pytest.raises(RuntimeError, match="result vector"):
        runner._validate_vector({"position_identities": ["p1"], "rows": []}, corpus)


def test_r3_python_vector_partition_preserves_two_positions_and_resume_cost(monkeypatch, tmp_path):
    semantic = SimpleNamespace(ruleset_fingerprint="synthetic")
    corpus = {"corpus_id": "corpus", "records": [{"output_index": 0, "position_identity_key": "p1", "action_history": []}, {"output_index": 1, "position_identity_key": "p2", "action_history": []}]}
    calls = []
    def decision(*args):
        record = args[1]
        args[3]["python_current_process"]["search_count"] += 1
        args[3]["python_current_process"]["requested_nodes"] += 2000
        calls.append(record["position_identity_key"])
        return {"action_key": record["position_identity_key"], "score": 1, "nodes": 1, "qnodes": 0, "termination_reason": "node_limit", "valid": True, "exception": None}
    monkeypatch.setattr(runner, "_python_decision", decision)
    first_metrics = runner._measurement_metrics()
    store = runner.AtomicPartitionStore(tmp_path)
    first = runner.python_nonmaterial_control(semantic, corpus, teacher_stable=True, metrics=first_metrics, partition_store=store)
    second_metrics = runner._measurement_metrics()
    second = runner.python_nonmaterial_control(semantic, corpus, teacher_stable=True, metrics=second_metrics, partition_store=store)
    assert calls.count("p1") == calls.count("p2") == 7
    assert first["status"] == second["status"] == "VALID"
    assert first["families"][0]["factors"][0]["rows"][0]["perturbed_action_key"] == "p1"
    assert second_metrics["python_current_process"]["search_count"] == 0
    assert first_metrics["python_authoritative"]["search_count"] == second_metrics["python_authoritative"]["search_count"] == 14


def test_r3_execution_views_route_control_structural_native_and_python(monkeypatch, tmp_path):
    semantic = SimpleNamespace(ruleset_fingerprint="semantic")
    legacy = SimpleNamespace(ruleset_fingerprint="legacy")
    entry = {"semantic_execution": semantic, "legacy_transport": legacy}
    seen = {"openings": [], "structural": [], "native": [], "python": [], "writes": []}
    checkpoint = _checkpoint()
    monkeypatch.setattr(runner, "validate_r3_measurement_freeze", lambda: None)
    monkeypatch.setattr(runner, "run_preflight", lambda: {"observed_results_present": False})
    monkeypatch.setattr(runner.f49_protocol, "build_h49r3a_primary_execution", lambda: {"synthetic": entry})
    monkeypatch.setattr(runner, "generate_arena_openings", lambda compiled, **kwargs: seen["openings"].append(compiled) or SimpleNamespace())
    monkeypatch.setattr(runner, "generate_diagnostic_corpus", lambda compiled, *args, **kwargs: seen["openings"].append(compiled) or SimpleNamespace(corpus_id="control", positions=[]))
    def structural(compiled, **kwargs):
        seen["structural"].append(compiled)
        return {"status": "VALID", "corpus_id": kwargs["stratum_id"], "records": []}
    monkeypatch.setattr(runner, "generate_structural_corpus", structural)
    monkeypatch.setattr(runner, "reconstruct_p48_0", lambda *args: checkpoint)
    monkeypatch.setattr(runner, "_write_partition", lambda *args, **kwargs: seen["writes"].append(kwargs))
    monkeypatch.setattr(runner, "native_material_surface", lambda compiled, *args, **kwargs: seen["native"].append(compiled) or {"surface": args[2], "cells": {}})
    monkeypatch.setattr(runner, "teacher_surface", lambda compiled, *args, **kwargs: seen["native"].append(compiled) or {"teacher_40_80": {"status": "VALID", "failed_searches": 0, "exact_best_move_agreement": 0.9, "stable": True}, "teacher_convergence": {}})
    def python_control(compiled, *args, **kwargs):
        seen["python"].append(compiled)
        return {"status": "VALID", "non_material_signal": False, "families": []}
    monkeypatch.setattr(runner, "python_nonmaterial_control", python_control)
    monkeypatch.setattr(runner.f49_protocol, "select_f49_classification", lambda observations: ("MIXED_OR_UNRESOLVED", "F50_LEARNING_ARCHITECTURE_REASSESSMENT", {name: False for name in ("A", "B", "C", "D", "E")}))
    ledger = {name: [] for name in ("A", "B", "C", "D", "E")}
    monkeypatch.setattr(runner, "_independent_selector_ledger", lambda observations: ("MIXED_OR_UNRESOLVED", "F50_LEARNING_ARCHITECTURE_REASSESSMENT", ledger))
    monkeypatch.setattr(runner, "_production_selector_witness_ledger", lambda observations: ledger)
    runner.run_measurements(partition_root=tmp_path)
    assert seen["openings"] == [legacy, legacy]
    assert seen["structural"] == [semantic, semantic]
    assert seen["native"] and all(value is legacy for value in seen["native"])
    assert seen["python"] == [semantic, semantic, semantic]
    assert all(item.get("corpus", {}).get("corpus_id") != "control" for item in seen["writes"])
    assert all(item.get("family") != "SELECTOR" for item in seen["writes"] if item.get("corpus", {}).get("corpus_id") in ("S49-M", "S49-E"))


def test_r3_witness_ledgers_preserve_ruleset_ids_for_all_six_paths():
    cases = [
        ({"control_l0": 0.0, "control_l1": 0.1, "structural": 0.0, "nonmaterial": False}, "LEARNER_ALIGNED_SIGNAL_SUPPORTED"),
        ({"control_l0": 0.0, "control_l1": 0.0, "structural": 0.1, "nonmaterial": False}, "STRUCTURAL_CORPUS_ARCHITECTURE_LIMITING"),
        ({"teacher_stable": False}, "NATIVE_SEARCH_TEACHER_STABILITY_LIMITING"),
        ({"control_l0": 0.0, "control_l1": 0.0, "structural": 0.0, "nonmaterial": True}, "MATERIAL_ONLY_REPRESENTATION_LIMITING"),
        ({"control_l0": 0.0, "control_l1": 0.0, "structural": 0.0, "nonmaterial": False}, "EVALUATION_SIGNAL_BROADLY_WEAK"),
        ({"control_l0": 0.0, "control_l1": 0.1, "structural": 0.0, "nonmaterial": None}, "MIXED_OR_UNRESOLVED"),
    ]
    for kwargs, expected in cases:
        observations = _observations(**kwargs)
        independent = runner._independent_selector_ledger(observations)
        production = runner._production_selector_witness_ledger(observations)
        assert independent[0] == expected
        assert independent[2] == production
        assert {key: bool(value) for key, value in independent[2].items()} == runner.f49_protocol.select_f49_classification(observations)[2]


def test_r3_python_candidate_changes_exactly_one_config_field(monkeypatch):
    semantic = SimpleNamespace(ruleset_fingerprint="synthetic")
    corpus = {"corpus_id": "corpus", "records": [{"output_index": 0, "position_identity_key": "p0", "action_history": []}]}
    configs = []
    valid = {"action_key": "a", "score": 1, "nodes": 1, "qnodes": 0, "termination_reason": "node_limit", "valid": True, "exception": None}
    monkeypatch.setattr(runner, "_python_decision", lambda execution, record, config, metrics: configs.append(config) or dict(valid))
    result = runner.python_nonmaterial_control(semantic, corpus, teacher_stable=True)
    baseline = configs[0]
    assert len(configs) == 7
    for config in configs[1:]:
        assert sum(getattr(config, field.name) != getattr(baseline, field.name) for field in fields(runner.EvaluationConfig)) == 1
    assert all("config_hash" in factor for family in result["families"] for factor in family["factors"])
